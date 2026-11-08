source cell.tcl
rr_cell rr2t2r
select top cell
drc catchup
foreach {c w} [drc listall why] { puts "WHY $c : $w" }
quit -noprompt
