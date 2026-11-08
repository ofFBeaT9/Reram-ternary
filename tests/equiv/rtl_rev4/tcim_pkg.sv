// tcim_pkg.sv - shared definitions for the TCIM0 ternary compute-in-memory device.
//
// Trit encoding on wires: two bits per trit. The default is two's complement
// (+1 = 01, 0 = 00, -1 = 11; 10 is illegal and is read as 0). If the CPU's ternary_pkg uses a
// different code, change T_POS / T_NEG / T_ZERO here; nothing else depends on the code values.
package tcim_pkg;
    localparam int ROWS  = 72;            // inputs per tile  (3 words of 24 trits)
    localparam int COLS  = 24;            // ternary columns  (1 word of 24 trits per row of weights)
    localparam int WORD  = 24;            // trits per REBEL-6 word
    localparam int TRYTE = 6;             // trits per tryte
    localparam int ACCW  = 10;            // accumulator width, two's complement (covers +/-364)

    localparam logic [1:0] T_ZERO = 2'b00;
    localparam logic [1:0] T_POS  = 2'b01;
    localparam logic [1:0] T_NEG  = 2'b11;

    // array operations requested from the analog macro
    localparam logic [2:0] OP_READ      = 3'd0;   // compare each device with the mid reference
    localparam logic [2:0] OP_VFY_SET   = 3'd1;   // compare with the set target   (1 = at or above target)
    localparam logic [2:0] OP_VFY_RESET = 3'd2;   // compare with the reset target (1 = still above target)
    localparam logic [2:0] OP_PULSE_SET = 3'd3;   // set pulse on the masked devices, amplitude code amp
    localparam logic [2:0] OP_PULSE_RST = 3'd4;   // reset pulse on the masked devices
    localparam logic [2:0] OP_SUM       = 3'd5;   // analog sum of the rows in row_mask, result on adc

    localparam int AMP_STEPS = 21;        // 0.5 V ... 2.5 V in 0.1 V steps (published IHP scheme)

    function automatic logic is_pos(input logic [1:0] t); return t == T_POS; endfunction
    function automatic logic is_neg(input logic [1:0] t); return t == T_NEG; endfunction

    function automatic logic [1:0] sign_to_trit(input logic pos, input logic neg);
        return pos ? T_POS : (neg ? T_NEG : T_ZERO);
    endfunction

    // 6-trit balanced-ternary tryte -> two's complement integer (-364 ... +364)
    function automatic logic signed [ACCW-1:0] tryte_to_int(input logic [2*TRYTE-1:0] t);
        logic signed [ACCW-1:0] acc;
        logic signed [ACCW-1:0] w;
        acc = '0; w = 10'sd1;
        for (int i = 0; i < TRYTE; i++) begin
            if (is_pos(t[2*i +: 2])) acc = acc + w;
            else if (is_neg(t[2*i +: 2])) acc = acc - w;
            w = w * 10'sd3;
        end
        return acc;
    endfunction

    // two's complement integer (-364 ... +364) -> 6-trit balanced-ternary tryte
    function automatic logic [2*TRYTE-1:0] int_to_tryte(input logic signed [ACCW-1:0] v);
        logic signed [ACCW+1:0] q;
        logic signed [ACCW+1:0] r;
        logic [2*TRYTE-1:0] t;
        q = v; t = '0;
        for (int i = 0; i < TRYTE; i++) begin
            // balanced remainder in {-1, 0, +1}:  r = ((q + 1) mod 3) - 1 with a floor-style modulus
            r = q % 3;
            if (r < 0) r = r + 3;          // now 0, 1 or 2
            if (r == 2) begin
                t[2*i +: 2] = T_NEG; q = (q + 1) / 3;
            end else if (r == 1) begin
                t[2*i +: 2] = T_POS; q = (q - 1) / 3;
            end else begin
                t[2*i +: 2] = T_ZERO; q = q / 3;
            end
        end
        return t;
    endfunction
endpackage
