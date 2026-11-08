// the table read must equal the arithmetic definition for every one of the 1024 input values
module cmp import tcim_pkg::*; (input logic signed [ACCW-1:0] v, output logic ok, output tryte_t a, output tryte_t b);
    assign a = calc_tryte(v);
    assign b = int_to_tryte(v);
    assign ok = (a == b);
endmodule
