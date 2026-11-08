# Timing constraints of tcim_top (the same assumptions as synth/sta.tcl). Self-contained: the flow copies this file.
current_design tcim_top
set clk_period 16.0   ;# slow corner ss_100C_1v60: about 15.4 ns was the shortest period after layout in revision 4.3
create_clock -name clk -period $clk_period [get_ports clk]
# The serial port is asynchronous to clk and enters through synchronizer flip-flops; the reset is asynchronous too.
set_false_path -from [get_ports {sck cs_n mosi rst_n}]
# The analog macro answers on clk: 30 % of the period for it, 30 % for the receivers of the outputs.
set arr_in [get_ports {arr_ack arr_sa_p* arr_sa_n* arr_adc*}]
set_input_delay  [expr 0.3 * $clk_period] -clock clk $arr_in
set_output_delay [expr 0.3 * $clk_period] -clock clk [all_outputs]
