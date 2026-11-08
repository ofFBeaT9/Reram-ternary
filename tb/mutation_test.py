"""Mutation test of the TCIM0 test bench: inject one deliberate bug at a time into the RTL and check that the
test bench fails. A mutant that survives points at something the test bench does not check.

Usage: python3 tb/mutation_test.py [first] [last]      (needs yosys with slang, a C++ compiler)
       python3 tb/mutation_test.py count               (prints the number of faults)
Environment: TB_SRC = another test bench to evaluate, TB_TAG = suffix for its result files,
TB_ENC=pnx = build the RTL and the test bench with the BSD-PNX trit code and add the faults of list MP.
Writes results/rtl_mutation<TAG>_<first>_<last>.json; tb/mutation_merge.py joins the parts."""
import json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = ["tcim_pkg.sv", "tcim_core.sv", "tcim_spi.sv", "tcim_top.sv"]
CXXRTL = subprocess.run(["yosys-config", "--datdir"], capture_output=True, text=True).stdout.strip() + "/include/backends/cxxrtl/runtime"
TB_SRC = Path(os.environ.get("TB_SRC", ROOT / "tb" / "tb_tcim.cc"))       # test bench to evaluate
PNX = os.environ.get("TB_ENC", "") == "pnx"                                # second trit code
TAG = os.environ.get("TB_TAG", "_pnx" if PNX else "")                      # suffix of the result file and work folders
DEFS = ["-DTCIM_ENC_PNX"] if PNX else []

