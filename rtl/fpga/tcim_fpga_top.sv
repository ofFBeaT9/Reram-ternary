// tcim_fpga_top.sv - TCIM0 on a Sipeed Tang Nano 9K (GW1NR-9) with an emulated array, driven over the USB serial
// port (9 October 2026). The register bus of tcim_core is reached through a small byte protocol (115200 8N1):
//   'W' addr flags d0..d5   bus write   (flags bit 0: word access; d0 = bits 7:0 of the 48-bit bus value)  -> 'w' st
//   'R' addr flags          bus read                                                                       -> 'r' st d0..d5
//   'E' cfg                 emulator: cfg[1:0] spread bank, cfg[4:2] read noise (LSB), cfg[7] redraw the array -> 'e' st
//   'P'                     device pulses applied since the last redraw, 32 bits                             -> 'p' st n0..n3
// st: bit 0 bus error, bit 1 irq, bit 2 emulator initializing. Unknown command bytes are ignored.
// LEDs (active low): 0 heartbeat, 1 irq, 2 emulator initializing, 3 any byte received, 4/5 off.
module tcim_fpga_top
    import tcim_pkg::*;
#(parameter int DIV = 117)                 // 13.5 MHz / 115200 baud
(
    input  logic       clk27,
    input  logic       btn_rst_n,          // S1
    input  logic       uart_rx,
    output logic       uart_tx,
    output logic [5:0] led_n
);
    // Clock: the design runs at 13.5 MHz. At 27 MHz the routed design missed timing (26.6 MHz achieved on
    // 10 October); a divide-by-two flip-flop then met setup but its clock was not on a global network and the routed
    // design had hold violations. On the board the 13.5 MHz clock therefore comes from the GW1NR-9 PLL
    // (rPLL: 27 MHz / 2 * 1, VCO 864 MHz with output divider 64); synthesis defines TCIM_FPGA_PLL.
    // Simulation (RTL and gate level) uses the divide-by-two flip-flop, which gives the same clock.
    logic clk, pll_lock;
`ifdef TCIM_FPGA_PLL
    rPLL #(.FCLKIN("27"), .IDIV_SEL(1), .FBDIV_SEL(0), .ODIV_SEL(64), .DEVICE("GW1NR-9C")) u_pll (
        .CLKOUT(clk), .LOCK(pll_lock), .CLKOUTP(), .CLKOUTD(), .CLKOUTD3(), .RESET(1'b0), .RESET_P(1'b0),
        .CLKIN(clk27), .CLKFB(1'b0), .FBDSEL(6'b0), .IDSEL(6'b0), .ODSEL(6'b0), .PSDA(4'b0), .DUTYDA(4'b0), .FDLY(4'b0));
`else
    /* verilator lint_off PROCASSINIT */
    logic clk_div = 1'b0;
    /* verilator lint_on PROCASSINIT */
    always_ff @(posedge clk27) clk_div <= ~clk_div;
    assign clk = clk_div;
    assign pll_lock = 1'b1;
