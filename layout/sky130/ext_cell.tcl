source cell.tcl
rr_cell rr2t2r
select top cell
drc catchup
puts "DRC total: [drc count total]"
# fault: a ReRAM element 0.20 um wide must be reported (rr1.1)
load fault -force
snap internal
p reram 0 0 0.20 0.20
p metal1 -0.05 -0.05 0.25 0.25
p metal2 -0.05 -0.05 0.25 0.25
select top cell
drc catchup
puts "DRC total fault: [drc count total]"
foreach {c w} [drc listall why] { puts "  $c : $w" }
load rr2t2r
extract all
ext2spice lvs
ext2spice cthresh infinite
ext2spice -o rr2t2r.spice
quit -noprompt
