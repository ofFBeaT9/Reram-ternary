// Behavioural models of the integrated clock-gating cells, for the gate-level runs (flow/orfs/post/gls.sh).
// The Liberty files describe these cells with a statetable and give GCLK no function, so Yosys cannot build a
// model from them. Behaviour as the IHP statetable states it (and as SkyWater's cells declare it with
// clock_gating_integrated_cell : "latch_posedge"): a latch, transparent while CLK is low, holds GATE (| SCE);
// GCLK = CLK & latch.
module icg_model (input CLK, input EN, output GCLK);
    reg q;
    always @(CLK or EN) if (!CLK) q = EN;
    assign GCLK = CLK & q;
endmodule
module sg13g2_lgcp_1 (input CLK, input GATE, output GCLK);            icg_model m (.CLK(CLK), .EN(GATE), .GCLK(GCLK)); endmodule
module sg13g2_slgcp_1 (input CLK, input GATE, input SCE, output GCLK); icg_model m (.CLK(CLK), .EN(GATE | SCE), .GCLK(GCLK)); endmodule
module sky130_fd_sc_hd__dlclkp_1 (input CLK, input GATE, output GCLK); icg_model m (.CLK(CLK), .EN(GATE), .GCLK(GCLK)); endmodule
module sky130_fd_sc_hd__dlclkp_2 (input CLK, input GATE, output GCLK); icg_model m (.CLK(CLK), .EN(GATE), .GCLK(GCLK)); endmodule
module sky130_fd_sc_hd__dlclkp_4 (input CLK, input GATE, output GCLK); icg_model m (.CLK(CLK), .EN(GATE), .GCLK(GCLK)); endmodule
module sky130_fd_sc_hd__sdlclkp_1 (input CLK, input GATE, input SCE, output GCLK); icg_model m (.CLK(CLK), .EN(GATE | SCE), .GCLK(GCLK)); endmodule
module sky130_fd_sc_hd__sdlclkp_2 (input CLK, input GATE, input SCE, output GCLK); icg_model m (.CLK(CLK), .EN(GATE | SCE), .GCLK(GCLK)); endmodule
module sky130_fd_sc_hd__sdlclkp_4 (input CLK, input GATE, input SCE, output GCLK); icg_model m (.CLK(CLK), .EN(GATE | SCE), .GCLK(GCLK)); endmodule
