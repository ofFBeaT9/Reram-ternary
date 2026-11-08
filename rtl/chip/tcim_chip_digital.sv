// tcim_chip_digital.sv - the hardened digital block of the SKY130 chip (11 October 2026): tcim_chip_core plus the
// constant levels the Caravan pads need (tie cells inside the block, so no pad control is wired to a supply).
// Pads used as inputs (13): io_out = 0, io_oeb = 1. Pads used as outputs (9): io_oeb = 0.
module tcim_chip_digital
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
    output logic                    pstb,
    output logic [12:0]             tie_hi,           // io_oeb of the 13 input pads
    output logic [21:0]             tie_lo            // io_out of the 13 input pads, io_oeb of the 9 output pads
);
    assign tie_hi = '1;
    assign tie_lo = '0;
    tcim_chip_core u_core (.*);
endmodule
