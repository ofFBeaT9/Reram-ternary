// tcim_chip_core.sv - digital part of the SKY130 test chip (11 October 2026): the verified TCIM0 top (serial port +
// core) and the array controller. Analog mode has no column converter on this chip: arr_adc is tied to zero, so an
// analog-mode product returns zero counts.
module tcim_chip_core
    import tcim_pkg::*;
(
    input  logic                    clk,
    input  logic                    rst_n,
    input  logic                    sck,
    input  logic                    cs_n,
    input  logic                    mosi,
    output logic                    miso,
    output logic                    irq,
    input  logic [2:0]              cfg_ts,
    input  logic [2:0]              cfg_tp,
    input  logic [1:0]              cfg_tr,
    output logic [ROWS-1:0]         wl_on,
    output logic                    wl_prog,
    output logic [COLS-1:0]         blp_prg, bln_prg,
    output logic                    bl_sen,
    output logic                    sl_prg,
    output logic                    flt,
    output logic [2:0]              ref_sel,
    input  logic [COLS-1:0]         sa_p,
    input  logic [COLS-1:0]         sa_n,
    output logic                    pk,
    output logic [4:0]              pamp,
    output logic                    pstb
);
    logic                    arr_req, arr_ack;
    logic [2:0]              arr_op;
    logic [6:0]              arr_row;
    /* verilator lint_off UNUSEDSIGNAL */
    logic [ROWS-1:0]         arr_row_mask;     // rows of an analog-mode sum: no analog mode on this chip, unused
    /* verilator lint_on UNUSEDSIGNAL */
    logic [COLS-1:0]         arr_mask_p, arr_mask_n, arr_sa_p, arr_sa_n;
    logic [4:0]              arr_amp;
    logic [COLS*ACCW-1:0]    arr_adc;

    assign arr_adc = '0;

    tcim_top  u_top  (.*);
    tcim_actl u_actl (.*);
endmodule
