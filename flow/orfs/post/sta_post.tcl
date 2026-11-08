# Timing of the routed TCIM0 block at one library corner, with the parasitics extracted by the flow (OpenRCX).
# Environment: POST_LIB (Liberty of the corner), POST_DIR (folder with 6_final.v, 6_final.spef, 6_final.sdc)
read_liberty $::env(POST_LIB)
read_verilog $::env(POST_DIR)/6_final.v
link_design [expr {[info exists ::env(DESIGN)] ? $::env(DESIGN) : "tcim_top"}]
read_sdc $::env(POST_DIR)/6_final.sdc
read_spef $::env(POST_DIR)/6_final.spef
puts "@@ setup_wns [sta::worst_slack_cmd max]"
puts "@@ setup_tns [sta::total_negative_slack_cmd max]"
puts "@@ hold_wns [sta::worst_slack_cmd min]"
puts "@@ BEGIN max path"
report_checks -path_delay max -digits 3
puts "@@ END"
puts "@@ BEGIN min path"
report_checks -path_delay min -digits 3
puts "@@ END"
puts "@@ BEGIN limits"
report_check_types -max_slew -max_capacitance -max_fanout -violators
puts "@@ END"
puts "@@ BEGIN skew"
report_clock_skew
puts "@@ END"
