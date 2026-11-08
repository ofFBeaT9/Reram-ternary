// gowin_models.v - behavioural models of the Gowin DPB block RAM and MULT18X18 multiplier for gate-level simulation.
// Yosys ships DPB only as a black box (share/yosys/gowin/cells_xtra_gw1n.v), so a netlist with block RAM cannot be
// simulated without a model. This one implements the behaviour Yosys assumes when it maps memories onto DPB
// (share/yosys/gowin/brams.txt): 16 kbit, widths 1/2/4/8/16 (BIT_WIDTH), address bits above log2(width) select the
// word, READ_MODE 0 (output registered once), WRITE_MODE 0 = output unchanged on a write cycle, 1 = new data,
// synchronous RESET clears the output, a port acts only when its BLKSEL equals BLK_SEL. Simulation only.
module DPB(CLKA, CEA, CLKB, CEB, OCEA, OCEB, RESETA, RESETB, WREA, WREB, ADA, ADB, BLKSELA, BLKSELB, DIA, DIB, DOA, DOB);
parameter READ_MODE0 = 1'b0;
parameter READ_MODE1 = 1'b0;
parameter WRITE_MODE0 = 2'b00;
parameter WRITE_MODE1 = 2'b00;
parameter BIT_WIDTH_0 = 16;
parameter BIT_WIDTH_1 = 16;
parameter BLK_SEL_0 = 3'b000;
parameter BLK_SEL_1 = 3'b000;
parameter RESET_MODE = "SYNC";
parameter [255:0] INIT_RAM_00 = 256'h0;
parameter [255:0] INIT_RAM_01 = 256'h0;
parameter [255:0] INIT_RAM_02 = 256'h0;
parameter [255:0] INIT_RAM_03 = 256'h0;
parameter [255:0] INIT_RAM_04 = 256'h0;
parameter [255:0] INIT_RAM_05 = 256'h0;
parameter [255:0] INIT_RAM_06 = 256'h0;
parameter [255:0] INIT_RAM_07 = 256'h0;
parameter [255:0] INIT_RAM_08 = 256'h0;
parameter [255:0] INIT_RAM_09 = 256'h0;
parameter [255:0] INIT_RAM_0A = 256'h0;
parameter [255:0] INIT_RAM_0B = 256'h0;
parameter [255:0] INIT_RAM_0C = 256'h0;
parameter [255:0] INIT_RAM_0D = 256'h0;
parameter [255:0] INIT_RAM_0E = 256'h0;
parameter [255:0] INIT_RAM_0F = 256'h0;
parameter [255:0] INIT_RAM_10 = 256'h0;
parameter [255:0] INIT_RAM_11 = 256'h0;
parameter [255:0] INIT_RAM_12 = 256'h0;
parameter [255:0] INIT_RAM_13 = 256'h0;
parameter [255:0] INIT_RAM_14 = 256'h0;
parameter [255:0] INIT_RAM_15 = 256'h0;
parameter [255:0] INIT_RAM_16 = 256'h0;
parameter [255:0] INIT_RAM_17 = 256'h0;
parameter [255:0] INIT_RAM_18 = 256'h0;
parameter [255:0] INIT_RAM_19 = 256'h0;
parameter [255:0] INIT_RAM_1A = 256'h0;
parameter [255:0] INIT_RAM_1B = 256'h0;
parameter [255:0] INIT_RAM_1C = 256'h0;
parameter [255:0] INIT_RAM_1D = 256'h0;
parameter [255:0] INIT_RAM_1E = 256'h0;
parameter [255:0] INIT_RAM_1F = 256'h0;
parameter [255:0] INIT_RAM_20 = 256'h0;
parameter [255:0] INIT_RAM_21 = 256'h0;
parameter [255:0] INIT_RAM_22 = 256'h0;
parameter [255:0] INIT_RAM_23 = 256'h0;
parameter [255:0] INIT_RAM_24 = 256'h0;
parameter [255:0] INIT_RAM_25 = 256'h0;
parameter [255:0] INIT_RAM_26 = 256'h0;
parameter [255:0] INIT_RAM_27 = 256'h0;
parameter [255:0] INIT_RAM_28 = 256'h0;
parameter [255:0] INIT_RAM_29 = 256'h0;
parameter [255:0] INIT_RAM_2A = 256'h0;
parameter [255:0] INIT_RAM_2B = 256'h0;
parameter [255:0] INIT_RAM_2C = 256'h0;
parameter [255:0] INIT_RAM_2D = 256'h0;
parameter [255:0] INIT_RAM_2E = 256'h0;
parameter [255:0] INIT_RAM_2F = 256'h0;
parameter [255:0] INIT_RAM_30 = 256'h0;
parameter [255:0] INIT_RAM_31 = 256'h0;
parameter [255:0] INIT_RAM_32 = 256'h0;
parameter [255:0] INIT_RAM_33 = 256'h0;
parameter [255:0] INIT_RAM_34 = 256'h0;
parameter [255:0] INIT_RAM_35 = 256'h0;
parameter [255:0] INIT_RAM_36 = 256'h0;
parameter [255:0] INIT_RAM_37 = 256'h0;
parameter [255:0] INIT_RAM_38 = 256'h0;
parameter [255:0] INIT_RAM_39 = 256'h0;
parameter [255:0] INIT_RAM_3A = 256'h0;
parameter [255:0] INIT_RAM_3B = 256'h0;
parameter [255:0] INIT_RAM_3C = 256'h0;
parameter [255:0] INIT_RAM_3D = 256'h0;
parameter [255:0] INIT_RAM_3E = 256'h0;
parameter [255:0] INIT_RAM_3F = 256'h0;
input CLKA, CEA, CLKB, CEB, OCEA, OCEB, RESETA, RESETB, WREA, WREB;
input [13:0] ADA, ADB;
input [2:0] BLKSELA, BLKSELB;
input [15:0] DIA, DIB;
output reg [15:0] DOA, DOB;
reg [16383:0] bits;
initial begin bits = {INIT_RAM_3F, INIT_RAM_3E, INIT_RAM_3D, INIT_RAM_3C, INIT_RAM_3B, INIT_RAM_3A, INIT_RAM_39, INIT_RAM_38, INIT_RAM_37, INIT_RAM_36, INIT_RAM_35, INIT_RAM_34, INIT_RAM_33, INIT_RAM_32, INIT_RAM_31, INIT_RAM_30, INIT_RAM_2F, INIT_RAM_2E, INIT_RAM_2D, INIT_RAM_2C, INIT_RAM_2B, INIT_RAM_2A, INIT_RAM_29, INIT_RAM_28, INIT_RAM_27, INIT_RAM_26, INIT_RAM_25, INIT_RAM_24, INIT_RAM_23, INIT_RAM_22, INIT_RAM_21, INIT_RAM_20, INIT_RAM_1F, INIT_RAM_1E, INIT_RAM_1D, INIT_RAM_1C, INIT_RAM_1B, INIT_RAM_1A, INIT_RAM_19, INIT_RAM_18, INIT_RAM_17, INIT_RAM_16, INIT_RAM_15, INIT_RAM_14, INIT_RAM_13, INIT_RAM_12, INIT_RAM_11, INIT_RAM_10, INIT_RAM_0F, INIT_RAM_0E, INIT_RAM_0D, INIT_RAM_0C, INIT_RAM_0B, INIT_RAM_0A, INIT_RAM_09, INIT_RAM_08, INIT_RAM_07, INIT_RAM_06, INIT_RAM_05, INIT_RAM_04, INIT_RAM_03, INIT_RAM_02, INIT_RAM_01, INIT_RAM_00}; DOA = 16'h0; DOB = 16'h0; end
function integer lg; input integer w; lg = w == 1 ? 0 : w == 2 ? 1 : w == 4 ? 2 : w == 8 ? 3 : 4; endfunction
integer i;
always @(posedge CLKA) if (CEA && BLKSELA == BLK_SEL_0) begin
    if (RESETA) DOA <= 16'h0;
    else if (WREA) begin
        for (i = 0; i < BIT_WIDTH_0; i = i + 1) bits[(ADA >> lg(BIT_WIDTH_0)) * BIT_WIDTH_0 + i] <= DIA[i];
        if (WRITE_MODE0 == 2'b01) DOA <= DIA;
    end else for (i = 0; i < 16; i = i + 1) DOA[i] <= (i < BIT_WIDTH_0) ? bits[(ADA >> lg(BIT_WIDTH_0)) * BIT_WIDTH_0 + i] : 1'b0;
end
always @(posedge CLKB) if (CEB && BLKSELB == BLK_SEL_1) begin
    if (RESETB) DOB <= 16'h0;
    else if (WREB) begin
        for (i = 0; i < BIT_WIDTH_1; i = i + 1) bits[(ADB >> lg(BIT_WIDTH_1)) * BIT_WIDTH_1 + i] <= DIB[i];
        if (WRITE_MODE1 == 2'b01) DOB <= DIB;
    end else for (i = 0; i < 16; i = i + 1) DOB[i] <= (i < BIT_WIDTH_1) ? bits[(ADB >> lg(BIT_WIDTH_1)) * BIT_WIDTH_1 + i] : 1'b0;
end
endmodule

// MULT18X18 / MULT9X9 - Yosys ships them as black boxes too. Model of the configuration Yosys uses for a
// combinational multiply (all input, pipeline and output registers off, which this model requires): DOUT = A * B,
// each operand signed when its *SIGN input is 1. SIA/SIB/ASEL/BSEL (shift chains) are not modelled. Simulation only.
// Signed use is reported: on the GW1NR-9 board a signed product of a negative operand did not match this model
// (10 October 2026), so the design uses unsigned products only (rtl/fpga/arr_emu.sv).
module MULT18X18(A, SIA, B, SIB, ASIGN, BSIGN, ASEL, BSEL, CE, CLK, RESET, DOUT, SOA, SOB);
input  [17:0] A, SIA;
input  [17:0] B, SIB;
input  ASIGN, BSIGN;
input  ASEL, BSEL;
input  CE;
input  CLK;
input  RESET;
output [35:0] DOUT;
output [17:0] SOA, SOB;
parameter AREG = 1'b0;
parameter BREG = 1'b0;
parameter OUT_REG = 1'b0;
parameter PIPE_REG = 1'b0;
parameter ASIGN_REG = 1'b0;
parameter BSIGN_REG = 1'b0;
parameter SOA_REG = 1'b0;
parameter MULT_RESET_MODE = "SYNC";
wire signed [18:0] a = $signed({ASIGN & A[17], A});   // 19-bit signed: sign bit only when ASIGN
wire signed [18:0] b = $signed({BSIGN & B[17], B});
wire signed [37:0] p = a * b;
assign DOUT = p[35:0];
assign SOA = A;
assign SOB = B;
initial if (AREG || BREG || OUT_REG || PIPE_REG || ASIGN_REG || BSIGN_REG) $display("MULT18X18 model: registers not modelled");
always @(ASIGN or BSIGN) if (ASIGN === 1'b1 || BSIGN === 1'b1) $display("MULT18X18 model: signed operand (not matched by the board)");
endmodule

module MULT9X9(A, SIA, B, SIB, ASIGN, BSIGN, ASEL, BSEL, CE, CLK, RESET, DOUT, SOA, SOB);
input  [8:0] A, SIA;
input  [8:0] B, SIB;
input  ASIGN, BSIGN;
input  ASEL, BSEL;
input  CE;
input  CLK;
input  RESET;
output [17:0] DOUT;
output [8:0] SOA, SOB;
parameter AREG = 1'b0;
parameter BREG = 1'b0;
parameter OUT_REG = 1'b0;
parameter PIPE_REG = 1'b0;
parameter ASIGN_REG = 1'b0;
parameter BSIGN_REG = 1'b0;
parameter SOA_REG = 1'b0;
parameter MULT_RESET_MODE = "SYNC";
wire signed [9:0]  a = $signed({ASIGN & A[8], A});
wire signed [9:0]  b = $signed({BSIGN & B[8], B});
wire signed [19:0] p = a * b;
assign DOUT = p[17:0];
assign SOA = A;
assign SOB = B;
initial if (AREG || BREG || OUT_REG || PIPE_REG || ASIGN_REG || BSIGN_REG) $display("MULT9X9 model: registers not modelled");
always @(ASIGN or BSIGN) if (ASIGN === 1'b1 || BSIGN === 1'b1) $display("MULT9X9 model: signed operand (not matched by the board)");
endmodule

// SPX9 - single-port 18 kbit block RAM (used by Yosys for ROMs); also a black box in Yosys' cells_sim.v.
// Model of the configuration Yosys uses: READ_MODE 0, word address AD[13:3] / AD[13:4] / AD[13:5] for widths
// 9 / 18 / 36, contents INIT_RAM_00..3F packed in 9-bit units (Yosys brams_map.v init_slice_x9), WRITE_MODE as in
// DPB, synchronous RESET clears the output. Simulation only.
module SPX9(DO, DI, BLKSEL, AD, WRE, CLK, CE, OCE, RESET);
parameter READ_MODE = 1'b0;
parameter WRITE_MODE = 2'b00;
parameter BIT_WIDTH = 36;
parameter BLK_SEL = 3'b000;
parameter RESET_MODE = "SYNC";
parameter [287:0] INIT_RAM_00 = 288'h0;
parameter [287:0] INIT_RAM_01 = 288'h0;
parameter [287:0] INIT_RAM_02 = 288'h0;
parameter [287:0] INIT_RAM_03 = 288'h0;
parameter [287:0] INIT_RAM_04 = 288'h0;
parameter [287:0] INIT_RAM_05 = 288'h0;
parameter [287:0] INIT_RAM_06 = 288'h0;
parameter [287:0] INIT_RAM_07 = 288'h0;
parameter [287:0] INIT_RAM_08 = 288'h0;
parameter [287:0] INIT_RAM_09 = 288'h0;
parameter [287:0] INIT_RAM_0A = 288'h0;
parameter [287:0] INIT_RAM_0B = 288'h0;
parameter [287:0] INIT_RAM_0C = 288'h0;
parameter [287:0] INIT_RAM_0D = 288'h0;
parameter [287:0] INIT_RAM_0E = 288'h0;
parameter [287:0] INIT_RAM_0F = 288'h0;
parameter [287:0] INIT_RAM_10 = 288'h0;
parameter [287:0] INIT_RAM_11 = 288'h0;
parameter [287:0] INIT_RAM_12 = 288'h0;
parameter [287:0] INIT_RAM_13 = 288'h0;
parameter [287:0] INIT_RAM_14 = 288'h0;
parameter [287:0] INIT_RAM_15 = 288'h0;
parameter [287:0] INIT_RAM_16 = 288'h0;
parameter [287:0] INIT_RAM_17 = 288'h0;
parameter [287:0] INIT_RAM_18 = 288'h0;
parameter [287:0] INIT_RAM_19 = 288'h0;
parameter [287:0] INIT_RAM_1A = 288'h0;
parameter [287:0] INIT_RAM_1B = 288'h0;
parameter [287:0] INIT_RAM_1C = 288'h0;
parameter [287:0] INIT_RAM_1D = 288'h0;
parameter [287:0] INIT_RAM_1E = 288'h0;
parameter [287:0] INIT_RAM_1F = 288'h0;
parameter [287:0] INIT_RAM_20 = 288'h0;
parameter [287:0] INIT_RAM_21 = 288'h0;
parameter [287:0] INIT_RAM_22 = 288'h0;
parameter [287:0] INIT_RAM_23 = 288'h0;
parameter [287:0] INIT_RAM_24 = 288'h0;
parameter [287:0] INIT_RAM_25 = 288'h0;
parameter [287:0] INIT_RAM_26 = 288'h0;
parameter [287:0] INIT_RAM_27 = 288'h0;
parameter [287:0] INIT_RAM_28 = 288'h0;
parameter [287:0] INIT_RAM_29 = 288'h0;
parameter [287:0] INIT_RAM_2A = 288'h0;
parameter [287:0] INIT_RAM_2B = 288'h0;
parameter [287:0] INIT_RAM_2C = 288'h0;
parameter [287:0] INIT_RAM_2D = 288'h0;
parameter [287:0] INIT_RAM_2E = 288'h0;
parameter [287:0] INIT_RAM_2F = 288'h0;
parameter [287:0] INIT_RAM_30 = 288'h0;
parameter [287:0] INIT_RAM_31 = 288'h0;
parameter [287:0] INIT_RAM_32 = 288'h0;
parameter [287:0] INIT_RAM_33 = 288'h0;
parameter [287:0] INIT_RAM_34 = 288'h0;
parameter [287:0] INIT_RAM_35 = 288'h0;
parameter [287:0] INIT_RAM_36 = 288'h0;
parameter [287:0] INIT_RAM_37 = 288'h0;
parameter [287:0] INIT_RAM_38 = 288'h0;
parameter [287:0] INIT_RAM_39 = 288'h0;
parameter [287:0] INIT_RAM_3A = 288'h0;
parameter [287:0] INIT_RAM_3B = 288'h0;
parameter [287:0] INIT_RAM_3C = 288'h0;
parameter [287:0] INIT_RAM_3D = 288'h0;
parameter [287:0] INIT_RAM_3E = 288'h0;
parameter [287:0] INIT_RAM_3F = 288'h0;
output reg [35:0] DO;
input [35:0] DI;
input [2:0] BLKSEL;
input [13:0] AD;
input WRE, CLK, CE, OCE, RESET;
reg [18431:0] bits;
initial begin bits = {INIT_RAM_3F, INIT_RAM_3E, INIT_RAM_3D, INIT_RAM_3C, INIT_RAM_3B, INIT_RAM_3A, INIT_RAM_39, INIT_RAM_38, INIT_RAM_37, INIT_RAM_36, INIT_RAM_35, INIT_RAM_34, INIT_RAM_33, INIT_RAM_32, INIT_RAM_31, INIT_RAM_30, INIT_RAM_2F, INIT_RAM_2E, INIT_RAM_2D, INIT_RAM_2C, INIT_RAM_2B, INIT_RAM_2A, INIT_RAM_29, INIT_RAM_28, INIT_RAM_27, INIT_RAM_26, INIT_RAM_25, INIT_RAM_24, INIT_RAM_23, INIT_RAM_22, INIT_RAM_21, INIT_RAM_20, INIT_RAM_1F, INIT_RAM_1E, INIT_RAM_1D, INIT_RAM_1C, INIT_RAM_1B, INIT_RAM_1A, INIT_RAM_19, INIT_RAM_18, INIT_RAM_17, INIT_RAM_16, INIT_RAM_15, INIT_RAM_14, INIT_RAM_13, INIT_RAM_12, INIT_RAM_11, INIT_RAM_10, INIT_RAM_0F, INIT_RAM_0E, INIT_RAM_0D, INIT_RAM_0C, INIT_RAM_0B, INIT_RAM_0A, INIT_RAM_09, INIT_RAM_08, INIT_RAM_07, INIT_RAM_06, INIT_RAM_05, INIT_RAM_04, INIT_RAM_03, INIT_RAM_02, INIT_RAM_01, INIT_RAM_00}; DO = 36'h0; end
integer i, w;
always @(posedge CLK) if (CE && BLKSEL == BLK_SEL) begin
    w = BIT_WIDTH == 9 ? (AD >> 3) : BIT_WIDTH == 18 ? (AD >> 4) : (AD >> 5);
    if (RESET) DO <= 36'h0;
    else if (WRE) begin
        for (i = 0; i < BIT_WIDTH; i = i + 1) bits[w * BIT_WIDTH + i] <= DI[i];
        if (WRITE_MODE == 2'b01) DO <= DI;
    end else for (i = 0; i < 36; i = i + 1) DO[i] <= (i < BIT_WIDTH) ? bits[w * BIT_WIDTH + i] : 1'b0;
end
initial if (READ_MODE != 1'b0) $display("SPX9 model: READ_MODE 1 not modelled");
endmodule
