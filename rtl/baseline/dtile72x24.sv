// dtile72x24.sv - fully digital stand-in for one tile: the same 72 x 24 ternary weights held in flip-flops,
// the same row-by-row accumulation as the digital read mode. Used only as an area / energy yardstick.
module dtile72x24
    import tcim_pkg::*;
(
    input  logic                    clk,
    input  logic                    rst_n,
    input  logic                    we,            // write one row of weights
    input  logic [6:0]              waddr,
    input  logic [2*COLS-1:0]       wdata,
    input  logic                    go,            // start a product
    input  logic [2*ROWS-1:0]       x,             // 72 input trits
    output logic                    busy,
    output logic [COLS*ACCW-1:0]    y
);
    logic [2*COLS-1:0] mem [ROWS];
    logic [6:0]        row;
    logic [2*ROWS-1:0] rx;
    logic [2*COLS-1:0] wrow;
    logic [1:0]        xt;

    assign wrow = mem[row < 7'(ROWS) ? row : 7'd0];
    assign xt   = rx[1:0];

    always_ff @(posedge clk) if (we) mem[waddr] <= wdata;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0; row <= '0; rx <= '0; y <= '0;
        end else if (go && !busy) begin
            busy <= 1'b1; row <= '0; rx <= x; y <= '0;
        end else if (busy) begin
            for (int c = 0; c < COLS; c++) begin
                logic signed [ACCW-1:0] a;
                a = $signed(y[c*ACCW +: ACCW]);
                if (is_pos(xt) & is_pos(wrow[2*c +: 2]) | is_neg(xt) & is_neg(wrow[2*c +: 2])) y[c*ACCW +: ACCW] <= a + 10'sd1;
                else if (is_pos(xt) & is_neg(wrow[2*c +: 2]) | is_neg(xt) & is_pos(wrow[2*c +: 2])) y[c*ACCW +: ACCW] <= a - 10'sd1;
            end
            rx  <= {2'b00, rx[2*ROWS-1:2]};
            row <= row + 7'd1;
            if (row == 7'(ROWS - 1)) busy <= 1'b0;
        end
    end
endmodule
