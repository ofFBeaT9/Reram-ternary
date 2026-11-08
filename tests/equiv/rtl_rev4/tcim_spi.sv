// tcim_spi.sv - 4-wire serial port (SPI mode 0, MSB first) in front of the TCIM0 register bus.
//
// Frame, 8 bytes with CS low:
//   byte 0   : {rw, word, addr[5:0]}   rw = 1 write, 0 read ; word = 1 for a 24-trit word, 0 for a tryte
//   bytes 1-6: 48 data bits, MSB first (2 bits per trit; a tryte uses the low 12 bits)
//   byte 7   : status returned on MISO: {5'b0, bus_err, irq, 1'b1} ; MOSI ignored
// On a read the data bytes on MISO carry the register value; on a write MISO returns zeros.
// The serial clock is sampled in the system clock domain. MISO changes up to three system clock cycles after
// the falling edge of sck and the host samples it on the next rising edge, so sck must not be faster than
// clk / 8. (In simulation clk / 6 still works and clk / 4 fails. Revision 3 stated clk / 4 here.)
// A frame cut short before bit 56 writes nothing. Clocks after bit 64 are ignored until CS rises.
module tcim_spi
    import tcim_pkg::*;
(
    input  logic                clk,
    input  logic                rst_n,
    input  logic                sck,
    input  logic                cs_n,
    input  logic                mosi,
    output logic                miso,
    // register bus master
    output logic                bus_we,
    output logic                bus_re,
    output logic                bus_word,
    output logic [5:0]          bus_addr,
    output logic [2*WORD-1:0]   bus_wdata,
    input  logic [2*WORD-1:0]   bus_rdata,
    input  logic                bus_err,
    input  logic                irq
);
    logic [2:0] sck_s, cs_s;
    logic [1:0] mosi_s;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin sck_s <= 3'b000; cs_s <= 3'b111; mosi_s <= 2'b00; end
        else begin sck_s <= {sck_s[1:0], sck}; cs_s <= {cs_s[1:0], cs_n}; mosi_s <= {mosi_s[0], mosi}; end
    end
    logic sck_rise, sck_fall, active;
    assign sck_rise = (sck_s[2:1] == 2'b01);
    assign sck_fall = (sck_s[2:1] == 2'b10);
    assign active   = ~cs_s[1];

    logic [6:0]  bitcnt;                 // 0 .. 64 (64 = frame complete, waiting for CS to rise)
    logic [7:0]  cmd;
    logic [47:0] shift_in, shift_out;
    logic        err_latch;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bitcnt <= '0; cmd <= '0; shift_in <= '0; shift_out <= '0; err_latch <= 1'b0;
            bus_we <= 1'b0; bus_re <= 1'b0; bus_word <= 1'b0; bus_addr <= '0; bus_wdata <= '0; miso <= 1'b0;
        end else begin
            bus_we <= 1'b0; bus_re <= 1'b0;
            if (!active) begin
                bitcnt <= '0; miso <= 1'b0;
            end else begin
                if (sck_rise) begin
                    if (bitcnt < 7'd8) cmd <= {cmd[6:0], mosi_s[1]};
                    else if (bitcnt < 7'd56) shift_in <= {shift_in[46:0], mosi_s[1]};
                    // command complete: launch the read so that data are ready for the next falling edge
                    if (bitcnt == 7'd7) begin
                        bus_word <= cmd[5]; bus_addr <= {cmd[4:0], mosi_s[1]};
                        if (!cmd[6]) bus_re <= 1'b1;
                    end
                    // last data bit of a write
                    if (bitcnt == 7'd55 && cmd[7]) begin
                        bus_wdata <= {shift_in[46:0], mosi_s[1]}; bus_we <= 1'b1;
                    end
                    if (!bitcnt[6]) bitcnt <= bitcnt + 7'd1;     // stop at 64: clocks beyond the 8-byte frame are ignored
                end
                if (bus_re) begin shift_out <= bus_rdata; err_latch <= bus_err; end
                if (bus_we) err_latch <= bus_err;
                if (sck_fall) begin
                    if (bitcnt >= 7'd8 && bitcnt < 7'd56) begin
                        miso <= cmd[7] ? 1'b0 : shift_out[47]; shift_out <= {shift_out[46:0], 1'b0};
                    end else if (bitcnt >= 7'd56 && bitcnt < 7'd64) begin
                        case (bitcnt)
                            7'd61: miso <= err_latch;
                            7'd62: miso <= irq;
                            7'd63: miso <= 1'b1;
                            default: miso <= 1'b0;
                        endcase
                    end else miso <= 1'b0;
                end
            end
        end
    end
endmodule
