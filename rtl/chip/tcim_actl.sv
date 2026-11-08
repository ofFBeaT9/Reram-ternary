// tcim_actl.sv - array controller of the SKY130 test chip (11 October 2026, revision 2).
//
// Turns one request of the TCIM0 core (arr_* handshake, see tcim_core.sv) into timed control of the analog macro:
// word lines, bit-line and source-line drivers, reference selection, and the sampling of the 48 sense amplifiers.
// Every macro-side output comes straight from a flip-flop (no glitches into the level shifters).
//
// Lines of ternary column c: bit line P (device +) = blp[c], bit line N (device -) = bln[c], source line sl[c]
// shared by both devices. In the macro (chip/sky130/sim/periph.spice), per bit line:
//     to VPRG    when  blp_prg / bln_prg
//     to its sense amplifier when bl_sen (all bit lines together)
//     to ground  when  NOT (prg OR bl_sen OR flt)      (a NOR gate in the 3.3 V domain)
// and for all 24 source lines together: to VPRG when sl_prg, to ground when NOT (sl_prg OR flt).
// flt ("float") is raised one cycle before any prg / sen / sl_prg changes and dropped one cycle after, so a line never
// goes directly from ground to a rail or back (break before make). A line is floating only while every word line is
// off, for at most two cycles.
// Revision 1 had a separate ground control per line (96 more level shifters); revision 2 needs one level shifter per
// bit line and four shared ones (bl_sen, sl_prg, flt, wl_prog).
//
// Sequence of every array operation (cycles of clk; T_* from the static configuration inputs):
//   IDLE   all lines grounded, word lines off
//   BRK    flt = 1: every line leaves ground                                                         1 cycle
//   MAKE   lines in their operating mode (prg / sen / sl_prg), word-line rail and references selected      1 cycle
//   SETL   flt = 0: the other lines grounded again; the board settles VPRG / VWLP                    T_SETTLE
//   WLON   the selected word line on the read rail (reads) or the program rail (pulses)   T_SENSE or T_PULSE
//          reads: the sense outputs are sampled in the last cycle of WLON (first flip-flop)
//   WLOFF  word line off; reads: second flip-flop of the sense outputs                                1 cycle
//   REL    flt = 1                                                                                     1 cycle
//   BRK2   prg / sen / sl_prg released                                                                 1 cycle
//   GND    flt = 0: all lines grounded                                                                 1 cycle
//   ACK    arr_ack = 1 with the sense bits; IDLE in the next cycle                                     1 cycle
// Operations:
//   READ / VFY_SET / VFY_RESET: all bit lines to the sense amplifiers, source lines grounded, reference
//     mid / set target / reset target (ref_sel = 010 / 100 / 001).
//   PULSE_SET: masked bit lines to VPRG, other bit lines and all source lines grounded (+VPRG on the masked devices).
//   PULSE_RST: masked bit lines grounded, other bit lines and all source lines at VPRG (-VPRG on the masked devices,
//     0 V on every other device of the row).
//   SUM (analog mode): not supported on this chip (no column converter); acknowledged after one cycle, converter
//     counts are tied to zero by the chip top.
// Test-board outputs: pk (0 set / 1 reset) and pamp (amplitude code) of the last pulse request, valid from the
// start of BRK of that request; pstb = 1 while a program word line is on.
module tcim_actl
    import tcim_pkg::*;
