# Standard cells written into the chip

`top.py` writes the standard cells of the chip's GDS from `sky130_fd_sc_hd.gds` here and uses `sky130_fd_sc_hd.spice`
here for LVS. Both are chosen so that the chip passes ChipFoundry's precheck in ChipFoundry's pinned versions
(cf-precheck 6c401ed: open_pdks 3e0e31dcce8519a7dbb82590346db16d91b7244f, Magic 8.3.471, netgen 1.5.272) and is also
correct by the newer cell layouts.

- `sky130_fd_sc_hd.spice`: the netlist of sky130B in open_pdks 3e0e31d, the PDK ChipFoundry's precheck and its analog
  template (`caravel_user_project_analog/Makefile`, OPEN_PDKS_COMMIT) pin; copied from ChipFoundry's ciel release site by
  `flow/eda/pc_batch20.sh`. It differs from open_pdks 1e35547 (the version used elsewhere in this repository) in one
  cell only: the tie cell `conb_1`, whose two polysilicon resistors are 0.045 um long here and 0.5 um in 1e35547.
- `sky130_fd_sc_hd.gds`: the library of open_pdks 1e35547 with one structure, `sky130_fd_sc_hd__conb_1`, replaced byte
  for byte by the 3e0e31d one (md5 2a5e1a68a1963e0177dae14cd1ce6cf6; built on 12 October 2026 by splicing the GDS
  records, no other change).

Why the mix (12 October 2026):

1. Batch 19: ChipFoundry's LVS (3e0e31d netlist) reported a property error on `conb_1` with the 1e35547 cell, whose
   resistor marker (GDS 66/15, which tells extraction the resistor's length) is 0.5 um. The 3e0e31d `conb_1` has a
   0.045 um marker. The polysilicon of the two is identical; the 3e0e31d cell also has a smaller nitride-poly-cut (NPC,
   95/20) shape.
2. Batch 21: with every cell from 3e0e31d, ChipFoundry's KLayout FEOL check reported one npc.2 violation (NPC spacing
   0.16 um < 0.27 um) at the left edge of an `and2_0` (instance _09919_ at 454.48, 92.48 in the logic block) next to an
   `a21boi_0`. The 3e0e31d `and2_0` has a notch in its NPC at x 0 to 0.16 um, y 1.345 to 1.715 um; 1e35547 fills it.
   Geometric differences between the two versions, after normalising polygon start points: `and2_0` (NPC),
   `and4b_2` (one poly shape), `conb_1` (66/15 marker, NPC), `o211a_2` (poly, licon; not used). All other cells are
   identical.

So the chip takes every cell from 1e35547 (with the later fixes) except `conb_1`, which comes from 3e0e31d so that
ChipFoundry's LVS sees the resistor it expects. The previous file (all cells from 3e0e31d) is not kept.
