# 72 x 24 ternary TCIM0 tile on SKY130 (sky130B), from the rr2t2r cell (cell.tcl), with labels for LVS.
# Usage (magic -dnull -noconsole -rcfile <sky130B.magicrc> array.tcl): writes tcim_sky130_array.mag / .gds,
# the flat extracted netlist tcim_sky130_array.spice and prints the DRC result.
source cell.tcl
set ROWS 72; set COLS 24; set WC 3.6; set HC 3.0
rr_cell rr2t2r
file delete -force tcim_sky130_array.mag
load tcim_sky130_array -force
snap internal
box values 0um 0um 0um 0um
getcell rr2t2r
select cell rr2t2r_0
array count 0 [expr $COLS-1] 0 [expr $ROWS-1]
array pitch ${WC}um ${HC}um
select clear
# vss rail at the left edge, joined to the substrate-tie strip of every row
p metal1 -1.0 0.0 -0.6 [expr $ROWS*$HC]
for {set r 0} {$r < $ROWS} {incr r} {
    set y [expr $r*$HC]
    p locali -0.95 [expr $y+2.51] 0.0 [expr $y+2.77]
    p viali -0.885 [expr $y+2.555] -0.715 [expr $y+2.725]
    p poly 0.0 [expr $y+0.95] 0.1 [expr $y+1.45]; label WL$r w poly
}
set top [expr $ROWS*$HC]
for {set c 0} {$c < $COLS} {incr c} {
    set x [expr $c*$WC]
    p metal2 [expr $x+0.62] [expr $top-0.1] [expr $x+0.98] $top; label BLP$c n metal2
    p metal2 [expr $x+2.62] [expr $top-0.1] [expr $x+2.98] $top; label BLN$c n metal2
    p metal1 [expr $x+1.65] [expr $top-0.1] [expr $x+1.95] $top; label SL$c n metal1
}
p metal1 -1.0 [expr $top-0.1] -0.6 $top; label VSS n metal1
# labels sit on small pieces of the same layer drawn in this cell over the arrayed lines
# every label a port, in a fixed order: WL, BLP, BLN, SL, VSS
set i 1
foreach pfx {WL BLP BLN SL} n [list $ROWS $COLS $COLS $COLS] {
    for {set k 0} {$k < $n} {incr k} { port $pfx$k make $i; incr i }
}
port VSS make $i
save tcim_sky130_array
select top cell
drc catchup
set cnt [drc listall count]
puts "ARRAY DRC: [llength [drc listall why]] rule groups"
foreach {c w} [drc listall why] { puts "ARRAYWHY $c : [lindex $w 0]" }
gds write tcim_sky130_array.gds
# second DRC on a flattened copy (no reliance on hierarchical interaction checks)
flatten tcim_flat_check
load tcim_flat_check
select top cell
drc check
drc catchup
puts "FLAT DRC errors: [drc count total]"
foreach {c w} [drc listall why] { puts "FLATWHY $c : [lindex $w 0]" }
load tcim_sky130_array
extract all
ext2spice lvs
ext2spice hierarchy off
ext2spice subcircuit top on
ext2spice cthresh infinite
ext2spice -o tcim_sky130_array.spice
quit -noprompt