# (name, file, text to replace (must occur exactly once), replacement)
M = [
    ("sign of a +1 weight in the accumulator", "tcim_core.sv",
     "if (arr_sa_p[c] & ~arr_sa_n[c])      acc_next[c*ACCW +: ACCW] = cur_pos ? a + 10'sd1 : a - 10'sd1;",
     "if (arr_sa_p[c] & ~arr_sa_n[c])      acc_next[c*ACCW +: ACCW] = cur_pos ? a - 10'sd1 : a + 10'sd1;"),
    ("sign of a -1 weight in the accumulator", "tcim_core.sv",
     "else if (arr_sa_n[c] & ~arr_sa_p[c]) acc_next[c*ACCW +: ACCW] = cur_pos ? a - 10'sd1 : a + 10'sd1;",
     "else if (arr_sa_n[c] & ~arr_sa_p[c]) acc_next[c*ACCW +: ACCW] = cur_pos ? a + 10'sd1 : a - 10'sd1;"),
    ("a cell with both devices in LRS counted as +1", "tcim_core.sv",
     "if (arr_sa_p[c] & ~arr_sa_n[c])      acc_next", "if (arr_sa_p[c])      acc_next"),
    ("last row never read", "tcim_core.sv", "for (int r = ROWS - 1; r >= 0; r--) if (nz[r]", "for (int r = ROWS - 2; r >= 0; r--) if (nz[r]"),
    ("rows with a -1 input skipped", "tcim_core.sv", "assign x_nz = x_pos | x_neg;", "assign x_nz = x_pos;"),
    ("rows with a 0 input read as well", "tcim_core.sv", "assign x_nz = x_pos | x_neg;", "assign x_nz = '1;"),
    ("invalid cell not flagged during a product", "tcim_core.sv",
     "if (|(arr_sa_p & arr_sa_n)) s_werr <= 1'b1;\n                    if (next_row == 7'(ROWS)) begin",
     "if (next_row == 7'(ROWS)) begin"),
    ("invalid cell not flagged during read-back", "tcim_core.sv",
     "if (|(arr_sa_p & arr_sa_n)) s_werr <= 1'b1;\n                    state <= S_FINISH;", "state <= S_FINISH;"),
    ("wrong row sent to the array in a product", "tcim_core.sv",
     "arr_op <= OP_READ; arr_row <= first_row; arr_mask_p <= '1;", "arr_op <= OP_READ; arr_row <= '0; arr_mask_p <= '1;"),
    ("product read uses the set-verify reference", "tcim_core.sv",
     "arr_op <= OP_READ; arr_row <= first_row; arr_mask_p <= '1;", "arr_op <= OP_VFY_SET; arr_row <= first_row; arr_mask_p <= '1;"),
    ("reset phase skipped when programming", "tcim_core.sv",
     "pend_p <= ~w_pos; pend_n <= ~w_neg;            // devices that must be HRS", "pend_p <= '0; pend_n <= '0;"),
    ("set phase programs the wrong side", "tcim_core.sv",
     "amp <= '0; pend_p <= w_pos; pend_n <= w_neg;        // devices that must be LRS", "amp <= '0; pend_p <= w_neg; pend_n <= w_pos;"),
    ("reset verify polarity", "tcim_core.sv", "pend_p <= pend_p & arr_sa_p; pend_n <= pend_n & arr_sa_n;", "pend_p <= pend_p & ~arr_sa_p; pend_n <= pend_n & arr_sa_n;"),
    ("set verify polarity", "tcim_core.sv", "pend_p <= pend_p & ~arr_sa_p; pend_n <= pend_n & ~arr_sa_n;", "pend_p <= pend_p & ~arr_sa_p; pend_n <= pend_n & arr_sa_n;"),
    ("no pulse limit in the reset phase", "tcim_core.sv",
     "end else if (amp == 5'(AMP_STEPS)) begin\n                        s_werr <= 1'b1; req <= 1'b0; state <= S_FINISH;\n                    end else begin\n                        arr_op <= OP_PULSE_RST;",
     "end else if (1'b0) begin\n                        s_werr <= 1'b1; req <= 1'b0; state <= S_FINISH;\n                    end else begin\n                        arr_op <= OP_PULSE_RST;"),
    ("no pulse limit in the set phase", "tcim_core.sv",
     "end else if (amp == 5'(AMP_STEPS)) begin\n                        s_werr <= 1'b1; req <= 1'b0; state <= S_FINISH;\n                    end else begin\n                        arr_op <= OP_PULSE_SET;",
     "end else if (1'b0) begin\n                        s_werr <= 1'b1; req <= 1'b0; state <= S_FINISH;\n                    end else begin\n                        arr_op <= OP_PULSE_SET;"),
    ("verify failure not reported (set phase)", "tcim_core.sv",
     "s_werr <= 1'b1; req <= 1'b0; state <= S_FINISH;\n                    end else begin\n                        arr_op <= OP_PULSE_SET;",
     "req <= 1'b0; state <= S_FINISH;\n                    end else begin\n                        arr_op <= OP_PULSE_SET;"),
    ("pulse amplitude not driven", "tcim_core.sv", "arr_op <= OP_PULSE_SET; arr_amp <= amp;", "arr_op <= OP_PULSE_SET; arr_amp <= '0;"),
    ("set pulses not counted in PITER", "tcim_core.sv",
     "amp <= amp + 5'd1; r_piter <= r_piter + 6'(|{arr_mask_p, arr_mask_n});\n                    arr_op <= OP_VFY_SET;", "amp <= amp + 5'd1;\n                    arr_op <= OP_VFY_SET;"),
    ("reset pulses not counted in PITER", "tcim_core.sv",
     "amp <= amp + 5'd1; r_piter <= r_piter + 6'(|{arr_mask_p, arr_mask_n});\n                    arr_op <= OP_VFY_RESET;", "amp <= amp + 5'd1;\n                    arr_op <= OP_VFY_RESET;"),
    ("analog difference has the wrong sign", "tcim_core.sv", "d = {a[ACCW-1], a} - {arr_adc", "d = {a[ACCW-1], a} + {arr_adc"),
    ("analog phases use the same rows", "tcim_core.sv", "arr_row_mask <= x_neg; req <= 1'b1; state <= S_SUM_N;", "arr_row_mask <= x_pos; req <= 1'b1; state <= S_SUM_N;"),
    ("positive clip limit off by one", "tcim_core.sv", "if (d > 11'sd364)       begin", "if (d > 11'sd365)       begin"),
    ("negative clip limit off by one", "tcim_core.sv", "else if (d < -11'sd364) begin", "else if (d < -11'sd365) begin"),
    ("SAT flag never set", "tcim_core.sv", "s_sat <= diff_clip;", "s_sat <= 1'b0;"),
    ("DONE not cleared by reading STAT", "tcim_core.sv", "if (rd && a_stat) s_done <= 1'b0;", ""),
    ("interrupt ignores the enable trit", "tcim_core.sv", "assign irq     = r_ie & s_done;", "assign irq     = s_done;"),
    ("row index 72 accepted", "tcim_core.sv", "(prow_int < ROWS_S)", "(prow_int <= ROWS_S)"),
    ("negative row index accepted", "tcim_core.sv", "(prow_int >= 10'sd0) && (prow_int < ROWS_S)", "(prow_int < ROWS_S)"),
    ("read-back swaps +1 and -1", "tcim_core.sv",
     "sign_to_trit(arr_sa_p[c] & ~arr_sa_n[c], arr_sa_n[c] & ~arr_sa_p[c])", "sign_to_trit(arr_sa_n[c] & ~arr_sa_p[c], arr_sa_p[c] & ~arr_sa_n[c])"),
    ("register writes accepted while busy", "tcim_core.sv", "if (wr && !s_busy) begin", "if (wr) begin"),
    ("program command works without EN", "tcim_core.sv", "is_pos(bus_wdata[1:0]) & ~s_busy & r_en;\n    assign rdbk_cmd", "is_pos(bus_wdata[1:0]) & ~s_busy;\n    assign rdbk_cmd"),
    ("GO works without EN", "tcim_core.sv", "is_pos(bus_wdata[7:6]) & is_pos(bus_wdata[1:0]) & ~s_busy;", "is_pos(bus_wdata[7:6]) & ~s_busy;"),
    ("MODE read from the wrong trit", "tcim_core.sv", "assign go_analog = is_pos(bus_wdata[5:4]);", "assign go_analog = is_pos(bus_wdata[3:2]);"),
    ("WERR not cleared by GO", "tcim_core.sv", "s_done <= 1'b0; s_sat <= 1'b0; s_werr <= 1'b0;", "s_done <= 1'b0; s_sat <= 1'b0;"),
    ("X1 and X2 exchanged", "tcim_core.sv", "(bus_addr == 6'd8) ? 2'd1 : 2'd2;", "(bus_addr == 6'd8) ? 2'd2 : 2'd1;"),
    ("Y index off by one", "tcim_core.sv", "y_idx   = 5'(bus_addr - 6'd16);", "y_idx   = 5'(bus_addr - 6'd15);"),
    ("tryte access to a word register accepted", "tcim_core.sv", "a_x     = bus_word && (bus_addr == 6'd4", "a_x     = (bus_addr == 6'd4"),
    ("balanced-ternary conversion: digit -1 written as +1", "tcim_pkg.sv", "t[2*i +: 2] = T_NEG; q = (q + 1) / 3;", "t[2*i +: 2] = T_POS; q = (q + 1) / 3;"),
    ("balanced-ternary conversion: wrong carry", "tcim_pkg.sv", "t[2*i +: 2] = T_NEG; q = (q + 1) / 3;", "t[2*i +: 2] = T_NEG; q = q / 3;"),
    ("tryte decoding uses base 2", "tcim_pkg.sv", "w = w * 10'sd3;", "w = w * 10'sd2;"),
    ("code 10 treated as -1", "tcim_pkg.sv", "function automatic logic is_neg(input logic [1:0] t); return t == T_NEG; endfunction",
     "function automatic logic is_neg(input logic [1:0] t); return t[1]; endfunction"),
    ("serial port: error flag not reported", "tcim_spi.sv", "7'd61: miso <= err_latch;", "7'd61: miso <= 1'b0;"),
    ("serial port: interrupt flag not reported", "tcim_spi.sv", "7'd62: miso <= irq;", "7'd62: miso <= 1'b0;"),
    ("serial port: write strobe one bit early", "tcim_spi.sv", "if (bitcnt == 7'd55 && cmd[7]) begin", "if (bitcnt == 7'd54 && cmd[7]) begin"),
    ("serial port: address bit lost", "tcim_spi.sv", "bus_addr <= {cmd[4:0], mosi_s[1]};", "bus_addr <= {cmd[4:0], 1'b0};"),
    ("serial port: read data shifted by one bit", "tcim_spi.sv", "miso <= cmd[7] ? 1'b0 : shift_out[47];", "miso <= cmd[7] ? 1'b0 : shift_out[46];"),
    ("serial port: word flag ignored", "tcim_spi.sv", "bus_word <= cmd[5];", "bus_word <= 1'b0;"),
    # ---- second round (audit): behaviour of revision 3 that the audit changed, and protocol faults
    ("interrupt held by WERR (revision 3 behaviour)", "tcim_core.sv", "assign irq     = r_ie & s_done;", "assign irq     = r_ie & (s_done | s_werr);"),
    ("serial port: bit counter wraps on a long frame (revision 3 behaviour)", "tcim_spi.sv", "if (!bitcnt[6]) bitcnt <= bitcnt + 7'd1;", "bitcnt <= bitcnt + 7'd1;"),
    ("set pulses repeated on devices that already passed verify", "tcim_core.sv",
     "arr_op <= OP_PULSE_SET; arr_amp <= amp; arr_mask_p <= pend_p & ~arr_sa_p; arr_mask_n <= pend_n & ~arr_sa_n;",
     "arr_op <= OP_PULSE_SET; arr_amp <= amp; arr_mask_p <= w_pos; arr_mask_n <= w_neg;"),
    ("reset pulses repeated on devices that already passed verify", "tcim_core.sv",
     "arr_op <= OP_PULSE_RST; arr_amp <= amp; arr_mask_p <= pend_p & arr_sa_p; arr_mask_n <= pend_n & arr_sa_n;",
     "arr_op <= OP_PULSE_RST; arr_amp <= amp; arr_mask_p <= ~w_pos; arr_mask_n <= ~w_neg;"),
    ("set amplitude not restarted after the reset phase", "tcim_core.sv",
     "amp <= '0; pend_p <= w_pos; pend_n <= w_neg;        // devices that must be LRS", "pend_p <= w_pos; pend_n <= w_neg;"),
    ("amplitude not restarted by a new program command", "tcim_core.sv", "s_werr <= ~prow_ok; r_piter <= '0; amp <= '0;", "s_werr <= ~prow_ok; r_piter <= '0;"),
    ("PITER not restarted by a new program command", "tcim_core.sv", "s_werr <= ~prow_ok; r_piter <= '0; amp <= '0;", "s_werr <= ~prow_ok; amp <= '0;"),
    ("accumulators not cleared by GO", "tcim_core.sv", "                        acc <= '0;\n                        if (go_analog) begin", "                        if (go_analog) begin"),
    ("SAT not cleared by GO", "tcim_core.sv", "s_done <= 1'b0; s_sat <= 1'b0; s_werr <= 1'b0;", "s_done <= 1'b0; s_werr <= 1'b0;"),
    ("SAT not cleared by a read-back command", "tcim_core.sv",
     "                        s_done <= 1'b0; s_sat <= 1'b0; s_werr <= ~prow_ok | r_lock;\n", "                        s_done <= 1'b0; s_werr <= ~prow_ok | r_lock;\n"),
    ("DONE not cleared by GO", "tcim_core.sv", "s_done <= 1'b0; s_sat <= 1'b0; s_werr <= 1'b0;", "s_sat <= 1'b0; s_werr <= 1'b0;"),
    ("DONE never set", "tcim_core.sv", "req <= 1'b0; s_done <= 1'b1; state <= S_IDLE;", "req <= 1'b0; state <= S_IDLE;"),
    ("MODE changed while busy", "tcim_core.sv", "if (!s_busy) r_mode <= is_pos(bus_wdata[5:4]);", "r_mode <= is_pos(bus_wdata[5:4]);"),
    # found by the gate-level clock-gating fault of the SKY130 chip block on 11 October 2026: nothing read the mode bit back
    ("CTRL mode bit never stored", "tcim_core.sv", "if (!s_busy) r_mode <= is_pos(bus_wdata[5:4]);", "if (!s_busy) r_mode <= 1'b0;"),
    ("read-back works without EN", "tcim_core.sv", "is_neg(bus_wdata[1:0]) & ~s_busy & r_en;", "is_neg(bus_wdata[1:0]) & ~s_busy;"),
    ("serial port: a write frame also launches a read", "tcim_spi.sv", "if (!cmd[6]) bus_re <= 1'b1;", "bus_re <= 1'b1;"),
    ("first row never read", "tcim_core.sv", "next_nz(x_nz, 8'd0) : start_row", "next_nz(x_nz, 8'd1) : start_row"),
    ("pulse limit one step short", "tcim_pkg.sv", "localparam int AMP_STEPS = 21;", "localparam int AMP_STEPS = 20;"),
    ("read-back of an invalid cell returns +1", "tcim_core.sv",
     "sign_to_trit(arr_sa_p[c] & ~arr_sa_n[c], arr_sa_n[c] & ~arr_sa_p[c])", "sign_to_trit(arr_sa_p[c], arr_sa_n[c] & ~arr_sa_p[c])"),
    ("result conversion: remainder 2 gives +1 instead of -1", "tcim_pkg.sv",
     "t[2*i +: 2] = T_NEG; q = (q + 1) / 3;", "t[2*i +: 2] = T_POS; q = (q + 1) / 3;"),
    ("result conversion: table read with a signed index (negative results read as 0)", "tcim_pkg.sv",
     "return TRYTE_TABLE[$unsigned(v)]; ", "return TRYTE_TABLE[v]; "),
    ("result conversion: table read one entry too high", "tcim_pkg.sv",
     "return TRYTE_TABLE[$unsigned(v)]; ", "return TRYTE_TABLE[$unsigned(v + 10'sd1)]; "),
    # ---- revision 4.2: back-to-back row reads in a digital product
    ("product: the row after a read is the next row, not the next non-zero row", "tcim_core.sv",
     "end else arr_row <= next_row;", "end else arr_row <= arr_row + 7'd1;"),
    ("product: the next row search starts at the row just read (same row again)", "tcim_core.sv",
     "{1'b0, arr_row} + 8'd1", "{1'b0, arr_row}"),
    ("product: request dropped between rows", "tcim_core.sv",
     "end else arr_row <= next_row;", "end else begin arr_row <= next_row; req <= 1'b0; end"),
    ("product: an all-zero input vector never finishes", "tcim_core.sv",
     "end else state <= S_FINISH;                  // all inputs 0", "end else state <= S_IDLE;                  // all inputs 0"),
    ("product: accumulation uses the input of the next row", "tcim_core.sv",
     "cur_pos  = x_pos[arr_row < 7'(ROWS) ? arr_row : 7'd0];", "cur_pos  = x_pos[next_row < 7'(ROWS) ? next_row : 7'd0];"),
    # ---- revision 4.6 (security study, 4 November 2026): fixed-latency products, shuffle, constant-time programming,
    # SEC / LOCK, margin check. The dummy accumulators change no result by design; ACT (+50) shows their parity, which
    # keeps them through synthesis and lets the test bench see them run.
    ("fixed latency: rows with input 0 change the result", "tcim_core.sv", "acc_upd = cur_nz ? acc_next : acc;", "acc_upd = acc_next;"),
    ("fixed latency: product ends one row early", "tcim_core.sv", "(r_cnt == 7'(ROWS - 1)) ? 7'(ROWS)", "(r_cnt == 7'(ROWS - 2)) ? 7'(ROWS)"),
    ("fixed latency: no wrap from row 71 to row 0", "tcim_core.sv", "((arr_row == 7'(ROWS - 1)) ? 7'd0 : arr_row + 7'd1)", "(arr_row + 7'd1)"),
    ("fixed latency: read counter not advanced", "tcim_core.sv", "d_acc <= d_acc_next; r_cnt <= r_cnt + 7'd1;", "d_acc <= d_acc_next;"),
    ("fixed latency: read counter not cleared by GO", "tcim_core.sv", "r_cnt <= '0;\n                        acc <= '0;", "acc <= '0;"),
    ("shuffle: start row always 0", "tcim_core.sv", "assign start_row  = noshuf_e ? 7'd0 :", "assign start_row  = 1'b1 ? 7'd0 :"),
    ("shuffle: start row may exceed 71", "tcim_core.sv", "(m72_t >= 9'sd72) ? 7'(m72_t - 9'sd72)", "(m72_t >= 9'sd127) ? 7'(m72_t - 9'sd72)"),
    ("shuffle: LFSR stuck", "tcim_core.sv", "lfsr <= {lfsr[14:0], lfsr_fb}; lfsr_m72 <= m72_next;", ""),
    ("shuffle: NOSHUF ignored", "tcim_core.sv", "assign start_row  = noshuf_e ? 7'd0 :", "assign start_row  = 1'b0 ? 7'd0 :"),
    ("ZSKIP ignored", "tcim_core.sv", "assign first_row = zskip_e ? next_nz", "assign first_row = 1'b0 ? next_nz"),
    ("constant time: reset phase stops at verify", "tcim_core.sv",
     "== '0 && (varprog_e || amp == 5'(AMP_STEPS))) begin\n                        amp <= '0;", "== '0 && (1'b1 || amp == 5'(AMP_STEPS))) begin\n                        amp <= '0;"),
    ("constant time: set phase stops at verify", "tcim_core.sv",
     "== '0 && (varprog_e || amp == 5'(AMP_STEPS))) begin\n                        req <= 1'b0;", "== '0 && (1'b1 || amp == 5'(AMP_STEPS))) begin\n                        req <= 1'b0;"),
    ("constant time: a failed reset phase ends the command", "tcim_core.sv", "end else if (amp == 5'(AMP_STEPS) && !varprog_e) begin", "end else if (1'b0) begin"),
    ("constant time: set pulses after a failed reset phase", "tcim_core.sv",
     "s_werr <= 1'b1; amp <= '0; pend_p <= '0; pend_n <= '0;", "s_werr <= 1'b1; amp <= '0; pend_p <= w_pos; pend_n <= w_neg;"),
    ("constant time: failed reset phase not reported", "tcim_core.sv",
     "s_werr <= 1'b1; amp <= '0; pend_p <= '0; pend_n <= '0;", "amp <= '0; pend_p <= '0; pend_n <= '0;"),
    ("PITER counts empty pulses", "tcim_core.sv",
     "r_piter <= r_piter + 6'(|{arr_mask_p, arr_mask_n});\n                    arr_op <= OP_VFY_RESET;", "r_piter <= r_piter + 6'd1;\n                    arr_op <= OP_VFY_RESET;"),
    ("SEC: VARPROG read from the wrong trit", "tcim_core.sv", "r_varprog <= is_pos(bus_wdata[3:2]);", "r_varprog <= is_pos(bus_wdata[5:4]);"),
    ("SEC: address not mapped", "tcim_core.sv", "a_sec   = (bus_addr == 6'd3)  && !bus_word;", "a_sec   = 1'b0;"),
    ("LOCK cleared by a write", "tcim_core.sv",
     "                    if (is_pos(bus_wdata[7:6])) begin\n                        r_lock <= 1'b1;",
     "                    r_lock <= is_pos(bus_wdata[7:6]);\n                    if (is_pos(bus_wdata[7:6])) begin\n                        r_lock <= 1'b1;"),
    ("LOCK does not block option writes", "tcim_core.sv", "if (!r_lock) begin\n                        r_zskip", "if (1'b1) begin\n                        r_zskip"),
    ("LOCK does not clear the options", "tcim_core.sv", "r_lock <= 1'b1; r_zskip <= 1'b0; r_varprog <= 1'b0; r_noshuf <= 1'b0;", "r_lock <= 1'b1;"),
    ("LOCK does not hide PITER", "tcim_core.sv", "r_lock ? ZERO_TRYTE : int_to_tryte({4'b0, r_piter})", "int_to_tryte({4'b0, r_piter})"),
    ("LOCK not cleared by reset", "tcim_core.sv", "r_noshuf <= 1'b0; r_lock <= 1'b0;", "r_noshuf <= 1'b0; r_lock <= r_lock;"),
    ("margin check: low-resistance device below the set target not flagged", "tcim_core.sv",
     "m_fail <= (pend_p & ~arr_sa_p) | (pend_n & ~arr_sa_n);", "m_fail <= '0;"),
    ("margin check: BL- devices not checked against the set target", "tcim_core.sv",
     "m_fail <= (pend_p & ~arr_sa_p) | (pend_n & ~arr_sa_n);", "m_fail <= (pend_p & ~arr_sa_p);"),
    ("margin check: high-resistance device above the reset target not flagged", "tcim_core.sv",
     "m_fail <= m_fail | (~pend_p & arr_sa_p) | (~pend_n & arr_sa_n);", "m_fail <= m_fail;"),
    ("margin check: WERR not set", "tcim_core.sv",
     "if ((m_fail | (~pend_p & arr_sa_p) | (~pend_n & arr_sa_n)) != '0) s_werr <= 1'b1;", ""),
    ("margin check: second read at the read reference", "tcim_core.sv",
     "arr_op <= OP_VFY_SET; state <= S_MC_SET;", "arr_op <= OP_READ; state <= S_MC_SET;"),
    ("margin check: works without EN", "tcim_core.sv", "is_pos(bus_wdata[3:2]) & ~s_busy & r_en;", "is_pos(bus_wdata[3:2]) & ~s_busy;"),
    ("margin check: PDATA not written", "tcim_core.sv",
     "r_pdata[2*c +: 2] <= sign_to_trit(arr_sa_p[c] && !arr_sa_n[c], arr_sa_n[c] && !arr_sa_p[c]);", ";"),
    ("margin check: MARG not cleared by the next margin check", "tcim_core.sv",
     "s_done <= 1'b0; s_sat <= 1'b0; s_werr <= ~prow_ok; m_fail <= '0;", "s_done <= 1'b0; s_sat <= 1'b0; s_werr <= ~prow_ok;"),
    ("MARG read with the wrong sign", "tcim_core.sv", "sign_to_trit(m_fail[c], 1'b0)", "sign_to_trit(1'b0, m_fail[c])"),
    ("dummy accumulators never updated", "tcim_core.sv", "d_acc <= d_acc_next; r_cnt <= r_cnt + 7'd1;", "r_cnt <= r_cnt + 7'd1;"),
    ("ACT not hidden by LOCK", "tcim_core.sv", "sign_to_trit(!r_lock && (^d_acc), 1'b0)", "sign_to_trit((^d_acc), 1'b0)"),
    # revision 4.7 (council review, 6 November 2026)
    ("read-back runs under LOCK", "tcim_core.sv", "if (prow_ok && !r_lock) begin", "if (prow_ok) begin"),
    ("read-back under LOCK without WERR", "tcim_core.sv", "s_werr <= ~prow_ok | r_lock;", "s_werr <= ~prow_ok;"),
    ("margin check writes PDATA under LOCK", "tcim_core.sv", "if (!r_lock) begin                           // (revision 4.7: not under LOCK)",
     "if (1'b1) begin                           // (revision 4.7: not under LOCK)"),
    ("offset not taken off at the end of a product", "tcim_core.sv", "state <= S_FINISH; acc <= acc_fin;", "state <= S_FINISH; acc <= acc_upd;"),
    ("offset taken off with the wrong sign", "tcim_core.sv", "acc_upd[c*ACCW +: ACCW] - r_off;", "acc_upd[c*ACCW +: ACCW] + r_off;"),
    ("offset register not loaded at GO", "tcim_core.sv", "r_off <= {{(ACCW-8){lfsr[15]}}, lfsr[15:8]}; acc <=", "acc <="),
]

