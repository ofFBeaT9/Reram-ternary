# Static timing analysis of a mapped TCIM0 netlist with OpenSTA (called by synth/run_sta.py).
# Environment: STA_LIB, STA_NETLIST, STA_TOP, STA_PERIOD (ns), STA_DRIVER (buffer cell), STA_LOAD (pF)
# Before layout: no wire capacitance or resistance, ideal clock, and the reset net is not buffered.
read_liberty $::env(STA_LIB)
read_verilog $::env(STA_NETLIST)
link_design $::env(STA_TOP)
set T $::env(STA_PERIOD)
create_clock -name clk -period $T [get_ports clk]
# The serial port is asynchronous to clk and enters through synchronizer flip-flops; the reset is asynchronous too.
set_false_path -from [get_ports {sck cs_n mosi rst_n}]
# The analog macro answers on clk; give it and the receivers 30 % of the period each.
set arr_in [get_ports {arr_ack arr_sa_p* arr_sa_n* arr_adc*}]
set_input_delay  [expr 0.3 * $T] -clock clk $arr_in
set_output_delay [expr 0.3 * $T] -clock clk [all_outputs]
set_driving_cell -lib_cell $::env(STA_DRIVER) [all_inputs]
set_load $::env(STA_LOAD) [all_outputs]
puts "@@ setup_wns [sta::worst_slack_cmd max]"
puts "@@ setup_tns [sta::total_negative_slack_cmd max]"
puts "@@ hold_wns [sta::worst_slack_cmd min]"
puts "@@ min_period [sta::find_clk_min_period [get_clocks clk] 0]"
puts "@@ BEGIN max path"
report_checks -path_delay max -format full -digits 3
puts "@@ END"
puts "@@ BEGIN reg2reg"
report_checks -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -digits 3
puts "@@ END"
puts "@@ BEGIN endpoints"
report_checks -path_delay max -format end -group_path_count 2000 -unique_paths_to_endpoint -digits 3
puts "@@ END"
puts "@@ BEGIN limits"
report_check_types -max_slew -max_capacitance -max_fanout -violators
puts "@@ END"
