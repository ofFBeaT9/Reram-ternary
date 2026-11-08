###############################################################################
# Created by write_sdc
###############################################################################
current_design tcim_chip_digital
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name clk -period 25.0000 [get_ports {clk}]
set_propagated_clock [get_clocks {clk}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bl_sen}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[0]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[10]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[11]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[12]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[13]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[14]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[15]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[16]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[17]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[18]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[19]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[1]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[20]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[21]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[22]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[23]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[2]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[3]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[4]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[5]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[6]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[7]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[8]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {bln_prg[9]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[0]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[10]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[11]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[12]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[13]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[14]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[15]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[16]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[17]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[18]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[19]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[1]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[20]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[21]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[22]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[23]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[2]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[3]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[4]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[5]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[6]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[7]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[8]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {blp_prg[9]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {flt}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {irq}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {miso}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {pamp[0]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {pamp[1]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {pamp[2]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {pamp[3]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {pamp[4]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {pk}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {pstb}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {ref_sel[0]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {ref_sel[1]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {ref_sel[2]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {sl_prg}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_hi[0]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_hi[10]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_hi[11]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_hi[12]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_hi[1]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_hi[2]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_hi[3]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_hi[4]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_hi[5]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_hi[6]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_hi[7]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_hi[8]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_hi[9]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_lo[0]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_lo[10]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_lo[11]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_lo[12]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_lo[13]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_lo[14]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_lo[15]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_lo[16]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_lo[17]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_lo[18]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_lo[19]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_lo[1]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_lo[20]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_lo[21]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_lo[2]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_lo[3]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_lo[4]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_lo[5]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_lo[6]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_lo[7]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_lo[8]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {tie_lo[9]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[0]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[10]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[11]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[12]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[13]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[14]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[15]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[16]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[17]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[18]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[19]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[1]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[20]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[21]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[22]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[23]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[24]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[25]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[26]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[27]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[28]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[29]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[2]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[30]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[31]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[32]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[33]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[34]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[35]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[36]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[37]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[38]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[39]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[3]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[40]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[41]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[42]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[43]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[44]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[45]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[46]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[47]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[48]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[49]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[4]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[50]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[51]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[52]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[53]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[54]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[55]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[56]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[57]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[58]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[59]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[5]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[60]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[61]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[62]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[63]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[64]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[65]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[66]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[67]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[68]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[69]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[6]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[70]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[71]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[7]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[8]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_on[9]}]
set_output_delay 7.5000 -clock [get_clocks {clk}] -add_delay [get_ports {wl_prog}]
set_false_path\
    -from [list [get_ports {cfg_tp[0]}]\
           [get_ports {cfg_tp[1]}]\
           [get_ports {cfg_tp[2]}]\
           [get_ports {cfg_tr[0]}]\
           [get_ports {cfg_tr[1]}]\
           [get_ports {cfg_ts[0]}]\
           [get_ports {cfg_ts[1]}]\
           [get_ports {cfg_ts[2]}]\
           [get_ports {cs_n}]\
           [get_ports {mosi}]\
           [get_ports {rst_n}]\
           [get_ports {sa_n[0]}]\
           [get_ports {sa_n[10]}]\
           [get_ports {sa_n[11]}]\
           [get_ports {sa_n[12]}]\
           [get_ports {sa_n[13]}]\
           [get_ports {sa_n[14]}]\
           [get_ports {sa_n[15]}]\
           [get_ports {sa_n[16]}]\
           [get_ports {sa_n[17]}]\
           [get_ports {sa_n[18]}]\
           [get_ports {sa_n[19]}]\
           [get_ports {sa_n[1]}]\
           [get_ports {sa_n[20]}]\
           [get_ports {sa_n[21]}]\
           [get_ports {sa_n[22]}]\
           [get_ports {sa_n[23]}]\
           [get_ports {sa_n[2]}]\
           [get_ports {sa_n[3]}]\
           [get_ports {sa_n[4]}]\
           [get_ports {sa_n[5]}]\
           [get_ports {sa_n[6]}]\
           [get_ports {sa_n[7]}]\
           [get_ports {sa_n[8]}]\
           [get_ports {sa_n[9]}]\
           [get_ports {sa_p[0]}]\
           [get_ports {sa_p[10]}]\
           [get_ports {sa_p[11]}]\
           [get_ports {sa_p[12]}]\
           [get_ports {sa_p[13]}]\
           [get_ports {sa_p[14]}]\
           [get_ports {sa_p[15]}]\
           [get_ports {sa_p[16]}]\
           [get_ports {sa_p[17]}]\
           [get_ports {sa_p[18]}]\
           [get_ports {sa_p[19]}]\
           [get_ports {sa_p[1]}]\
           [get_ports {sa_p[20]}]\
           [get_ports {sa_p[21]}]\
           [get_ports {sa_p[22]}]\
           [get_ports {sa_p[23]}]\
           [get_ports {sa_p[2]}]\
           [get_ports {sa_p[3]}]\
           [get_ports {sa_p[4]}]\
           [get_ports {sa_p[5]}]\
           [get_ports {sa_p[6]}]\
           [get_ports {sa_p[7]}]\
           [get_ports {sa_p[8]}]\
           [get_ports {sa_p[9]}]\
           [get_ports {sck}]]
###############################################################################
# Environment
###############################################################################
###############################################################################
# Design Rules
###############################################################################
