# Timing constraints of tcim_chip_core: board clock up to 40 MHz (25 ns) at the slow corner.
current_design tcim_chip_digital
set clk_period 25.0
create_clock -name clk -period $clk_period [get_ports clk]
# asynchronous inputs: serial port (synchronized), reset, static configuration pins
set_false_path -from [get_ports {sck cs_n mosi rst_n cfg_ts* cfg_tp* cfg_tr*}]
# sense outputs: sampled by the controller T_SENSE cycles after the word line rises (settled by then; two flip-flops)
set_false_path -from [get_ports {sa_p* sa_n*}]
# outputs: level shifters and board, 30 % of the period
set_output_delay [expr 0.3 * $clk_period] -clock clk [all_outputs]
