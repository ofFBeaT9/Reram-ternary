# Questions only other people can answer — drafts ready to send

Three short messages. Each item is something the design needs and that no simulation can settle.
Edit the greeting and signature, then send. Nothing here has been sent.

---

## 1. To IHP (MPW and prototyping service)

**Subject:** SG13G2 with MEMRES: design kit, device data and access for a small research design

Hello,

I am designing a small compute-in-memory test chip in SG13G2 that stores ternary weights in pairs of
MEMRES ReRAM cells (two states per device, 72 × 24 cells of 2T2R). The digital logic and the read path are
simulated with the open PDK. Before going further I would like to ask:

1. Your pages state that the MEMRES module comes with a design kit including layout and a Verilog-A
   simulation model. How is the kit obtained, under which agreement, and which tools does it support? Can a
   design made with the open PDK and KLayout include the MEMRES cell and be signed off?
2. What are the layer stack, the cell dimensions and pitch, and the metal levels between which the device sits?
   Which HfO2 deposition does the module use (precursor, temperature, amorphous or crystalline after the
   400 °C anneal)? Your 2018 study showed that this choice sets the cell-to-cell spread.
3. Which forming, set and reset voltages do you recommend in SG13G2, and which transistor types may carry them?
   In particular: what is the highest gate voltage allowed on the 3.3 V NMOS that selects a cell during reset?
   (Simulations with an assumed device spread need 3.0 to 3.3 V on the gate for every device to reset within
   the published 21-step ladder; at the published 2.7 V some do not. With the spread fitted to SkyWater's
   published yields the answer ranges from 2.7 V to more than 3.3 V, so the measured SG13G2 spread decides it.)
   And forming: your published arrays form with sweeps up to 5 V, and your 2018 study (Grossi et al.,
   Sci. Rep. 8, 11160) needed about 4.4 to 5 V for the most uniform film. SG13G2 has no transistor rated above
   3.3 V. What forming voltage does the MEMRES cell need, and how do you recommend bringing it to the bit line
   (stacked 3.3 V devices, a dedicated pad path, or a structure in the kit)? A path from stacked 3.3 V
   devices keeps every gate and channel voltage within 3.3 V once settled in simulation, but some devices
   exceed it for a few nanoseconds while switching: are such short excursions allowed? And with the source line
   along the column, the selected cell receives only about 3 V; is forming on wafer, or a forming structure in
   the kit, available instead?
4. Your process specification states VGS <= 3.3 V for HV NMOS with L >= 0.6 um and HV PMOS with L >= 0.5 um.
   May an HV NMOS of L = 0.45 um (the minimum) carry VGS = 3.3 V, and for how long in total? Our cell select
   transistors and word-line drivers use L = 0.45 um and switch 3.0 to 3.3 V during reset.
5. What is the kit's Verilog-A model calibrated to? Are measured statistics for the SG13G2 module available:
   read-current distributions of the programmed levels, relaxation after programming, read disturb, temperature?
6. Who may order MEMRES runs? Can an individual or a small company order directly, and under which agreements?
7. What are the confirmed 2027 tape-in and delivery dates for runs with MEMRES, the minimum area and the
   packaging options?

Thank you.

---

## 2. To ChipFoundry (SKY130 with ReRAM)

**Subject:** Next shuttle with the SKY130 ReRAM option

Hello,

I have designed a small ReRAM compute-in-memory test chip for the Caravan analog harness (sky130B, 3,456 ReRAM
devices in a 72 × 24 2T2R array with its drivers, sense amplifiers and logic). It passes your precheck (cf-precheck
6c401ed, all 14 checks) in the tool and PDK versions it pins (Magic 8.3.471, netgen 1.5.272, open_pdks 3e0e31d). Your
ReRAM page mentions a November 2025 ChipCreate shuttle, and your FAQ says chipIgnite does not initially support ReRAM.

1. Is there a current or upcoming shuttle that accepts the ReRAM layer? If so, what are its price, dates, user area
   and number of parts, and can a Caravan (analog) project use it?
2. Are the open `sky130_fd_pr_reram` cells, rules and model (version 2.0.3, April 2022) the current sign-off set? Your
   pinned PDK (open_pdks 3e0e31d), enabled for sky130B with ciel's default libraries, includes `sky130_fd_pr_reram` at
   commit d6d2a3c; the chip was drawn with open_pdks 1e35547. Is d6d2a3c the library you sign ReRAM projects off with?
   (An earlier draft of this question said your pinned PDK had no such folder; that came from enabling it with an option
   that left the library out.)
3a. The analog pads io_analog[4:6] carry our programming rails (0 to 3.3 V, driven by the board). Should their harness
   clamps (io_clamp_high/low[2:0]) be connected for this use, and does your LVS accept the clamp pin tied to the same net
   as its pad (two wrapper ports on one net)? Our other analog pads (reference, bias, test cell) have no ESD protection;
   is an on-chip diode pair to vdda1/vssa1 what you recommend there?
3. Which forming voltage does the option support, and through which devices (5 V transistors)?
4. Are measured statistics available beyond those in the open library: per-state read-current distributions
   after verify, relaxation, read disturb, temperature?
5. The open library gives reset conditions for the 1T1R test structure of word line 2.5 V, source line 2.6 V,
   1 µs, with a measured yield of 90.83 %, and 99.41 % on a 1T4R structure when the reset is stepped to 3 V.
   With the open Verilog-A model and the nfet_g5v0d10v5 model, a simulation of that 1T1R does not reset at any
   transistor width from 0.42 to 4 µm; it needs about 2.75 to 3.25 V on the word line. Which transistor width
   does the test structure use, which read voltage do the conductance figures refer to, and is the open model
   the one you use for sign-off, or has it been recalibrated since version 2.0.3?
6. Is sky130B (the ReRAM variant in open_pdks) the variant to design the whole chip in, including the logic, and will
   the chip be processed as sky130B? (With sky130A, the default of the analog template, your LVS does not extract the
   ReRAM devices.)
7. Which pass criteria (conductance after reset and after set, read voltage) and which select-transistor width
   does the yield table of the open library use? Fitting a model to the table, the answer moves the inferred
   cell-to-cell spread by a factor of about seven.

Thank you.

---

## 3. To the REBEL-6 maintainers at USN

**Subject:** A ReRAM ternary dot-product device for REBEL-6: slot, interrupt, trit code, simulator

Hello,

I am designing TCIM0, a memory-mapped ternary compute-in-memory device for REBEL-6 (one tile of 72 × 24
ternary weights, results equal to the corresponding TMAC.T sums). The register map follows
`rebel6-platform.md`. Four questions:

1. May an experimental device use memory-mapped slot 11 and interrupt source 7?
2. Your tools write binary-coded ternary as BSD-PNX (10 for +1, 11 for 0, 01 for −1, 00 illegal). Is that the
   code REBEL-6 hardware will use on wires? The device supports BSD-PNX and a two's-complement code.
3. The conformance suite runs on an R2R executor that takes `.tas` files and supports TMAC.T and
   memory-mapped devices. The public RV32IToREBEL repository (June 2025) has neither. Could I get access to
   the current executor, so that a device model can be attached and one program run against software TMAC.T?
4. Would you reserve encoding space for an accelerator extension once the device works?

Thank you.
