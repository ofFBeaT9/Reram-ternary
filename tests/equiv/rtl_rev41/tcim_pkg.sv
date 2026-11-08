// tcim_pkg.sv - shared definitions for the TCIM0 ternary compute-in-memory device.
//
// Trit encoding on wires: two bits per trit. Two codes are supported and both are run through the full
// test bench (make rtl, make rtl-pnx):
//   default            two's complement:  +1 = 01, 0 = 00, -1 = 11; 10 is illegal
//   `define TCIM_ENC_PNX   BSD-PNX:       +1 = 10, 0 = 11, -1 = 01; 00 is illegal
// BSD-PNX is the binary-coded-ternary code of the REBEL group's own tools (ternary-workbench, radix "bsdpnx";
// S. Bos, PhD thesis, USN 2023, table 4.1). Use it when TCIM0 is attached to REBEL-6 hardware built with
// those tools. In both codes an illegal pair is read as 0, and every trit the device produces is legal.
// Nothing outside this package depends on the code values: trit registers reset to ZERO_TRYTE / ZERO_WORD.
package tcim_pkg;
    localparam int ROWS  = 72;            // inputs per tile  (3 words of 24 trits)
    localparam int COLS  = 24;            // ternary columns  (1 word of 24 trits per row of weights)
    localparam int WORD  = 24;            // trits per REBEL-6 word
    localparam int TRYTE = 6;             // trits per tryte
    localparam int ACCW  = 10;            // accumulator width, two's complement (covers +/-364)

`ifdef TCIM_ENC_PNX
    localparam logic [1:0] T_ZERO = 2'b11;
    localparam logic [1:0] T_POS  = 2'b10;
    localparam logic [1:0] T_NEG  = 2'b01;
`else
    localparam logic [1:0] T_ZERO = 2'b00;
    localparam logic [1:0] T_POS  = 2'b01;
    localparam logic [1:0] T_NEG  = 2'b11;
`endif
    localparam logic [2*TRYTE-1:0] ZERO_TRYTE = {TRYTE{T_ZERO}};   // a tryte of six zero trits
    localparam logic [2*WORD-1:0]  ZERO_WORD  = {WORD{T_ZERO}};    // a word of 24 zero trits

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

    // two's complement integer (-364 ... +364) -> 6-trit balanced-ternary tryte.
    // calc_tryte is the arithmetic definition. Hardware uses TRYTE_TABLE, which holds calc_tryte of every 10-bit value
    // and is built when the design is elaborated: as six chained divisions by three this function was the slowest path
    // of the design (13.9 ns on IHP SG13G2, typical corner, before layout); as a table it takes under 2 ns and fewer cells.
    typedef logic [2*TRYTE-1:0] tryte_t;
    typedef tryte_t tryte_table_t [1 << ACCW];

    function automatic tryte_t calc_tryte(input logic signed [ACCW-1:0] v);
        logic signed [ACCW+1:0] q;
        logic signed [ACCW+1:0] r;
        tryte_t t;
        q = (ACCW + 2)'(v); t = ZERO_TRYTE;              // sign-extended to 12 bits
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

    function automatic tryte_table_t build_tryte_table();
        tryte_table_t tab;
        for (int a = 0; a < (1 << ACCW); a++) tab[a] = calc_tryte($signed(ACCW'(a)));     // index = the two's complement bits
        return tab;
    endfunction
    localparam tryte_table_t TRYTE_TABLE = build_tryte_table();

    function automatic tryte_t int_to_tryte(input logic signed [ACCW-1:0] v);
        return TRYTE_TABLE[$unsigned(v)];              // a signed index would read outside the table for v < 0
    endfunction
endpackage
