source cell.tcl
rr_cell rr2t2r
select top cell
drc catchup
drc check
set n [drc listall count]
puts "DRC count: $n"
foreach {cell why} [drc listall why] { puts "DRC: $cell : $why" }
quit -noprompt
