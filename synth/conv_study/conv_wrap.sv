// The result conversion alone, between two registers, in its two forms (synth/conv_study/run.sh):
//   CONV_CHAIN defined: the arithmetic definition, six divisions by three one after the other
//   otherwise:          the table that the design uses
module conv_wrap import tcim_pkg::*; (input logic clk, input logic signed [ACCW-1:0] v, output tryte_t t);
    logic signed [ACCW-1:0] vq;
    tryte_t c;
`ifdef CONV_CHAIN
    assign c = calc_tryte(vq);
`else
    assign c = int_to_tryte(vq);
`endif
    always_ff @(posedge clk) begin vq <= v; t <= c; end
endmodule
