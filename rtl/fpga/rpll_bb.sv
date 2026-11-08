// rpll_bb.sv - black-box declaration of the Gowin rPLL primitive, so that the slang front end can elaborate the
// board build of tcim_fpga_top (TCIM_FPGA_PLL); synth_gowin keeps the instance as the rPLL cell for nextpnr.
(* blackbox *)
module rPLL #(
    parameter FCLKIN = "100.0", parameter DYN_IDIV_SEL = "false", parameter IDIV_SEL = 0,
    parameter DYN_FBDIV_SEL = "false", parameter FBDIV_SEL = 0, parameter DYN_ODIV_SEL = "false", parameter ODIV_SEL = 8,
    parameter PSDA_SEL = "0000", parameter DYN_DA_EN = "false", parameter DUTYDA_SEL = "1000",
    parameter CLKOUT_FT_DIR = 1'b1, parameter CLKOUTP_FT_DIR = 1'b1, parameter CLKOUT_DLY_STEP = 0, parameter CLKOUTP_DLY_STEP = 0,
    parameter CLKFB_SEL = "internal", parameter CLKOUT_BYPASS = "false", parameter CLKOUTP_BYPASS = "false",
    parameter CLKOUTD_BYPASS = "false", parameter DYN_SDIV_SEL = 2, parameter CLKOUTD_SRC = "CLKOUT",
    parameter CLKOUTD3_SRC = "CLKOUT", parameter DEVICE = "GW1N-1"
) (
    output CLKOUT, output LOCK, output CLKOUTP, output CLKOUTD, output CLKOUTD3,
    input RESET, input RESET_P, input CLKIN, input CLKFB,
    input [5:0] FBDSEL, input [5:0] IDSEL, input [5:0] ODSEL, input [3:0] PSDA, input [3:0] DUTYDA, input [3:0] FDLY
);
endmodule
