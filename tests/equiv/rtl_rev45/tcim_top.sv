// tcim_top.sv - test-chip digital top: serial port + TCIM0 core. The analog macro connects to the arr_* ports.
module tcim_top
    import tcim_pkg::*;
(
    input  logic                    clk,
    input  logic                    rst_n,
    input  logic                    sck,
    input  logic                    cs_n,
    input  logic                    mosi,
    output logic                    miso,
    output logic                    irq,
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
    logic                bus_we, bus_re, bus_word, bus_err;
    logic [5:0]          bus_addr;
    logic [2*WORD-1:0]   bus_wdata, bus_rdata;

    tcim_spi u_spi (.*);
    tcim_core u_core (.*);
endmodule
