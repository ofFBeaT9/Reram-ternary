# Power grid of tcim_chip_core: met1 rails, met4 / met5 straps, and VPWR / VGND rings on met4 / met5 around the core
# (the wrapper connects vccd1 / vssd1 to the rings). Net names VDD / VSS as the ORFS reports expect.
add_global_connection -net {VDD} -pin_pattern {^VPWR$} -power
add_global_connection -net {VDD} -pin_pattern {^VPB$}
add_global_connection -net {VSS} -pin_pattern {^VGND$} -ground
add_global_connection -net {VSS} -pin_pattern {^VNB$}
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {grid} -voltage_domains {CORE}
add_pdn_stripe -grid {grid} -layer {met1} -width {0.48} -pitch {5.44} -offset {0} -followpins
add_pdn_ring -grid {grid} -layers {met4 met5} -widths {3.1 3.1} -spacings {1.7 1.7} -core_offsets {2.0 2.0}
add_pdn_stripe -grid {grid} -layer {met4} -width {1.6} -pitch {56.0} -offset {13.6} -extend_to_core_ring
add_pdn_stripe -grid {grid} -layer {met5} -width {1.6} -pitch {56.0} -offset {13.6} -extend_to_core_ring
add_pdn_connect -grid {grid} -layers {met1 met4}
add_pdn_connect -grid {grid} -layers {met4 met5}