# faults that change nothing in the two's complement code (where a zero trit is 00) and are run only with TB_ENC=pnx
MP = [
    ("PNX: X registers reset to 0 bits instead of zero trits", "tcim_core.sv", "r_x <= {3{ZERO_WORD}};", "r_x <= '0;"),
    ("PNX: PROW and PDATA reset to 0 bits instead of zero trits", "tcim_core.sv",
     "r_prow <= ZERO_TRYTE; r_pdata <= ZERO_WORD;", "r_prow <= '0; r_pdata <= '0;"),
    ("PNX: TILE resets to 0 bits instead of zero trits", "tcim_core.sv", "r_tile <= ZERO_TRYTE;", "r_tile <= '0;"),
    ("PNX: unused trits of a read value are 0 bits", "tcim_core.sv", "bus_rdata = ZERO_WORD; ", "bus_rdata = '0; "),
    ("PNX: codes of +1 and -1 exchanged", "tcim_pkg.sv",
     "localparam logic [1:0] T_POS  = 2'b10;\n    localparam logic [1:0] T_NEG  = 2'b01;",
     "localparam logic [1:0] T_POS  = 2'b01;\n    localparam logic [1:0] T_NEG  = 2'b10;"),
    ("PNX: zero trit produced as the illegal pair 00", "tcim_pkg.sv",
     "localparam logic [1:0] T_ZERO = 2'b11;", "localparam logic [1:0] T_ZERO = 2'b00;"),
]
if PNX:
    M = M + MP


