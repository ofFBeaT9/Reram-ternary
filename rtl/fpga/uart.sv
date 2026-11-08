// uart.sv - 8N1 serial port for the FPGA demonstration. DIV = clock cycles per bit (27 MHz / 115200 = 234).
module uart_rx #(parameter int DIV = 234) (
    input  logic clk, rst_n, rx,
    output logic [7:0] data,
    output logic valid                       // one-cycle pulse per received byte
);
    logic [1:0]  sync;
    logic [15:0] cnt;
    logic [3:0]  bitn;
    logic [7:0]  sh;
    logic        busy;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin sync <= 2'b11; cnt <= '0; bitn <= '0; sh <= '0; busy <= 1'b0; valid <= 1'b0; data <= '0; end
        else begin
            sync <= {sync[0], rx}; valid <= 1'b0;
            if (!busy) begin
                if (!sync[1]) begin busy <= 1'b1; cnt <= 16'(DIV / 2); bitn <= '0; end   // start bit edge
            end else if (cnt == 16'(DIV - 1)) begin
                cnt <= '0;
                if (bitn == 4'd0) begin if (sync[1]) busy <= 1'b0; else bitn <= 4'd1; end // false start
                else if (bitn <= 4'd8) begin sh <= {sync[1], sh[7:1]}; bitn <= bitn + 4'd1; end
                else begin busy <= 1'b0; if (sync[1]) begin data <= sh; valid <= 1'b1; end end // stop bit
            end else cnt <= cnt + 16'd1;
        end
    end
endmodule

module uart_tx #(parameter int DIV = 234) (
    input  logic clk, rst_n,
    input  logic [7:0] data,
    input  logic start,                      // accepted when ready
    output logic ready,
    output logic tx
);
    logic [15:0] cnt;
    logic [3:0]  bitn;
    logic [9:0]  sh;
    assign ready = (bitn == 4'd0);
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin cnt <= '0; bitn <= '0; sh <= '1; tx <= 1'b1; end
        else if (bitn == 4'd0) begin
            tx <= 1'b1;
            if (start) begin sh <= {1'b1, data, 1'b0}; bitn <= 4'd10; cnt <= '0; end
        end else begin
            tx <= sh[0];
            if (cnt == 16'(DIV - 1)) begin cnt <= '0; sh <= {1'b1, sh[9:1]}; bitn <= bitn - 4'd1; end
            else cnt <= cnt + 16'd1;
        end
    end
endmodule
