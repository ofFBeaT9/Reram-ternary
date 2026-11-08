// tcim_core.sv - register block and sequencers of TCIM0, one 72 x 24 ternary tile.
//
// Register map (offsets in trytes from the device slot base; words at multiples of 4):
//   +0  CTRL   RW tryte  t0 EN, t1 IE (interrupt while DONE is set), t2 MODE (0 digital / + analog), t3 GO (write +, reads 0)
//   +1  STAT   RO tryte  t0 BUSY, t1 DONE (cleared by reading STAT or by the next command),
//                        t2 WERR, t3 SAT (both describe the last command; cleared by the next GO or PCMD)
//   +2  TILE   RW tryte  tile select (stored, unused on a one-tile chip)
//   +3  SEC    RW tryte  security options (revision 4.6), all opt-in, reset to 0:
//                        t0 ZSKIP   (+ : products read only rows with a non-zero input, in increasing order; otherwise
//                                    every product reads all 72 rows, starting at a pseudo-random row)
//                        t1 VARPROG (+ : programming stops as soon as every device verifies; otherwise every program
//                                    command runs 21 reset steps and 21 set steps, padding with empty pulses)
//                        t2 NOSHUF  (+ : fixed-latency products start at row 0)
//                        t3 LOCK    (+ : set-only until reset; clears t0-t2, ignores later SEC writes, PITER and ACT read
//                                    0; revision 4.7: also refuses read-back, keeps the margin check from writing PDATA,
//                                    and gates every use of t0-t2). A SEC write while BUSY is ignored: read SEC back.
//   +4/+8/+12  X0..X2 RW word   input vector, row r = trit (r mod 24) of word (r div 24)
//   +16..+39   Y[0..23] RO tryte column results (digital: exact sum; analog: raw converter count); valid while BUSY = 0
//                        (revision 4.7: during a digital product they hold the sum plus a random offset)
//   +40 PROW   RW tryte  row index 0..71 for programming and read-back
//   +44 PDATA  RW word   24 weights of the selected row
//   +48 PCMD   W  tryte  t0 = + : program row from PDATA with verify ; t0 = - : read row into PDATA (refused under LOCK) ;
//                        t0 = 0, t1 = + : margin check of the row (revision 4.6): PDATA <- the weights read (not under
//                        LOCK), MARG <- +
//                        for each column with a device inside the margin band (WERR if any)
//   +49 PITER  RO tryte  pulses used by the last program command (empty padding pulses not counted)
//   +50 ACT    RO tryte  t0 = + when the parity of all dummy-accumulator bits is odd (revision 4.6). It makes the dummy
//                        accumulators observable, so that synthesis keeps them, and lets a test see them run; 0 under LOCK.
//                        The parity depends on the inputs and weights, so a deployment sets LOCK (council, 6 Nov 2026)
//   +52 MARG   RO word   result of the last margin check, one trit per column
//
// Digital product (revision 4.2): one request per row; the next row is put on arr_row in the cycle the answer for the
// previous one arrives, and arr_req stays high between them, so the macro is never idle between two row reads.
// Revision 4.6 (security study, 4 November 2026): by default every product reads all 72 rows, starting at a row taken
// from a free-running 16-bit LFSR (rotation mod 72), so its duration depends neither on the inputs nor on the weights
// (revision 4.7: the whole 16-bit value modulo 72, so every row is equally likely to within 1 part in 910; revision 4.6
// used 7 bits folded once, which made rows 0-55 twice as likely as rows 56-71; the LFSR is deterministic after reset);
// a row with input 0 is read and changes no result. In every row read each column makes exactly one accumulator update:
// the result accumulator when input and weight are both non-zero, otherwise a dummy accumulator (+1 or -1 from the
// LFSR) that never enters a result, so the number of accumulator updates per row does not depend on the data either.
// Revision 4.7: the result accumulators start each digital product at a common random offset (-128 ... 127) that the
// last row takes off again, so the bits an update flips do not follow the partial sum as it moves around zero.
// With SEC.ZSKIP the revision 4.2 behaviour returns (only rows with a non-zero input, in increasing order).
// Programming (revision 4.6): by default each phase runs exactly 21 verify-pulse steps and a final verify, whatever the
// devices do; a step in which every device has verified issues a pulse with empty masks (the macro then grounds every
// bit and source line for a set pulse, and puts VPRG on all of them for a reset pulse: no voltage across any device).
//
// Bus: bus_addr is the tryte offset in plain binary; data are 2 bits per trit (code: see tcim_pkg), tryte in the low 12 bits.
// All trit registers reset to zero trits, and the unused trits of a read value are zero trits.
// Array side: one request at a time; the macro answers with arr_ack and the sense bits / converter counts.
// A request is outstanding while arr_req is high. If arr_req is still high in the cycle after an answer, that is a
// new request with the operation, row and masks present then (programming and digital products both use this).
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
    logic                   r_zskip, r_varprog, r_noshuf, r_lock;     // SEC (revision 4.6)
    logic [15:0]            lfsr;                                     // free-running, x^16 + x^14 + x^13 + x^11 + 1
    logic [6:0]             lfsr_m72;                                 // lfsr mod 72, kept step by step (revision 4.7)
    logic signed [ACCW-1:0] r_off;                                    // offset of the result accumulators (revision 4.7)
    logic [6:0]             r_cnt;                                    // rows answered in a fixed-latency product
    logic [COLS-1:0]        m_fail;                                   // MARG
    logic [COLS*ACCW-1:0]   d_acc;                                    // dummy accumulators (never read)

    // ------------------------------------------------------------------ sequencer state
    typedef enum logic [3:0] {
        S_IDLE, S_READ, S_SUM_P, S_SUM_N,
        S_RST_VFY, S_RST_PULSE, S_SET_VFY, S_SET_PULSE, S_RDBK, S_FINISH,
        S_MC_RD, S_MC_SET, S_MC_RST
    } state_t;
    state_t state;

    // ------------------------------------------------------------------ decode
    logic a_ctrl, a_stat, a_tile, a_sec, a_x, a_y, a_prow, a_pdata, a_pcmd, a_piter, a_act, a_marg, a_valid;
    logic [1:0] x_idx;
    logic [4:0] y_idx;
    always_comb begin
        a_ctrl  = (bus_addr == 6'd0)  && !bus_word;
        a_stat  = (bus_addr == 6'd1)  && !bus_word;
        a_tile  = (bus_addr == 6'd2)  && !bus_word;
        a_sec   = (bus_addr == 6'd3)  && !bus_word;
        a_x     = bus_word && (bus_addr == 6'd4 || bus_addr == 6'd8 || bus_addr == 6'd12);
        a_y     = !bus_word && (bus_addr >= 6'd16) && (bus_addr <= 6'd39);
        a_prow  = (bus_addr == 6'd40) && !bus_word;
        a_pdata = (bus_addr == 6'd44) && bus_word;
        a_pcmd  = (bus_addr == 6'd48) && !bus_word;
        a_piter = (bus_addr == 6'd49) && !bus_word;
        a_act   = (bus_addr == 6'd50) && !bus_word;
        a_marg  = (bus_addr == 6'd52) && bus_word;
        a_valid = a_ctrl | a_stat | a_tile | a_sec | a_x | a_y | a_prow | a_pdata | a_pcmd | a_piter | a_act | a_marg;
        x_idx   = (bus_addr == 6'd4) ? 2'd0 : (bus_addr == 6'd8) ? 2'd1 : 2'd2;
        y_idx   = 5'(bus_addr - 6'd16);
        bus_err = (bus_we | bus_re) & ~a_valid;
    end

    logic wr, rd;
    assign wr = bus_we & a_valid;
    assign rd = bus_re & a_valid;

    logic go_cmd, go_analog, prog_cmd, rdbk_cmd, mchk_cmd;
    // GO takes effect together with the EN and MODE trits written in the same access
    assign go_cmd    = wr & a_ctrl & is_pos(bus_wdata[7:6]) & is_pos(bus_wdata[1:0]) & ~s_busy;
    assign go_analog = is_pos(bus_wdata[5:4]);
    assign prog_cmd  = wr & a_pcmd & is_pos(bus_wdata[1:0]) & ~s_busy & r_en;
    assign rdbk_cmd  = wr & a_pcmd & is_neg(bus_wdata[1:0]) & ~s_busy & r_en;
    assign mchk_cmd  = wr & a_pcmd & (bus_wdata[1:0] == T_ZERO) & is_pos(bus_wdata[3:2]) & ~s_busy & r_en;

    // read data
    always_comb begin
        bus_rdata = ZERO_WORD;                       // trits that a register does not use read as 0
        if (a_ctrl)       bus_rdata[5:0]  = {sign_to_trit(r_mode, 1'b0), sign_to_trit(r_ie, 1'b0), sign_to_trit(r_en, 1'b0)};
        else if (a_stat)  bus_rdata[7:0]  = {sign_to_trit(s_sat, 1'b0), sign_to_trit(s_werr, 1'b0), sign_to_trit(s_done, 1'b0), sign_to_trit(s_busy, 1'b0)};
        else if (a_tile)  bus_rdata[2*TRYTE-1:0] = r_tile;
        else if (a_sec)   bus_rdata[7:0]  = {sign_to_trit(r_lock, 1'b0), sign_to_trit(r_noshuf, 1'b0), sign_to_trit(r_varprog, 1'b0), sign_to_trit(r_zskip, 1'b0)};
        else if (a_x)     bus_rdata = r_x[x_idx*2*WORD +: 2*WORD];
        else if (a_y)     bus_rdata[2*TRYTE-1:0] = int_to_tryte($signed(acc[y_idx*ACCW +: ACCW]));
        else if (a_prow)  bus_rdata[2*TRYTE-1:0] = r_prow;
        else if (a_pdata) bus_rdata = r_pdata;
        else if (a_piter) bus_rdata[2*TRYTE-1:0] = r_lock ? ZERO_TRYTE : int_to_tryte({4'b0, r_piter});
        else if (a_act)   bus_rdata[1:0]  = sign_to_trit(!r_lock && (^d_acc), 1'b0);
        else if (a_marg)  for (int c = 0; c < COLS; c++) bus_rdata[2*c +: 2] = sign_to_trit(m_fail[c], 1'b0);
    end

    // ------------------------------------------------------------------ helpers
    logic [2*ROWS-1:0] x_flat;
    assign x_flat = r_x;
    logic [ROWS-1:0] x_pos, x_neg, x_nz;
    always_comb for (int r = 0; r < ROWS; r++) begin
        x_pos[r] = is_pos(x_flat[2*r +: 2]);
        x_neg[r] = is_neg(x_flat[2*r +: 2]);
    end
    assign x_nz = x_pos | x_neg;                     // rows a digital product has to read

    // first row with a non-zero input at or after row 'from'; ROWS if there is none
    function automatic logic [6:0] next_nz(input logic [ROWS-1:0] nz, input logic [7:0] from);
        next_nz = 7'(ROWS);
        for (int r = ROWS - 1; r >= 0; r--) if (nz[r] && 8'(r) >= from) next_nz = 7'(r);
    endfunction
    // fixed-latency products (revision 4.6): all rows, from a start row taken from the LFSR, wrapping at 71
    // revision 4.7 (council review, 6 November 2026): every use of an option is also gated by LOCK, so that one upset of an
    // option flip-flop after LOCK cannot bring the option back; the start row is the whole 16-bit LFSR value modulo 72
    // (rows 1-15 come up 911 times and the others 910 times in the LFSR's 65,535 states) instead of its low 7 bits
    // folded once (rows 0-55 twice as often as rows 56-71)
    logic zskip_e, varprog_e, noshuf_e;
    assign zskip_e = r_zskip & ~r_lock; assign varprog_e = r_varprog & ~r_lock; assign noshuf_e = r_noshuf & ~r_lock;
    // lfsr' = 2 lfsr + fb - 65536 lfsr[15], and 65536 = 16 (mod 72): lfsr_m72' = (2 lfsr_m72 + fb - 16 lfsr[15]) mod 72
    logic       lfsr_fb;
    logic signed [8:0] m72_t;
    logic [6:0] m72_next;
    assign lfsr_fb  = lfsr[15] ^ lfsr[13] ^ lfsr[12] ^ lfsr[10];
    assign m72_t    = $signed({2'b0, lfsr_m72} + {2'b0, lfsr_m72} + {8'b0, lfsr_fb}) - (lfsr[15] ? 9'sd16 : 9'sd0);
    assign m72_next = (m72_t < 9'sd0) ? 7'(m72_t + 9'sd72) : ((m72_t >= 9'sd72) ? 7'(m72_t - 9'sd72) : 7'(m72_t));
    logic [6:0] start_row, fixed_next;
    assign start_row  = noshuf_e ? 7'd0 : lfsr_m72;
    assign fixed_next = (r_cnt == 7'(ROWS - 1)) ? 7'(ROWS) : ((arr_row == 7'(ROWS - 1)) ? 7'd0 : arr_row + 7'd1);
    logic [6:0] first_row, next_row;
    assign first_row = zskip_e ? next_nz(x_nz, 8'd0) : start_row;
    assign next_row  = zskip_e ? next_nz(x_nz, {1'b0, arr_row} + 8'd1) : fixed_next;
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
    logic [COLS*ACCW-1:0] acc_next, diff_sat, acc_upd, acc_fin, d_acc_next;
    logic                 diff_clip;
    logic                 cur_pos, cur_nz;
    always_comb begin
        acc_next = acc; diff_sat = '0; diff_clip = 1'b0;
        cur_pos  = x_pos[arr_row < 7'(ROWS) ? arr_row : 7'd0];   // input of the row whose answer arrives
        cur_nz   = x_nz[arr_row < 7'(ROWS) ? arr_row : 7'd0];
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
        // a row with input 0 (read only in fixed-latency products) changes no result; every column that does not
        // update its result accumulator updates its dummy accumulator instead (+1 or -1 from the LFSR)
        acc_upd = cur_nz ? acc_next : acc;
        for (int c = 0; c < COLS; c++) acc_fin[c*ACCW +: ACCW] = acc_upd[c*ACCW +: ACCW] - r_off;
        d_acc_next = d_acc;
`ifndef TCIM_NO_DUMMY   // defined only for the FPGA demonstration (rtl/fpga), which has no room for them (GW1NR-9)
        for (int c = 0; c < COLS; c++)
            if (!(cur_nz && (arr_sa_p[c] ^ arr_sa_n[c])))
                d_acc_next[c*ACCW +: ACCW] = lfsr[c % 16] ? d_acc[c*ACCW +: ACCW] + 10'd1 : d_acc[c*ACCW +: ACCW] - 10'd1;
`endif
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
            state <= S_IDLE; pend_p <= '0; pend_n <= '0; amp <= '0; req <= 1'b0;
            arr_op <= OP_READ; arr_row <= '0; arr_row_mask <= '0; arr_mask_p <= '0; arr_mask_n <= '0; arr_amp <= '0;
            acc <= '0;
            r_zskip <= 1'b0; r_varprog <= 1'b0; r_noshuf <= 1'b0; r_lock <= 1'b0;
            lfsr <= 16'hace1; lfsr_m72 <= 7'd49; r_off <= '0; r_cnt <= '0; m_fail <= '0; d_acc <= '0;   // 0xace1 = 44257 = 49 mod 72
        end else begin
            lfsr <= {lfsr[14:0], lfsr_fb}; lfsr_m72 <= m72_next;
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
                if (a_sec) begin                              // LOCK is set-only: once set, the options stay 0
                    if (!r_lock) begin
                        r_zskip <= is_pos(bus_wdata[1:0]); r_varprog <= is_pos(bus_wdata[3:2]); r_noshuf <= is_pos(bus_wdata[5:4]);
                    end
                    if (is_pos(bus_wdata[7:6])) begin
                        r_lock <= 1'b1; r_zskip <= 1'b0; r_varprog <= 1'b0; r_noshuf <= 1'b0;
                    end
                end
            end
            if (rd && a_stat) s_done <= 1'b0;                 // DONE is cleared by reading STAT

            case (state)
                S_IDLE: begin
                    req <= 1'b0;
                    if (go_cmd) begin
                        s_done <= 1'b0; s_sat <= 1'b0; s_werr <= 1'b0;
                        r_cnt <= '0;
                        acc <= '0;
                        if (go_analog) begin
                            arr_op <= OP_SUM; arr_row_mask <= x_pos; req <= 1'b1; state <= S_SUM_P;
                        end else if (first_row != 7'(ROWS)) begin
                            arr_op <= OP_READ; arr_row <= first_row; arr_mask_p <= '1; arr_mask_n <= '1; req <= 1'b1;
                            // revision 4.7: the result accumulators start at a random offset (-128 ... 127 from the
                            // LFSR) that is taken off again with the last row, so that which bits an update flips does
                            // not follow the partial sum around zero
                            r_off <= {{(ACCW-8){lfsr[15]}}, lfsr[15:8]}; acc <= {COLS{{(ACCW-8){lfsr[15]}}, lfsr[15:8]}};
                            state <= S_READ;
                        end else state <= S_FINISH;                  // all inputs 0: the result is 0
                    end else if (prog_cmd) begin
                        s_done <= 1'b0; s_sat <= 1'b0; s_werr <= ~prow_ok; r_piter <= '0; amp <= '0;
                        if (prow_ok) begin
                            arr_row <= prow_int[6:0];
                            pend_p <= ~w_pos; pend_n <= ~w_neg;            // devices that must be HRS
                            arr_op <= OP_VFY_RESET; arr_mask_p <= ~w_pos; arr_mask_n <= ~w_neg; req <= 1'b1;
                            state <= S_RST_VFY;
                        end else state <= S_FINISH;
                    end else if (rdbk_cmd) begin
                        // revision 4.7: under LOCK read-back is refused (WERR, no array access): LOCK must not leave
                        // the weights readable over the bus
                        s_done <= 1'b0; s_sat <= 1'b0; s_werr <= ~prow_ok | r_lock;
                        if (prow_ok && !r_lock) begin
                            arr_row <= prow_int[6:0]; arr_op <= OP_READ; arr_mask_p <= '1; arr_mask_n <= '1; req <= 1'b1;
                            state <= S_RDBK;
                        end else state <= S_FINISH;
                    end else if (mchk_cmd) begin
                        s_done <= 1'b0; s_sat <= 1'b0; s_werr <= ~prow_ok; m_fail <= '0;
                        if (prow_ok) begin
                            arr_row <= prow_int[6:0]; arr_op <= OP_READ; arr_mask_p <= '1; arr_mask_n <= '1; req <= 1'b1;
                            state <= S_MC_RD;
                        end else state <= S_FINISH;
                    end
                end

                // ---------------- digital product: one row read per non-zero input, back to back
                S_READ: if (arr_ack) begin
                    acc <= acc_upd;                              // weight = sa_p - sa_n ; both set counts as 0
                    d_acc <= d_acc_next; r_cnt <= r_cnt + 7'd1;
                    if (|(arr_sa_p & arr_sa_n)) s_werr <= 1'b1;
                    if (next_row == 7'(ROWS)) begin
                        req <= 1'b0; state <= S_FINISH; acc <= acc_fin;   // the last row: offset taken off (revision 4.7)
                    end else arr_row <= next_row;               // req stays high: the next row is the next request
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
                    if (((pend_p & arr_sa_p) | (pend_n & arr_sa_n)) == '0 && (varprog_e || amp == 5'(AMP_STEPS))) begin
                        amp <= '0; pend_p <= w_pos; pend_n <= w_neg;        // devices that must be LRS
                        arr_op <= OP_VFY_SET; arr_mask_p <= w_pos; arr_mask_n <= w_neg; state <= S_SET_VFY;
                    end else if (amp == 5'(AMP_STEPS) && !varprog_e) begin  // constant time: the set phase runs, with empty pulses only
                        s_werr <= 1'b1; amp <= '0; pend_p <= '0; pend_n <= '0;
                        arr_op <= OP_VFY_SET; arr_mask_p <= w_pos; arr_mask_n <= w_neg; state <= S_SET_VFY;
                    end else if (amp == 5'(AMP_STEPS)) begin
                        s_werr <= 1'b1; req <= 1'b0; state <= S_FINISH;
                    end else begin
                        arr_op <= OP_PULSE_RST; arr_amp <= amp; arr_mask_p <= pend_p & arr_sa_p; arr_mask_n <= pend_n & arr_sa_n;
                        state <= S_RST_PULSE;
                    end
                end
                S_RST_PULSE: if (arr_ack) begin
                    amp <= amp + 5'd1; r_piter <= r_piter + 6'(|{arr_mask_p, arr_mask_n});
                    arr_op <= OP_VFY_RESET; state <= S_RST_VFY;
                end
                S_SET_VFY: if (arr_ack) begin
                    pend_p <= pend_p & ~arr_sa_p; pend_n <= pend_n & ~arr_sa_n;
                    if (((pend_p & ~arr_sa_p) | (pend_n & ~arr_sa_n)) == '0 && (varprog_e || amp == 5'(AMP_STEPS))) begin
                        req <= 1'b0; state <= S_FINISH;
                    end else if (amp == 5'(AMP_STEPS)) begin
                        s_werr <= 1'b1; req <= 1'b0; state <= S_FINISH;
                    end else begin
                        arr_op <= OP_PULSE_SET; arr_amp <= amp; arr_mask_p <= pend_p & ~arr_sa_p; arr_mask_n <= pend_n & ~arr_sa_n;
                        state <= S_SET_PULSE;
                    end
                end
                S_SET_PULSE: if (arr_ack) begin
                    amp <= amp + 5'd1; r_piter <= r_piter + 6'(|{arr_mask_p, arr_mask_n});
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

                // ---------------- margin check (revision 4.6): read at the mid reference, then at the set and reset targets
                S_MC_RD: if (arr_ack) begin
                    if (!r_lock) begin                           // (revision 4.7: not under LOCK)
                        for (int c = 0; c < COLS; c++)           // the weights as read-back would return them
                            r_pdata[2*c +: 2] <= sign_to_trit(arr_sa_p[c] && !arr_sa_n[c], arr_sa_n[c] && !arr_sa_p[c]);
                        for (int c = COLS; c < WORD; c++) r_pdata[2*c +: 2] <= T_ZERO;
                    end
                    if (|(arr_sa_p & arr_sa_n)) s_werr <= 1'b1;
                    pend_p <= arr_sa_p; pend_n <= arr_sa_n;     // devices above the read reference
                    arr_op <= OP_VFY_SET; state <= S_MC_SET;     // req stays high
                end
                S_MC_SET: if (arr_ack) begin
                    m_fail <= (pend_p & ~arr_sa_p) | (pend_n & ~arr_sa_n);   // low-resistance but below the set target
                    arr_op <= OP_VFY_RESET; state <= S_MC_RST;
                end
                S_MC_RST: if (arr_ack) begin                    // high-resistance but above the reset target
                    m_fail <= m_fail | (~pend_p & arr_sa_p) | (~pend_n & arr_sa_n);
                    if ((m_fail | (~pend_p & arr_sa_p) | (~pend_n & arr_sa_n)) != '0) s_werr <= 1'b1;
                    req <= 1'b0; state <= S_FINISH;
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
    logic [2:0] f_cmd;                   // last accepted command: 1 digital, 2 analog, 3 program, 4 read-back, 5 margin check
    logic       f_lock;                  // LOCK in the previous cycle
    logic [6:0] f_row;                   // row of the last program or read-back command
    logic       f_seen_set;              // a set pulse has been issued in the present command
    logic [8:0] f_busy_cnt;              // clock cycles since the present command started
    logic [2*WORD-1:0] f_pdata;          // PDATA at the start of the command
    logic [ROWS-1:0] f_read;             // rows answered so far in the present digital product
    logic [7:0]      f_last;             // last row answered in it (8'hff before the first answer)
    logic [ROWS-1:0] f_nz;               // rows with a non-zero input, decoded here independently of x_nz
    logic            f_was_busy;         // s_busy in the previous cycle
    logic            f_start;            // a command was accepted in the previous cycle
    logic [6:0]      f_srow;             // first row of the present digital product (revision 4.6)
    logic [7:0]      f_cnt;              // rows answered so far in the present digital product (revision 4.6)
    always_comb for (int r = 0; r < ROWS; r++) f_nz[r] = (r_x[2*r +: 2] == T_POS) || (r_x[2*r +: 2] == T_NEG);
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
            f_cmd <= '0; f_row <= '0; f_seen_set <= 1'b0; f_busy_cnt <= '0; f_pdata <= '0; f_read <= '0; f_last <= 8'hff; f_was_busy <= 1'b0; f_start <= 1'b0;
            f_lock <= 1'b0; f_srow <= '0; f_cnt <= '0;
        end else begin
            f_was_busy <= s_busy;
            f_lock <= r_lock;
            f_start <= go_cmd | prog_cmd | rdbk_cmd | mchk_cmd;
            if (go_cmd)        begin f_cmd <= go_analog ? 3'd2 : 3'd1; f_seen_set <= 1'b0; f_busy_cnt <= '0; f_read <= '0; f_last <= 8'hff; f_srow <= first_row; f_cnt <= '0; end
            else if (prog_cmd) begin f_cmd <= 3'd3; f_row <= prow_int[6:0]; f_seen_set <= 1'b0; f_busy_cnt <= '0; f_pdata <= r_pdata; end
            else if (rdbk_cmd) begin f_cmd <= 3'd4; f_row <= prow_int[6:0]; f_seen_set <= 1'b0; f_busy_cnt <= '0; end
            else if (mchk_cmd) begin f_cmd <= 3'd5; f_row <= prow_int[6:0]; f_seen_set <= 1'b0; f_busy_cnt <= '0; f_pdata <= r_pdata; end
            else begin
                if (s_busy && f_busy_cnt != 9'h1ff) f_busy_cnt <= f_busy_cnt + 9'd1;
                if (f_pulse && arr_op == OP_PULSE_SET) f_seen_set <= 1'b1;
                if (f_cmd == 3'd1 && state == S_READ && arr_ack) begin f_read[arr_row] <= 1'b1; f_last <= {1'b0, arr_row}; f_cnt <= f_cnt + 8'd1; end
            end
        end
        if (!f_init && rst_n) begin
            // the array is never asked about a row that does not exist
            if (req && arr_op != OP_SUM) assert (arr_row < 7'(ROWS));
            // pulses happen only inside a program command, on its row, with the stored weights unchanged
            if (f_pulse) assert (s_busy && f_cmd == 3'd3 && arr_row == f_row);
            // verify reads only inside a program command or a margin check (revision 4.6), on its row
            if (f_vfy)   assert (s_busy && (f_cmd == 3'd3 || f_cmd == 3'd5) && arr_row == f_row);
            if (f_cmd == 3'd3 && s_busy) assert (r_pdata == f_pdata);
            // pulse amplitude stays inside the published scheme (and, with VARPROG, every pulse selects at least one device)
            if (f_pulse) assert (arr_amp < 5'(AMP_STEPS));
            // (revision 4.6: empty padding pulses only in constant-time programming)
            if (f_pulse && r_varprog) assert ((arr_mask_p | arr_mask_n) != '0);
            // a pulse only reaches devices that must change: set only where the weight needs LRS, reset only where HRS
            if (f_pulse && arr_op == OP_PULSE_SET) assert ((arr_mask_p & ~w_pos) == '0 && (arr_mask_n & ~w_neg) == '0);
            if (f_pulse && arr_op == OP_PULSE_RST) assert ((arr_mask_p & w_pos) == '0 && (arr_mask_n & w_neg) == '0);
            // within one command no reset pulse follows a set pulse
            if (f_pulse && arr_op == OP_PULSE_RST) assert (!f_seen_set);
            // at most 21 reset and 21 set pulses per command
            assert (r_piter <= 6'(2 * AMP_STEPS));
            // (lemmas for it: one pulse step raises the amplitude by one and the count by at most one)
            if (f_cmd == 3'd3 && (state == S_RST_VFY || state == S_RST_PULSE)) assert (amp <= 5'(AMP_STEPS) && {1'b0, r_piter} <= {2'b0, amp});
            if (f_cmd == 3'd3 && (state == S_SET_VFY || state == S_SET_PULSE)) assert (amp <= 5'(AMP_STEPS) && {1'b0, r_piter} <= 7'(AMP_STEPS) + {2'b0, amp});
            // products and read-back never write the array
            if (f_cmd == 3'd1 || f_cmd == 3'd2 || f_cmd == 3'd4 || f_cmd == 3'd5) assert (!f_pulse);
            if (f_cmd == 3'd5 && req) assert (arr_row == f_row);
            // digital product: a result never exceeds the number of rows (checked on column 0; the columns are alike)
            // (revision 4.7: while the product runs the accumulators also hold the offset; the bound is on the result)
            if (f_cmd == 3'd1 && state != S_READ) assert ($signed(acc[ACCW-1:0]) <= 10'sd72 && $signed(acc[ACCW-1:0]) >= -10'sd72);
            // digital product: only rows with a non-zero input are read, each once, in increasing order, and the
            // product ends only when all of them have been read
            if (f_cmd == 3'd1 && r_zskip && req && arr_op == OP_READ) assert (f_nz[arr_row] && (f_last == 8'hff || {1'b0, arr_row} > f_last));
            if (f_cmd == 3'd1 && r_zskip && s_busy) assert ((f_read & ~f_nz) == '0);
            if (f_cmd == 3'd1 && r_zskip && state == S_FINISH) assert (f_read == f_nz);
            // constant activity (revision 4.6): in every row read of a product each column updates exactly one of its
            // result accumulator and its dummy accumulator (a +1 / -1 update always changes the value)
            if (f_cmd == 3'd1 && state == S_READ && arr_ack)
                for (int c = 0; c < COLS; c++)
                    assert ((acc_upd[c*ACCW +: ACCW] != acc[c*ACCW +: ACCW]) != (d_acc_next[c*ACCW +: ACCW] != d_acc[c*ACCW +: ACCW]));
            // fixed-latency product (revision 4.6): every row is read exactly once, whatever the inputs. Stated as: the
            // k-th row answered (k = 0 ... 71) is (start row + k) modulo 72, and the product ends after exactly 72
            // answers; 72 consecutive rows modulo 72 are the 72 rows, each once. f_cnt counts the answers here,
            // independently of the logic's own counter.
            if (f_cmd == 3'd1 && !r_zskip && state == S_READ)
                assert (f_cnt < 8'(ROWS) && f_srow < 7'(ROWS) &&
                        {1'b0, arr_row} == (({1'b0, f_srow} + f_cnt >= 8'(ROWS)) ? {1'b0, f_srow} + f_cnt - 8'(ROWS) : {1'b0, f_srow} + f_cnt));
            if (f_cmd == 3'd1 && !r_zskip && state == S_FINISH) assert (f_cnt == 8'(ROWS));
            // with NOSHUF the window starts at row 0 (council, 6 November 2026: f_srow alone is the logic's own start row)
            if (f_cmd == 3'd1 && !r_zskip && r_noshuf && state == S_READ) assert (f_srow == 7'd0);
            // a digital product keeps asking for reads, back to back, until it ends
            if (f_cmd == 3'd1 && state == S_READ) assert (req && arr_op == OP_READ);
            // (lemmas for the bound on the result above: one answer changes a result by at most 1; with zero-skipping
            // the answers come from increasing rows, so there are at most 72)
            if (f_cmd == 3'd1) assert (f_cnt <= 8'(ROWS));
            if (f_cmd == 3'd1 && state != S_READ) assert ($signed(acc[ACCW-1:0]) <= $signed({2'b0, f_cnt}) && $signed(acc[ACCW-1:0]) >= -$signed({2'b0, f_cnt}));
            if (f_cmd == 3'd1 && state == S_READ) assert (r_off >= -10'sd128 && r_off <= 10'sd127 &&
                $signed({acc[ACCW-1], acc[ACCW-1:0]}) - $signed({r_off[ACCW-1], r_off}) <= $signed({3'b0, f_cnt}) &&
                $signed({acc[ACCW-1], acc[ACCW-1:0]}) - $signed({r_off[ACCW-1], r_off}) >= -$signed({3'b0, f_cnt}));
            if (f_cmd == 3'd1 && r_zskip && state == S_READ) assert (f_cnt <= {1'b0, arr_row});
            // LOCK is set-only, and while it is set the options are off and PITER reads 0
            if (f_lock) assert (r_lock);
            if (r_lock) assert (!r_zskip && !r_varprog && !r_noshuf);
            if (r_lock && a_piter) assert (bus_rdata == ZERO_WORD);
            if (r_lock && a_act) assert (bus_rdata == ZERO_WORD);
            // revision 4.7: under LOCK no read-back runs, and a margin check leaves PDATA as it was
            if (r_lock) assert (state != S_RDBK);
            if (r_lock && f_cmd == 3'd5 && s_busy) assert (r_pdata == f_pdata);
            // revision 4.7: the start-row register is the LFSR value modulo 72
            assert (lfsr_m72 == 7'(lfsr % 16'd72));
            // every command that ends sets DONE (revision 4.2: also a product with an all-zero input)
            if (f_was_busy && !s_busy) assert (s_done);
            // every accepted command either runs (BUSY) or has already ended with DONE: none is dropped
            if (f_start) assert (s_busy || s_done);
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
