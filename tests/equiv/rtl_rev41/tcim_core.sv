// tcim_core.sv - register block and sequencers of TCIM0, one 72 x 24 ternary tile.
//
// Register map (offsets in trytes from the device slot base; words at multiples of 4):
//   +0  CTRL   RW tryte  t0 EN, t1 IE (interrupt while DONE is set), t2 MODE (0 digital / + analog), t3 GO (write +, reads 0)
//   +1  STAT   RO tryte  t0 BUSY, t1 DONE (cleared by reading STAT or by the next command),
//                        t2 WERR, t3 SAT (both describe the last command; cleared by the next GO or PCMD)
//   +2  TILE   RW tryte  tile select (stored, unused on a one-tile chip)
//   +4/+8/+12  X0..X2 RW word   input vector, row r = trit (r mod 24) of word (r div 24)
//   +16..+39   Y[0..23] RO tryte column results (digital: exact sum; analog: raw converter count); valid while BUSY = 0
//   +40 PROW   RW tryte  row index 0..71 for programming and read-back
//   +44 PDATA  RW word   24 weights of the selected row
//   +48 PCMD   W  tryte  t0 = + : program row from PDATA with verify ; t0 = - : read row into PDATA
//   +49 PITER  RO tryte  pulses used by the last program command
//
// Bus: bus_addr is the tryte offset in plain binary; data are 2 bits per trit (code: see tcim_pkg), tryte in the low 12 bits.
// All trit registers reset to zero trits, and the unused trits of a read value are zero trits.
// Array side: one request at a time; the macro answers with arr_ack and the sense bits / converter counts.
module tcim_core
    import tcim_pkg::*;