(
    input  logic                    clk,
    input  logic                    rst_n,
    // TCIM0 core side
    input  logic                    arr_req,
    input  logic [2:0]              arr_op,
    input  logic [6:0]              arr_row,
    input  logic [COLS-1:0]         arr_mask_p,
    input  logic [COLS-1:0]         arr_mask_n,
    input  logic [4:0]              arr_amp,
    output logic                    arr_ack,
    output logic [COLS-1:0]         arr_sa_p,
    output logic [COLS-1:0]         arr_sa_n,
    // static configuration: T_SETTLE = 2^(cfg_ts+1), T_PULSE = 2^(cfg_tp+2), T_SENSE = 2^(cfg_tr+2) cycles
    input  logic [2:0]              cfg_ts,
    input  logic [2:0]              cfg_tp,
    input  logic [1:0]              cfg_tr,
    // analog macro side (1.8 V; level-shifted in the macro)
    output logic [ROWS-1:0]         wl_on,
    output logic                    wl_prog,          // word-line rail: 1 = VWLP (program), 0 = VWLR (read)
    output logic [COLS-1:0]         blp_prg, bln_prg, // bit line to VPRG
    output logic                    bl_sen,           // all bit lines to their sense amplifiers
    output logic                    sl_prg,           // all source lines to VPRG
    output logic                    flt,              // no line grounded (break before make)
    output logic [2:0]              ref_sel,          // one-hot: [0] reset target, [1] mid, [2] set target
    input  logic [COLS-1:0]         sa_p,             // raw sense outputs (asynchronous to clk)
    input  logic [COLS-1:0]         sa_n,
    // test board
    output logic                    pk,
    output logic [4:0]              pamp,
    output logic                    pstb
);
    typedef enum logic [3:0] { A_IDLE, A_BRK, A_MAKE, A_SETL, A_WLON, A_WLOFF, A_REL, A_BRK2, A_GND, A_ACK, A_SUM } astate_t;
    astate_t st;

    logic [2:0]       op;
    logic [6:0]       row;
    logic [COLS-1:0]  mp, mn;
    logic [8:0]       cnt;                 // longest wait 2^9 cycles
    logic [COLS-1:0]  q1_p, q1_n;          // sense outputs, first flip-flop
    logic             is_rd, is_set, is_rst;

    assign is_rd  = (op == OP_READ) || (op == OP_VFY_SET) || (op == OP_VFY_RESET);
    assign is_set = (op == OP_PULSE_SET);
    assign is_rst = (op == OP_PULSE_RST);

    function automatic logic [8:0] pow2m1(input logic [3:0] e);     // 2^e - 1
        return 9'((10'd1 << e) - 10'd1);
    endfunction

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= A_IDLE; op <= OP_READ; row <= '0; mp <= '0; mn <= '0; cnt <= '0;
            q1_p <= '0; q1_n <= '0; arr_sa_p <= '0; arr_sa_n <= '0; arr_ack <= 1'b0;
            wl_on <= '0; wl_prog <= 1'b0; bl_sen <= 1'b0; ref_sel <= '0;
            blp_prg <= '0; bln_prg <= '0; sl_prg <= 1'b0; flt <= 1'b0;
            pk <= 1'b0; pamp <= '0; pstb <= 1'b0;
        end else begin
            arr_ack <= 1'b0;
            case (st)
                A_IDLE: if (arr_req) begin
                    op <= arr_op; row <= arr_row; mp <= arr_mask_p; mn <= arr_mask_n;
                    if (arr_op == OP_SUM || arr_op > OP_SUM || arr_row >= 7'(ROWS)) begin
                        st <= A_SUM;                              // nothing is driven: answered with zeros
                    end else begin
                        if (arr_op == OP_PULSE_SET || arr_op == OP_PULSE_RST) begin
                            pk <= (arr_op == OP_PULSE_RST); pamp <= arr_amp;
                        end
                        flt <= 1'b1;
                        st <= A_BRK;
                    end
                end
                A_BRK: begin                                      // every line floating; set the operating mode
                    blp_prg <= is_set ? mp : (is_rst ? ~mp : '0);
                    bln_prg <= is_set ? mn : (is_rst ? ~mn : '0);
                    sl_prg  <= is_rst;
                    bl_sen  <= is_rd;
                    wl_prog <= ~is_rd;                            // word-line rail chosen before the word line rises
                    ref_sel <= (op == OP_VFY_SET) ? 3'b100 : (op == OP_VFY_RESET) ? 3'b001 : (is_rd ? 3'b010 : 3'b000);
                    st <= A_MAKE;
                end
                A_MAKE: begin                                     // lines in their mode; the rest grounded again
                    flt <= 1'b0;
                    cnt <= pow2m1({1'b0, cfg_ts} + 4'd1);
                    st <= A_SETL;
                end
                A_SETL: begin
                    if (cnt == '0) begin
                        wl_on[row] <= 1'b1; pstb <= ~is_rd;
                        cnt <= is_rd ? pow2m1({2'b0, cfg_tr} + 4'd2) : pow2m1({1'b0, cfg_tp} + 4'd2);
                        st <= A_WLON;
                    end else cnt <= cnt - 9'd1;
                end
                A_WLON: begin
                    if (cnt == '0) begin
                        if (is_rd) begin q1_p <= sa_p; q1_n <= sa_n; end
                        wl_on <= '0; pstb <= 1'b0;
                        st <= A_WLOFF;
                    end else cnt <= cnt - 9'd1;
                end
                A_WLOFF: begin                                    // word line falling; second sampling flip-flop
                    arr_sa_p <= is_rd ? q1_p : '0; arr_sa_n <= is_rd ? q1_n : '0;
                    flt <= 1'b1;
                    st <= A_REL;
                end
                A_REL: begin                                      // every line floating: release the modes
                    blp_prg <= '0; bln_prg <= '0; sl_prg <= 1'b0; bl_sen <= 1'b0; ref_sel <= '0; wl_prog <= 1'b0;
                    st <= A_BRK2;
                end
                A_BRK2: begin
                    flt <= 1'b0;
                    arr_ack <= 1'b1;
                    st <= A_GND;
                end
                A_GND: st <= A_IDLE;                              // all lines grounded; arr_ack is high in this cycle
                A_SUM: begin
                    arr_sa_p <= '0; arr_sa_n <= '0; arr_ack <= 1'b1;
                    st <= A_ACK;
                end
                A_ACK: st <= A_IDLE;
                default: st <= A_IDLE;
            endcase
        end
    end
endmodule
