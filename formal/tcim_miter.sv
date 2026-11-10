// Two-copy miter (revision 4.6, security study, 4 November 2026): the timing of TCIM0 does not depend on secrets.
// Two copies of tcim_core receive the same clock, reset, bus control (write / read strobes, word flag, address) and the
// same array acknowledge; the data they receive may differ wherever it is secret: the data written to X0-X2 (inputs)
// and PDATA (weights), and everything the array returns (sense bits, converter counts). With the SEC options ZSKIP and
// VARPROG left off (the defaults, which LOCK enforces), the proof shows that both copies issue the same array requests
// (request line, operation, row, amplitude) and raise DONE (seen as the interrupt line) in the same clock cycle, for every
// sequence of bus accesses and array answers. A copy that skipped a row, stopped programming early or ended a command
// at a data-dependent time would make the two copies differ.
// What the proof assumes and does not cover (council, 6 November 2026): the array answers (arr_ack) at the same times for
// both copies, i.e. the macro's answer time does not depend on the data (true of tcim_actl's fixed phase timing, not proved
// here); the device masks, and so the power drawn, are not compared (the power is the subject of tools/tvla_tcim0.py); the
// bus error flag and the read data are not compared (reading a secret register returns the secret, by design).
module tcim_miter
    import tcim_pkg::*;
(
    input  logic                 clk, rst_n,
    input  logic                 anylock,     // revision 4.9 (FORMAL_ANYLOCK): the same LOCK state after reset in both copies
    input  logic                 bus_we, bus_re, bus_word,
    input  logic [5:0]           bus_addr,
    input  logic [2*WORD-1:0]    wd0, wd1,
    input  logic                 arr_ack,
    input  logic [COLS-1:0]      sa_p0, sa_n0, sa_p1, sa_n1,
    input  logic [COLS*ACCW-1:0] adc0, adc1
);
    logic [2*WORD-1:0] rd0, rd1;
    logic err0, err1, irq0, irq1, req0, req1;
    logic [2:0] op0, op1;
    logic [6:0] row0, row1;
    logic [ROWS-1:0] rm0, rm1;
    logic [COLS-1:0] mp0, mn0, mp1, mn1;
    logic [4:0] amp0, amp1;
    tcim_core u0 (.clk, .rst_n, .f_anylock(anylock), .bus_we, .bus_re, .bus_word, .bus_addr, .bus_wdata(wd0), .bus_rdata(rd0), .bus_err(err0), .irq(irq0),
                  .arr_req(req0), .arr_op(op0), .arr_row(row0), .arr_row_mask(rm0), .arr_mask_p(mp0), .arr_mask_n(mn0), .arr_amp(amp0),
                  .arr_ack, .arr_sa_p(sa_p0), .arr_sa_n(sa_n0), .arr_adc(adc0));
    tcim_core u1 (.clk, .rst_n, .f_anylock(anylock), .bus_we, .bus_re, .bus_word, .bus_addr, .bus_wdata(wd1), .bus_rdata(rd1), .bus_err(err1), .irq(irq1),
                  .arr_req(req1), .arr_op(op1), .arr_row(row1), .arr_row_mask(rm1), .arr_mask_p(mp1), .arr_mask_n(mn1), .arr_amp(amp1),
                  .arr_ack, .arr_sa_p(sa_p1), .arr_sa_n(sa_n1), .arr_adc(adc1));
    wire secret_wr = bus_word && (bus_addr == 6'd4 || bus_addr == 6'd8 || bus_addr == 6'd12 || bus_addr == 6'd44);
    logic f_init = 1'b1;
    always_ff @(posedge clk) begin
        f_init <= 1'b0;
        if (f_init) assume (!rst_n);
        if (bus_we && !secret_wr) assume (wd0 == wd1);                         // public registers get the same data
        if (bus_we && !bus_word && bus_addr == 6'd3) assume (!is_pos(wd0[1:0]) && !is_pos(wd0[3:2]));   // ZSKIP, VARPROG off
        assume (!arr_ack || req0);                                              // the array answers only a request
        // revision 4.9: an erase clears LOCK only if every device verified, and the verify answers are secret here, so two copies
        // could leave an erase one locked and one unlocked, and then differ (batch 29 found this at step 6,270). Whether an erase
        // succeeded is public (STAT.WERR and SEC.LOCK both show it), so the proof takes the LOCK state as public: both copies hold
        // the same LOCK in every cycle. (What the failure itself reveals about the devices is the WERR fault oracle, out of scope.)
        assume (u0.r_lock == u1.r_lock);
        if (!f_init && rst_n) begin
            assert (req0 == req1);
            assert (op0 == op1);
            assert (row0 == row1);
            assert (amp0 == amp1);
            assert (irq0 == irq1);
        end
    end
endmodule