(
    input  logic                    clk,
    input  logic                    rst_n,
    // register bus
    input  logic                    bus_we,
    input  logic                    bus_re,
    input  logic                    bus_word,        // 1: word access (24 trits), 0: tryte access
    input  logic [5:0]              bus_addr,
    input  logic [2*WORD-1:0]       bus_wdata,
    output logic [2*WORD-1:0]       bus_rdata,
    output logic                    bus_err,         // misaligned or unmapped access (combinational)
    output logic                    irq,
    // analog macro
    output logic                    arr_req,
    output logic [2:0]              arr_op,
    output logic [6:0]              arr_row,
    output logic [ROWS-1:0]         arr_row_mask,
    output logic [COLS-1:0]         arr_mask_p,
    output logic [COLS-1:0]         arr_mask_n,
    output logic [4:0]              arr_amp,
    input  logic                    arr_ack,
    input  logic [COLS-1:0]         arr_sa_p,
    input  logic [COLS-1:0]         arr_sa_n,
    input  logic [COLS*ACCW-1:0]    arr_adc
);
    // ------------------------------------------------------------------ registers
    logic                   r_en, r_ie, r_mode;
    logic                   s_busy, s_done, s_werr, s_sat;
    logic [2*TRYTE-1:0]     r_tile;
    logic [3*2*WORD-1:0]    r_x;             // X2, X1, X0
    logic [COLS*ACCW-1:0]   acc;             // 24 two's-complement accumulators
    logic [2*TRYTE-1:0]     r_prow;
    logic [2*WORD-1:0]      r_pdata;
    logic [5:0]             r_piter;

    // ------------------------------------------------------------------ sequencer state
    typedef enum logic [3:0] {
        S_IDLE, S_SCAN, S_READ, S_SUM_P, S_SUM_N,
        S_RST_VFY, S_RST_PULSE, S_SET_VFY, S_SET_PULSE, S_RDBK, S_FINISH
    } state_t;
    state_t state;
    logic [6:0]             row;

    // ------------------------------------------------------------------ decode
    logic a_ctrl, a_stat, a_tile, a_x, a_y, a_prow, a_pdata, a_pcmd, a_piter, a_valid;
    logic [1:0] x_idx;
    logic [4:0] y_idx;
    always_comb begin
        a_ctrl  = (bus_addr == 6'd0)  && !bus_word;
        a_stat  = (bus_addr == 6'd1)  && !bus_word;
        a_tile  = (bus_addr == 6'd2)  && !bus_word;
        a_x     = bus_word && (bus_addr == 6'd4 || bus_addr == 6'd8 || bus_addr == 6'd12);
        a_y     = !bus_word && (bus_addr >= 6'd16) && (bus_addr <= 6'd39);
        a_prow  = (bus_addr == 6'd40) && !bus_word;
        a_pdata = (bus_addr == 6'd44) && bus_word;
        a_pcmd  = (bus_addr == 6'd48) && !bus_word;
        a_piter = (bus_addr == 6'd49) && !bus_word;
        a_valid = a_ctrl | a_stat | a_tile | a_x | a_y | a_prow | a_pdata | a_pcmd | a_piter;
        x_idx   = (bus_addr == 6'd4) ? 2'd0 : (bus_addr == 6'd8) ? 2'd1 : 2'd2;
        y_idx   = 5'(bus_addr - 6'd16);
        bus_err = (bus_we | bus_re) & ~a_valid;
    end

    logic wr, rd;
    assign wr = bus_we & a_valid;
    assign rd = bus_re & a_valid;

    logic go_cmd, go_analog, prog_cmd, rdbk_cmd;
    // GO takes effect together with the EN and MODE trits written in the same access
    assign go_cmd    = wr & a_ctrl & is_pos(bus_wdata[7:6]) & is_pos(bus_wdata[1:0]) & ~s_busy;
    assign go_analog = is_pos(bus_wdata[5:4]);
    assign prog_cmd  = wr & a_pcmd & is_pos(bus_wdata[1:0]) & ~s_busy & r_en;
    assign rdbk_cmd  = wr & a_pcmd & is_neg(bus_wdata[1:0]) & ~s_busy & r_en;

    // read data
    always_comb begin
        bus_rdata = ZERO_WORD;                       // trits that a register does not use read as 0
        if (a_ctrl)       bus_rdata[5:0]  = {sign_to_trit(r_mode, 1'b0), sign_to_trit(r_ie, 1'b0), sign_to_trit(r_en, 1'b0)};
        else if (a_stat)  bus_rdata[7:0]  = {sign_to_trit(s_sat, 1'b0), sign_to_trit(s_werr, 1'b0), sign_to_trit(s_done, 1'b0), sign_to_trit(s_busy, 1'b0)};
        else if (a_tile)  bus_rdata[2*TRYTE-1:0] = r_tile;
        else if (a_x)     bus_rdata = r_x[x_idx*2*WORD +: 2*WORD];
        else if (a_y)     bus_rdata[2*TRYTE-1:0] = int_to_tryte($signed(acc[y_idx*ACCW +: ACCW]));
        else if (a_prow)  bus_rdata[2*TRYTE-1:0] = r_prow;
        else if (a_pdata) bus_rdata = r_pdata;
        else if (a_piter) bus_rdata[2*TRYTE-1:0] = int_to_tryte({4'b0, r_piter});
    end

    // ------------------------------------------------------------------ helpers
    logic [2*ROWS-1:0] x_flat;
    assign x_flat = r_x;
    logic [ROWS-1:0] x_pos, x_neg;
    always_comb for (int r = 0; r < ROWS; r++) begin
        x_pos[r] = is_pos(x_flat[2*r +: 2]);
        x_neg[r] = is_neg(x_flat[2*r +: 2]);
    end
    logic [COLS-1:0] w_pos, w_neg;
    always_comb for (int c = 0; c < COLS; c++) begin
        w_pos[c] = is_pos(r_pdata[2*c +: 2]);
        w_neg[c] = is_neg(r_pdata[2*c +: 2]);
    end
    logic signed [ACCW-1:0] prow_int;
    assign prow_int = tryte_to_int(r_prow);
    logic prow_ok;
    localparam logic signed [ACCW-1:0] ROWS_S = ACCW'(ROWS);   // ROWS as a signed value of the same width
    assign prow_ok = (prow_int >= 10'sd0) && (prow_int < ROWS_S);

    // next accumulator values for a digital row read, and the saturated P - N difference for analog mode
    logic [COLS*ACCW-1:0] acc_next, diff_sat;
    logic                 diff_clip;
    logic                 cur_pos;
    always_comb begin
        acc_next = acc; diff_sat = '0; diff_clip = 1'b0;
        cur_pos  = x_pos[row < 7'(ROWS) ? row : 7'd0];
        for (int c = 0; c < COLS; c++) begin
            logic signed [ACCW-1:0] a;
            logic signed [ACCW:0]   d;
            a = $signed(acc[c*ACCW +: ACCW]);
            if (arr_sa_p[c] & ~arr_sa_n[c])      acc_next[c*ACCW +: ACCW] = cur_pos ? a + 10'sd1 : a - 10'sd1;
            else if (arr_sa_n[c] & ~arr_sa_p[c]) acc_next[c*ACCW +: ACCW] = cur_pos ? a - 10'sd1 : a + 10'sd1;
            d = {a[ACCW-1], a} - {arr_adc[c*ACCW + ACCW-1], arr_adc[c*ACCW +: ACCW]};
            if (d > 11'sd364)       begin diff_sat[c*ACCW +: ACCW] = 10'sd364;  diff_clip = 1'b1; end
            else if (d < -11'sd364) begin diff_sat[c*ACCW +: ACCW] = -10'sd364; diff_clip = 1'b1; end
            else                    diff_sat[c*ACCW +: ACCW] = d[ACCW-1:0];
        end
    end

    // ------------------------------------------------------------------ sequencer
    logic [COLS-1:0] pend_p, pend_n;
    logic [4:0]      amp;
    logic            req;

    assign arr_req = req;
    // WERR and SAT never arrive without DONE (every operation ends in S_FINISH), so DONE alone drives the
    // interrupt and reading STAT acknowledges it. (Revision 3 also OR-ed WERR in, which reading STAT could not clear.)
    assign irq     = r_ie & s_done;
    assign s_busy  = (state != S_IDLE);

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            r_en <= 1'b0; r_ie <= 1'b0; r_mode <= 1'b0; r_tile <= ZERO_TRYTE;
            r_x <= {3{ZERO_WORD}};
            r_prow <= ZERO_TRYTE; r_pdata <= ZERO_WORD; r_piter <= '0;
            s_done <= 1'b0; s_werr <= 1'b0; s_sat <= 1'b0;
            state <= S_IDLE; row <= '0; pend_p <= '0; pend_n <= '0; amp <= '0; req <= 1'b0;
            arr_op <= OP_READ; arr_row <= '0; arr_row_mask <= '0; arr_mask_p <= '0; arr_mask_n <= '0; arr_amp <= '0;
            acc <= '0;
        end else begin
            // ---- bus writes (ignored while busy, except CTRL enable/interrupt bits)
            if (wr && a_ctrl) begin
                r_en <= is_pos(bus_wdata[1:0]); r_ie <= is_pos(bus_wdata[3:2]);
                if (!s_busy) r_mode <= is_pos(bus_wdata[5:4]);
            end
            if (wr && !s_busy) begin
                if (a_tile)  r_tile <= bus_wdata[2*TRYTE-1:0];
                if (a_x)     r_x[x_idx*2*WORD +: 2*WORD] <= bus_wdata;
                if (a_prow)  r_prow <= bus_wdata[2*TRYTE-1:0];
                if (a_pdata) r_pdata <= bus_wdata;
            end
            if (rd && a_stat) s_done <= 1'b0;                 // DONE is cleared by reading STAT

            case (state)
                S_IDLE: begin
                    req <= 1'b0;
                    if (go_cmd) begin
                        s_done <= 1'b0; s_sat <= 1'b0; s_werr <= 1'b0;
                        acc <= '0; row <= '0;
                        if (go_analog) begin
                            arr_op <= OP_SUM; arr_row_mask <= x_pos; req <= 1'b1; state <= S_SUM_P;
                        end else state <= S_SCAN;
                    end else if (prog_cmd) begin
                        s_done <= 1'b0; s_sat <= 1'b0; s_werr <= ~prow_ok; r_piter <= '0; amp <= '0;
                        if (prow_ok) begin
                            arr_row <= prow_int[6:0];
                            pend_p <= ~w_pos; pend_n <= ~w_neg;            // devices that must be HRS
                            arr_op <= OP_VFY_RESET; arr_mask_p <= ~w_pos; arr_mask_n <= ~w_neg; req <= 1'b1;
                            state <= S_RST_VFY;
                        end else state <= S_FINISH;
                    end else if (rdbk_cmd) begin
                        s_done <= 1'b0; s_sat <= 1'b0; s_werr <= ~prow_ok;
                        if (prow_ok) begin
                            arr_row <= prow_int[6:0]; arr_op <= OP_READ; arr_mask_p <= '1; arr_mask_n <= '1; req <= 1'b1;
                            state <= S_RDBK;
                        end else state <= S_FINISH;
                    end
                end

                // ---------------- digital product: one row read per non-zero input
                S_SCAN: begin
                    if (row == 7'(ROWS)) state <= S_FINISH;
                    else if (x_pos[row] | x_neg[row]) begin
                        arr_op <= OP_READ; arr_row <= row; arr_mask_p <= '1; arr_mask_n <= '1; req <= 1'b1;
                        state <= S_READ;
                    end else row <= row + 7'd1;
                end
                S_READ: if (arr_ack) begin
                    req <= 1'b0;
                    acc <= acc_next;                             // weight = sa_p - sa_n ; both set counts as 0
                    if (|(arr_sa_p & arr_sa_n)) s_werr <= 1'b1;
                    row <= row + 7'd1; state <= S_SCAN;
                end

                // ---------------- analog product: two summed reads, P phase minus N phase
                S_SUM_P: if (arr_ack) begin
                    acc <= arr_adc;
                    arr_row_mask <= x_neg; req <= 1'b1; state <= S_SUM_N;
                end
                S_SUM_N: if (arr_ack) begin
                    req <= 1'b0; acc <= diff_sat; s_sat <= diff_clip;
                    state <= S_FINISH;
                end

                // ---------------- program row: reset phase, then set phase, each pulse followed by verify
                S_RST_VFY: if (arr_ack) begin
                    pend_p <= pend_p & arr_sa_p; pend_n <= pend_n & arr_sa_n;
                    if (((pend_p & arr_sa_p) | (pend_n & arr_sa_n)) == '0) begin
                        amp <= '0; pend_p <= w_pos; pend_n <= w_neg;        // devices that must be LRS
                        arr_op <= OP_VFY_SET; arr_mask_p <= w_pos; arr_mask_n <= w_neg; state <= S_SET_VFY;
                    end else if (amp == 5'(AMP_STEPS)) begin
                        s_werr <= 1'b1; req <= 1'b0; state <= S_FINISH;
                    end else begin
                        arr_op <= OP_PULSE_RST; arr_amp <= amp; arr_mask_p <= pend_p & arr_sa_p; arr_mask_n <= pend_n & arr_sa_n;
                        state <= S_RST_PULSE;
                    end
                end
                S_RST_PULSE: if (arr_ack) begin
                    amp <= amp + 5'd1; r_piter <= r_piter + 6'd1;
                    arr_op <= OP_VFY_RESET; state <= S_RST_VFY;
                end
                S_SET_VFY: if (arr_ack) begin
                    pend_p <= pend_p & ~arr_sa_p; pend_n <= pend_n & ~arr_sa_n;
                    if (((pend_p & ~arr_sa_p) | (pend_n & ~arr_sa_n)) == '0) begin
                        req <= 1'b0; state <= S_FINISH;
                    end else if (amp == 5'(AMP_STEPS)) begin
                        s_werr <= 1'b1; req <= 1'b0; state <= S_FINISH;
                    end else begin
                        arr_op <= OP_PULSE_SET; arr_amp <= amp; arr_mask_p <= pend_p & ~arr_sa_p; arr_mask_n <= pend_n & ~arr_sa_n;
                        state <= S_SET_PULSE;
                    end
                end
                S_SET_PULSE: if (arr_ack) begin
                    amp <= amp + 5'd1; r_piter <= r_piter + 6'd1;
                    arr_op <= OP_VFY_SET; state <= S_SET_VFY;
                end

                // ---------------- read a row back into PDATA
                S_RDBK: if (arr_ack) begin
                    req <= 1'b0;
                    for (int c = 0; c < COLS; c++)
                        r_pdata[2*c +: 2] <= sign_to_trit(arr_sa_p[c] & ~arr_sa_n[c], arr_sa_n[c] & ~arr_sa_p[c]);
                    for (int c = COLS; c < WORD; c++) r_pdata[2*c +: 2] <= T_ZERO;
                    if (|(arr_sa_p & arr_sa_n)) s_werr <= 1'b1;
                    state <= S_FINISH;
                end

                S_FINISH: begin
                    req <= 1'b0; s_done <= 1'b1; state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
`ifdef FORMAL
    // ------------------------------------------------------------------ formal properties (formal/tcim_core.sby)
    // Checked for every sequence of bus accesses and array answers after a reset. Shadow registers below exist
    // only for the proofs. With FORMAL_ACK defined the array is assumed to answer every request at once, and the
    // progress property (every command ends within a bounded time) is checked.
    logic       f_init = 1'b1;
    logic [2:0] f_cmd;                   // last accepted command: 1 digital, 2 analog, 3 program, 4 read-back
    logic [6:0] f_row;                   // row of the last program or read-back command
    logic       f_seen_set;              // a set pulse has been issued in the present command
    logic [8:0] f_busy_cnt;              // clock cycles since the present command started
    logic [2*WORD-1:0] f_pdata;          // PDATA at the start of the command
    localparam logic [8:0] F_BUSY_MAX = 9'd200;
    wire f_pulse = req && (arr_op == OP_PULSE_SET || arr_op == OP_PULSE_RST);
    wire f_vfy   = req && (arr_op == OP_VFY_SET || arr_op == OP_VFY_RESET);
    always_ff @(posedge clk) begin
        f_init <= 1'b0;
        if (f_init) assume (!rst_n);
`ifdef FORMAL_ACK
        assume (arr_ack == arr_req);
`endif
        if (!rst_n) begin
            f_cmd <= '0; f_row <= '0; f_seen_set <= 1'b0; f_busy_cnt <= '0; f_pdata <= '0;
        end else begin
            if (go_cmd)        begin f_cmd <= go_analog ? 3'd2 : 3'd1; f_seen_set <= 1'b0; f_busy_cnt <= '0; end
            else if (prog_cmd) begin f_cmd <= 3'd3; f_row <= prow_int[6:0]; f_seen_set <= 1'b0; f_busy_cnt <= '0; f_pdata <= r_pdata; end
            else if (rdbk_cmd) begin f_cmd <= 3'd4; f_row <= prow_int[6:0]; f_seen_set <= 1'b0; f_busy_cnt <= '0; end
            else begin
                if (s_busy && f_busy_cnt != 9'h1ff) f_busy_cnt <= f_busy_cnt + 9'd1;
                if (f_pulse && arr_op == OP_PULSE_SET) f_seen_set <= 1'b1;
            end
        end
        if (!f_init && rst_n) begin
            // the array is never asked about a row that does not exist
            if (req && arr_op != OP_SUM) assert (arr_row < 7'(ROWS));
            // pulses happen only inside a program command, on its row, with the stored weights unchanged
            if (f_pulse) assert (s_busy && f_cmd == 3'd3 && arr_row == f_row);
            if (f_vfy)   assert (s_busy && f_cmd == 3'd3 && arr_row == f_row);
            if (f_cmd == 3'd3 && s_busy) assert (r_pdata == f_pdata);
            // pulse amplitude stays inside the published scheme; every pulse selects at least one device
            if (f_pulse) assert (arr_amp < 5'(AMP_STEPS));
            if (f_pulse) assert ((arr_mask_p | arr_mask_n) != '0);
            // a pulse only reaches devices that must change: set only where the weight needs LRS, reset only where HRS
            if (f_pulse && arr_op == OP_PULSE_SET) assert ((arr_mask_p & ~w_pos) == '0 && (arr_mask_n & ~w_neg) == '0);
            if (f_pulse && arr_op == OP_PULSE_RST) assert ((arr_mask_p & w_pos) == '0 && (arr_mask_n & w_neg) == '0);
            // within one command no reset pulse follows a set pulse
            if (f_pulse && arr_op == OP_PULSE_RST) assert (!f_seen_set);
            // at most 21 reset and 21 set pulses per command
            assert (r_piter <= 6'(2 * AMP_STEPS));
            // products and read-back never write the array
            if (f_cmd == 3'd1 || f_cmd == 3'd2 || f_cmd == 3'd4) assert (!f_pulse);
            // digital product: a result never exceeds the number of rows (checked on column 0; the columns are alike)
            if (f_cmd == 3'd1) assert ($signed(acc[ACCW-1:0]) <= 10'sd72 && $signed(acc[ACCW-1:0]) >= -10'sd72);
            // the interrupt line is exactly IE and DONE
            assert (irq == (r_ie && s_done));
`ifdef FORMAL_ACK
            // progress: with an array that answers at once, every command ends within F_BUSY_MAX cycles
            assert (f_busy_cnt < F_BUSY_MAX);
`endif
        end
    end
`endif
endmodule