`endif
    /* verilator lint_off PROCASSINIT */
    logic [7:0] por = 8'd0;             // power-on value (FPGA register initialization)
    /* verilator lint_on PROCASSINIT */

    // reset: button and a power-on counter
    logic       rst_n;
    always_ff @(posedge clk) if (!btn_rst_n || !pll_lock) por <= 8'd0; else if (por != 8'hff) por <= por + 8'd1;
    assign rst_n = (por == 8'hff);

    // core and emulated array
    logic                 bus_we, bus_re, bus_word, bus_err, irq;
    logic [5:0]           bus_addr;
    logic [2*WORD-1:0]    bus_wdata, bus_rdata;
    logic                 arr_req, arr_ack;
    logic [2:0]           arr_op;
    logic [6:0]           arr_row;
    logic [ROWS-1:0]      arr_row_mask;
    logic [COLS-1:0]      arr_mask_p, arr_mask_n, arr_sa_p, arr_sa_n;
    logic [4:0]           arr_amp;
    logic [COLS*ACCW-1:0] arr_adc;
    logic [1:0]           cfg_bank;
    logic [2:0]           cfg_noise;
    logic                 cfg_init, busy_init;
    logic [31:0]          n_pulses;

    tcim_core u_core (.clk(clk), .*);
    arr_emu   u_emu  (.clk(clk), .*);

    // serial port
    logic [7:0] rxd, txd;
    logic       rxv, txs, txr;
    uart_rx #(.DIV(DIV)) u_rx (.clk(clk), .rst_n, .rx(uart_rx), .data(rxd), .valid(rxv));
    uart_tx #(.DIV(DIV)) u_tx (.clk(clk), .rst_n, .data(txd), .start(txs), .ready(txr), .tx(uart_tx));

    // command decoder
    typedef enum logic [2:0] { B_CMD, B_ARGS, B_EXEC, B_WAIT, B_SEND, B_INIT1, B_INIT2, B_INIT3 } bst_t;
    bst_t       bst;
    logic [7:0] cmd, arg [0:7], rsp [0:7];
    logic [3:0] need, got, nsend, sent;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bst <= B_CMD; cmd <= '0; need <= '0; got <= '0; nsend <= '0; sent <= '0;
            bus_we <= 1'b0; bus_re <= 1'b0; bus_word <= 1'b0; bus_addr <= '0; bus_wdata <= '0;
            cfg_bank <= '0; cfg_noise <= 3'd1; cfg_init <= 1'b0; txs <= 1'b0; txd <= '0;
            for (int i = 0; i < 8; i++) begin arg[i] <= '0; rsp[i] <= '0; end
        end else begin
            bus_we <= 1'b0; bus_re <= 1'b0; txs <= 1'b0;
            case (bst)
                B_CMD: if (rxv) begin
                    cmd <= rxd; got <= '0;
                    case (rxd)
                        8'h57: begin need <= 4'd8; bst <= B_ARGS; end   // W
                        8'h52: begin need <= 4'd2; bst <= B_ARGS; end   // R
                        8'h45: begin need <= 4'd1; bst <= B_ARGS; end   // E
                        8'h50: begin need <= 4'd0; bst <= B_EXEC; end   // P
                        default: ;
                    endcase
                end
                B_ARGS: if (rxv) begin
                    arg[got[2:0]] <= rxd; got <= got + 4'd1;
                    if (got + 4'd1 == need) bst <= B_EXEC;
                end
                B_EXEC: begin
                    case (cmd)
                        8'h57: begin
                            bus_addr <= arg[0][5:0]; bus_word <= arg[1][0];
                            bus_wdata <= {arg[7], arg[6], arg[5], arg[4], arg[3], arg[2]};
                            bus_we <= 1'b1; bst <= B_WAIT;
                        end
                        8'h52: begin bus_addr <= arg[0][5:0]; bus_word <= arg[1][0]; bus_re <= 1'b1; bst <= B_WAIT; end
                        8'h45: begin
                            cfg_bank <= arg[0][1:0]; cfg_noise <= arg[0][4:2];
                            bst <= arg[0][7] ? B_INIT1 : B_WAIT;
                        end
                        default: bst <= B_WAIT;
                    endcase
                end
                B_WAIT: begin                    // bus access happens in this cycle (bus_we / bus_re high)
                    logic [7:0] st;
                    st = {5'b0, busy_init, irq, bus_err & (bus_we | bus_re)};
                    rsp[0] <= cmd | 8'h20;       // lower-case echo
                    rsp[1] <= st;
                    case (cmd)
                        8'h52: begin
                            rsp[2] <= bus_rdata[7:0];   rsp[3] <= bus_rdata[15:8];  rsp[4] <= bus_rdata[23:16];
                            rsp[5] <= bus_rdata[31:24]; rsp[6] <= bus_rdata[39:32]; rsp[7] <= bus_rdata[47:40];
                            nsend <= 4'd8;
                        end
                        8'h50: begin
                            rsp[2] <= n_pulses[7:0]; rsp[3] <= n_pulses[15:8]; rsp[4] <= n_pulses[23:16]; rsp[5] <= n_pulses[31:24];
                            nsend <= 4'd6;
                        end
                        default: nsend <= 4'd2;
                    endcase
                    sent <= '0; bst <= B_SEND;
                end
                // redraw: a one-cycle request (the emulator starts, or starts again if it is still drawing), one cycle
                // for its busy flag to rise, then wait until it has finished. Before 10 October the request was dropped
                // when the emulator was already busy.
                B_INIT1: begin cfg_init <= 1'b1; bst <= B_INIT3; end
                B_INIT3: begin cfg_init <= 1'b0; bst <= B_INIT2; end
                B_INIT2: if (!busy_init) bst <= B_WAIT;
                B_SEND: if (txr && !txs) begin
                    if (sent == nsend) bst <= B_CMD;
                    else begin txd <= rsp[sent[2:0]]; txs <= 1'b1; sent <= sent + 4'd1; end
                end
                default: bst <= B_CMD;
            endcase
        end
    end

    // LEDs
    logic [24:0] hb;
    logic        seen;
    always_ff @(posedge clk or negedge rst_n)
        if (!rst_n) begin hb <= '0; seen <= 1'b0; end else begin hb <= hb + 25'd1; if (rxv) seen <= ~seen; end
    assign led_n = ~{2'b00, seen, busy_init, irq, hb[24]};
endmodule
