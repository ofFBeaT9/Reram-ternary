// tmac24.sv - digital baseline: the arithmetic of one REBEL-6 TMAC.T step on binary-coded trits.
//   acc_out = acc_in + sum over 24 lanes of a[i] * b[i]        (a, b: 24 trits, two bits per trit)
// Inputs and outputs are registered so that the synthesized block has a clean clock-to-clock path.
// A dense 72 x 24 product needs 72 of these steps (3 words of inputs for each of 24 columns).
module tmac24
    import tcim_pkg::*;
(
    input  logic                     clk,
    input  logic [2*WORD-1:0]        a,
    input  logic [2*WORD-1:0]        b,
    input  logic signed [ACCW-1:0]   acc_in,
    output logic signed [ACCW-1:0]   acc_out
);
    logic [2*WORD-1:0]      ra, rb;
    logic signed [ACCW-1:0] racc;
    logic [4:0]             n_pos, n_neg;

    always_comb begin
        n_pos = '0; n_neg = '0;
        for (int i = 0; i < WORD; i++) begin
            logic ap, an, bp, bn;
            ap = is_pos(ra[2*i +: 2]); an = is_neg(ra[2*i +: 2]);
            bp = is_pos(rb[2*i +: 2]); bn = is_neg(rb[2*i +: 2]);
            if ((ap & bp) | (an & bn)) n_pos = n_pos + 5'd1;
            if ((ap & bn) | (an & bp)) n_neg = n_neg + 5'd1;
        end
    end

    always_ff @(posedge clk) begin
        ra <= a; rb <= b; racc <= acc_in;
        acc_out <= racc + $signed({5'b0, n_pos}) - $signed({5'b0, n_neg});
    end
endmodule
