# Pin sides: to the analog macro on the top edge, to the pads on the bottom edge.
set_io_pin_constraint -region top:* -pin_names {wl_on[*] wl_prog blp_prg[*] bln_prg[*] bl_sen sl_prg flt ref_sel[*] sa_p[*] sa_n[*]}
set_io_pin_constraint -region bottom:* -pin_names {clk rst_n sck cs_n mosi miso irq cfg_ts[*] cfg_tp[*] cfg_tr[*] pk pamp[*] pstb tie_hi[*] tie_lo[*]}
