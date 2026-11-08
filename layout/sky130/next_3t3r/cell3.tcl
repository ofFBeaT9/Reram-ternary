# 3T3R one-of-three ternary cell for SKY130 (sky130B), next-chip proposal (8 November 2026), drawn by script in magic.
# The 2T2R cell of ../cell.tcl with a third select transistor and ReRAM element: P (x 0), Z (x 2.0), N (x 4.0), each
# sky130_fd_pr__nfet_g5v0d10v5 W 1.0 / L 0.5 um with a 0.26 x 0.26 um ReRAM element on its drain under its own metal2 bit
# line (BLP, BLZ, BLN). Word line: poly along the row. Source line: metal1 between P and Z, joined to all three sources by
# a local-interconnect strip. Cell 5.6 x 3.0 um (2T2R: 3.6 x 3.0 um), substrate-tie strip along the top edge; lines reach
# the cell edges so arrayed cells connect by abutment. Exactly one of P, Z, N is low-resistance: +1 = P, 0 = Z, -1 = N.
proc b {x0 y0 x1 y1} { box values ${x0}um ${y0}um ${x1}um ${y1}um }
proc p {layer x0 y0 x1 y1} { b $x0 $y0 $x1 $y1; paint $layer }
proc rr3_cell {name} {
    file delete -force $name.mag
    load $name -force
    snap internal
    set WC 5.6; set HC 3.0
    foreach dx {0.0 2.0 4.0} {
        p mvndiff [expr 0.30+$dx] 0.20 [expr 1.30+$dx] 2.10
        p mvndc   [expr 0.40+$dx] 0.40 [expr 1.20+$dx] 0.57
        p mvndc   [expr 0.40+$dx] 1.70 [expr 1.20+$dx] 1.87
        p locali  [expr 0.32+$dx] 1.70 [expr 1.28+$dx] 1.87
        p viali   [expr 0.715+$dx] 1.70 [expr 0.885+$dx] 1.87
        p metal1  [expr 0.60+$dx] 1.65 [expr 1.00+$dx] 2.30
        p reram   [expr 0.67+$dx] 1.99 [expr 0.93+$dx] 2.25
        p metal2  [expr 0.62+$dx] 0.00 [expr 0.98+$dx] $HC
    }
    p poly 0.0 0.95 $WC 1.45
    p locali 0.32 0.40 5.28 0.57
    p viali 1.715 0.40 1.885 0.57
    p metal1 1.65 0.0 1.95 $HC
    p mvpsd 0.0 2.47 $WC 2.82
    p mvpsc 0.20 2.555 5.40 2.725
    p locali 0.0 2.51 $WC 2.77
    save $name
}