def run(k, name, fname, old, new):
    d = ROOT / "tb" / "build" / f"mut{TAG}{k:02d}"
    shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True)
    for f in RTL:
        s = (ROOT / "rtl" / f).read_text()
        if f == fname:
            if s.count(old) != 1:
                return dict(name=name, status="NOT APPLIED", detail=f"{s.count(old)} matches")
            s = s.replace(old, new)
        (d / f).write_text(s)
    srcs = " ".join(str(d / f) for f in RTL)
    y = subprocess.run(["yosys", "-q", "-p", f"read_slang {' '.join('-D ' + x[2:] for x in DEFS)} --top tcim_top {srcs}; hierarchy -top tcim_top; proc; flatten; opt; "
                        f"write_cxxrtl -header -namespace cxxrtl_design {d}/tcim_top.cc"], capture_output=True, text=True)
    if y.returncode:
        return dict(name=name, status="DOES NOT ELABORATE", detail=(y.stdout + y.stderr)[-300:])
    c = subprocess.run(["c++", "-std=c++14", "-O1", *DEFS, "-I", str(d), "-I", CXXRTL, str(TB_SRC), str(d / "tcim_top.cc"),
                        "-o", str(d / "tb")], capture_output=True, text=True)
    if c.returncode:
        return dict(name=name, status="DOES NOT COMPILE", detail=c.stderr[-300:])
    t0 = time.time()
    try:
        r = subprocess.run([str(d / "tb"), str(ROOT / "tb" / "vectors")], capture_output=True, text=True, timeout=1500,
                           env=dict(os.environ, TB_FAIL_FAST="1"))
        out = r.stdout
        caught = "TEST FAILED" in out or r.returncode != 0
        first = next((l.strip() for l in out.splitlines() if "FAIL:" in l), "")
        stage = [l for l in out.splitlines() if l[:1].isdigit()]
        res = dict(name=name, status="caught" if caught else "SURVIVED", first_failure=first, in_test=stage[-1][:40] if stage else "",
                   seconds=round(time.time() - t0))
    except subprocess.TimeoutExpired:
        res = dict(name=name, status="caught", first_failure="test bench did not finish (hang)", in_test="", seconds=1500)
    for f in ("tcim_top.cc", "tcim_top.h", "tb"):
        (d / f).unlink(missing_ok=True)
    return res


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "count":
        print(len(M)); sys.exit(0)
    a = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    b = int(sys.argv[2]) if len(sys.argv) > 2 else len(M) - 1
    out = ROOT / "results" / f"rtl_mutation{TAG}_{a}_{b}.json"
    res = []
    for k in range(a, b + 1):
        r = run(k, *M[k])
        r["id"] = k
        res.append(r)
        print(k, r["status"], "|", r["name"], "|", r.get("first_failure", r.get("detail", ""))[:110], "|", r.get("seconds", ""), flush=True)
        out.write_text(json.dumps(res, indent=1))
