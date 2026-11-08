// arr_emu.sv - emulated 72 x 24 2T2R ternary array for the FPGA demonstration of TCIM0 (9 October 2026).
//
// Answers the arr_* requests of tcim_core like the analog macro would, with device-to-device and pulse-to-pulse
// variability. NOT a model of silicon: the numbers come from tools/make_devlut.py (arr_emu_lut.svh):
//   - each device has a fixed "personality" index (0..127) into a table of pulse thresholds taken from the device
//     model's programming Monte Carlo (results/program_mc.json): a set pulse of amplitude step a succeeds when
//     a >= set threshold, a reset pulse when a >= reset threshold (31 = never: the device cannot be reset);
//   - a successful pulse puts the device at a level drawn afresh from the published IHP distribution
//     (LRS 43.59 +/- 1.55 uA, HRS 2.85 +/- 1.85 uA, sigma x1/x2/x3 by bank), so a draw that misses the verify
//     target is caught by the verify read and pulsed again, as on silicon;
//   - every comparison adds read noise of +/- noise LSB (0.25 uA per LSB), uniform.
// Storage: one 16-bit word per device {personality[6:0], level[7:0]} in block RAM, address row * 48 + 2 * col + n.
// Each device takes three clock cycles per operation (word read, table read, then compute and write back).
// After reset (and after an init request) every device is drawn at HRS with a random personality.
module arr_emu
    import tcim_pkg::*;
