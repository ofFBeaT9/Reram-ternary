source cell3.tcl
rr3_cell rr3t3r
select top cell
drc catchup
drc check
puts "CELL DRC total: [drc count total]"
foreach {cell why} [drc listall why] { puts "CELLWHY $cell : [lindex $why 0]" }
gds write rr3t3r.gds
# planted fault: a ReRAM element 0.20 um wide must be reported (rr1.1)
load fault3 -force
snap internal
p reram 0 0 0.20 0.20
p metal1 -0.05 -0.05 0.25 0.25
p metal2 -0.05 -0.05 0.25 0.25
select top cell
drc catchup
puts "DRC total fault: [drc count total]"
foreach {c w} [drc listall why] { puts "  $c : $w" }
quit -noprompt