(
    input  logic                    clk,
    input  logic                    rst_n,
    input  logic [1:0]              cfg_bank,        // 0: 1x, 1: 2x, 2: 3x spread (see arr_emu_lut.svh)
    input  logic [2:0]              cfg_noise,       // read noise amplitude in LSB
    input  logic                    cfg_init,        // pulse: redraw the whole array
    output logic                    busy_init,
    output logic [31:0]             n_pulses,        // device pulses applied since init (for the host)
    input  logic                    arr_req,
    input  logic [2:0]              arr_op,
    input  logic [6:0]              arr_row,
    input  logic [ROWS-1:0]         arr_row_mask,
    input  logic [COLS-1:0]         arr_mask_p,
    input  logic [COLS-1:0]         arr_mask_n,
    input  logic [4:0]              arr_amp,
    output logic                    arr_ack,
    output logic [COLS-1:0]         arr_sa_p,
    output logic [COLS-1:0]         arr_sa_n,
    output logic [COLS*ACCW-1:0]    arr_adc
);
`include "arr_emu_lut.svh"
    localparam int NDEV = ROWS * 2 * COLS;            // 3456
    localparam logic [7:0] REF_READ = 8'd100, REF_SET = 8'd168, REF_RST = 8'd24;

    // ---------------------------------------------------------------- random numbers: 32-bit Galois LFSR
    logic [31:0] lfsr;
    always_ff @(posedge clk or negedge rst_n)
        if (!rst_n) lfsr <= 32'hACE1_2026;
        else        lfsr <= {1'b0, lfsr[31:1]} ^ (lfsr[0] ? 32'hA300_0001 : 32'h0);

    // ---------------------------------------------------------------- device memory
    logic [15:0] mem [0:4095];
    logic [11:0] raddr, waddr;
    logic [15:0] rdata, wdata;
    logic        we;
    always_ff @(posedge clk) begin
        if (we) mem[waddr] <= wdata;
        rdata <= mem[raddr];
    end

    // ---------------------------------------------------------------- level draw
    // Level drawn by a successful pulse: a table (arr_emu_lut.svh, lev_lut), no multiplier. On the GW1NR-9 board a
    // signed MULT18X18 product of a negative operand came out wrong (10 October 2026: every analog column with a
    // negative sum saturated) although the gate-level model, written from the documented behaviour, matched the RTL;
    // the unsigned 9 x 9 product that replaced it here could not be placed by nextpnr. The table holds exactly the
    // values the former level function computed: MEAN + floor(SIG * q / 256), clamped.

    // table lookups, registered: a fresh quantile every cycle, and the thresholds of the device whose word is in rdata
    // One table read per cycle: the LRS level is needed only while a set pulse is applied (E_WB of OP_PULSE_SET, whose
    // previous cycle, E_RD2, has the same op); the power-on draw (E_INIT, entered from E_IDLE) and reset pulses need HRS.
    logic [7:0]        lev_q;                            // level for this cycle's random draw
    logic [9:0]        thr_q;
    logic              lev_hi;
    always_ff @(posedge clk) begin
        lev_q <= lev_lut({lev_hi, cfg_bank, lfsr[7:0]});
        thr_q <= thr_lut({cfg_bank[1:0], rdata[14:8]});
    end

    // read noise: uniform in [-noise, +noise]
    logic signed [4:0] nz;
    always_comb begin
        logic [3:0] span;
        span = {cfg_noise, 1'b0} + 4'd1;                        // 2 * noise + 1 values
        nz = 5'(lfsr[19:16] % span) - 5'({2'b0, cfg_noise});
    end

    // ---------------------------------------------------------------- sequencer
    typedef enum logic [2:0] { E_INIT, E_IDLE, E_RD, E_RD2, E_WB, E_FIN, E_GAP } st_t;
    st_t st;
    logic [2:0]  op;
    logic [6:0]  row, r_end;
    logic [5:0]  dev;                                         // 0..47 within a row
    logic [ROWS-1:0] rmask;
    logic [COLS-1:0] mp, mn;
    logic [4:0]  amp;
    logic [11:0] icnt;
    logic signed [15:0] colsum [0:COLS-1];

    wire  [4:0]  col = dev[5:1];
    wire         neg = dev[0];
    wire  [11:0] base = 12'(row) * 12'd48;

    assign busy_init = (st == E_INIT);
    assign lev_hi = (op == OP_PULSE_SET) && (st != E_IDLE) && (st != E_INIT);

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= E_INIT; icnt <= '0; we <= 1'b0; arr_ack <= 1'b0; arr_sa_p <= '0; arr_sa_n <= '0; arr_adc <= '0;
            op <= '0; row <= '0; r_end <= '0; dev <= '0; rmask <= '0; mp <= '0; mn <= '0; amp <= '0; raddr <= '0;
            waddr <= '0; wdata <= '0; n_pulses <= '0;
            for (int c = 0; c < COLS; c++) colsum[c] <= '0;
        end else begin
            we <= 1'b0; arr_ack <= 1'b0;
            case (st)
                E_INIT: begin                                   // one device per cycle: HRS, random personality
                    we <= 1'b1; waddr <= icnt; wdata <= {1'b0, lfsr[30:24], lev_q};
                    n_pulses <= '0;
                    // a redraw requested while drawing starts again (before 10 October it was ignored, so a host that
                    // changed the spread bank during the power-on draw got part of the array with the old bank)
                    if (cfg_init) icnt <= '0;
                    else begin
                        icnt <= icnt + 12'd1;
                        if (icnt == 12'(NDEV - 1)) st <= E_IDLE;
                    end
                end
                E_IDLE: begin
                    if (cfg_init) begin icnt <= '0; st <= E_INIT; end
                    else if (arr_req) begin
                        op <= arr_op; amp <= arr_amp; mp <= arr_mask_p; mn <= arr_mask_n; rmask <= arr_row_mask;
                        dev <= '0;
                        for (int c = 0; c < COLS; c++) colsum[c] <= '0;
                        if (arr_op == OP_SUM) begin row <= 7'd0; r_end <= 7'(ROWS - 1); end
                        else begin row <= arr_row; r_end <= arr_row; end
                        raddr <= 12'(arr_op == OP_SUM ? 7'd0 : arr_row) * 12'd48;
                        st <= E_RD;
                    end
                end
                E_RD:  st <= E_RD2;                             // device word read in flight
                E_RD2: st <= E_WB;                              // threshold table read in flight
                E_WB: begin
                    logic [7:0]  g, gn;
                    logic [9:0]  th;
                    logic        sel, hit;
                    logic signed [9:0] ge;
                    g  = rdata[7:0];
                    th = thr_q;
                    ge = 10'(g) + 10'(nz);
                    sel = neg ? mn[col] : mp[col];
                    gn = g; hit = 1'b0;
                    case (op)
                        OP_READ:      if (neg) arr_sa_n[col] <= ge > $signed({2'b0, REF_READ}); else arr_sa_p[col] <= ge > $signed({2'b0, REF_READ});
                        OP_VFY_SET:   if (neg) arr_sa_n[col] <= ge >= $signed({2'b0, REF_SET}); else arr_sa_p[col] <= ge >= $signed({2'b0, REF_SET});
                        OP_VFY_RESET: if (neg) arr_sa_n[col] <= ge > $signed({2'b0, REF_RST}); else arr_sa_p[col] <= ge > $signed({2'b0, REF_RST});
                        OP_PULSE_SET: if (sel) begin hit = amp >= th[4:0]; if (hit) gn = lev_q; end
                        OP_PULSE_RST: if (sel) begin hit = amp >= th[9:5]; if (hit) gn = lev_q; end
                        OP_SUM:       if (rmask[row]) colsum[col] <= neg ? colsum[col] - 16'(ge) : colsum[col] + 16'(ge);
                        default: ;
                    endcase
                    if ((op == OP_PULSE_SET || op == OP_PULSE_RST) && sel) n_pulses <= n_pulses + 32'd1;
                    if (gn != g) begin we <= 1'b1; waddr <= base + 12'(dev); wdata <= {rdata[15:8], gn}; end
                    if (dev == 6'd47) begin
                        dev <= '0;
                        if (row == r_end) st <= E_FIN;
                        else begin row <= row + 7'd1; raddr <= base + 12'd48; st <= E_RD; end
                    end else begin
                        dev <= dev + 6'd1; raddr <= base + 12'(dev) + 12'd1; st <= E_RD;
                    end
                end
                // answer: arr_ack is high in the cycle after E_FIN (state E_GAP). A request that is still (or again)
                // high in the cycle after that is a new one and is taken in E_IDLE, as tcim_core expects.
                // For a sum, E_FIN converts one column per cycle, dev counting the columns.
                E_FIN: begin
                    if (op == OP_SUM && dev != 6'(COLS)) begin
                        // round(cs * STEP_RECIP / 2^16), halves up, without a signed product: the sum is offset to
                        // unsigned (cs + 2^15 = cs with its top bit inverted) and 2^15 * R = (R / 2) * 2^16 (R = STEP_RECIP, even) is
                        // taken off after the shift, which is exact: ((u * R + 2^15) >> 16) - R / 2 = (cs * R + 2^15) >>> 16
                        logic [15:0]        u;
                        logic [31:0]        pm;
                        logic signed [31:0] r;
                        u  = {~colsum[dev[4:0]][15], colsum[dev[4:0]][14:0]};
                        pm = 32'(u) * 32'(STEP_RECIP);                    // unsigned multiply (MULT18X18)
                        r  = $signed((pm + 32'd32768) >> 16) - $signed(32'(STEP_RECIP / 2));   // STEP_RECIP is even (make_devlut.py)
                        for (int c = 0; c < COLS; c++)                    // constant part-selects only
                            if (dev[4:0] == 5'(c)) arr_adc[c*ACCW +: ACCW] <= ACCW'(r);
                        dev <= dev + 6'd1;
                    end else begin
                        dev <= '0; arr_ack <= 1'b1; st <= E_GAP;
                    end
                end
                E_GAP: st <= E_IDLE;
                default: st <= E_IDLE;
            endcase
        end
    end
endmodule
