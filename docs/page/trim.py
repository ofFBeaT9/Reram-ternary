"""Tighter wording for the prose blocks of the full page (8 November 2026). Keys: the first 10 hex digits of the md5 of the
block's HTML as generated (base_rev45.html and security_section.py); value: the new HTML, or "" to drop the block.
full.py applies it and reports any key whose block no longer exists, so a change upstream cannot pass unnoticed."""

TRIM = {
# 1 the idea
"08c1d70efc": "<p>REBEL-6 is the balanced-ternary processor of the University of South-Eastern Norway (USN). A ternary neural-network layer is a "
              "matrix-vector product, which REBEL-6 computes one multiply-accumulate (TMAC.T) at a time. TCIM0 holds the matrix in resistive memory "
              "and computes the whole 72 × 24 product in one command.</p>",
"f34f5cc261": "<figcaption>REBEL-6 reaches TCIM0's registers as memory; on the test chip a host reaches them through a four-wire serial port, and a test board supplies the programming voltages.</figcaption>",
"8858731ca9": "<p>Column j returns Y[j] = Σ<sub>r</sub> W[r][j] · X[r] over 72 rows, with W, X ∈ {−1, 0, +1}. The size follows REBEL-6's 24-trit word: "
              "the input is three words, a weight row one word, and each result fits a 6-trit tryte.</p>",
# 2 one weight
"db0e2f8db1": "<p>A ReRAM device has two stable states. A <i>set</i> pulse grows a conducting filament (low resistance, LRS); a <i>reset</i> pulse of "
              "opposite polarity breaks it (high resistance, HRS). Each weight uses two devices with their own select transistors on bit lines BL+ "
              "and BL−; each device is read as one bit, so the weight is recovered exactly.</p>",
"d3ff25b1ab": "<figcaption>One cell of the 72 × 24 array. In SkyWater's process a set device conducts 30–120 µS and a reset one about 4.5 µS. The encoding is prior art (Laborieux et al., 2020); TCIM0 differs in how it reads.</figcaption>",
"475879c9b2": "<p><b>Two levels, not four.</b> Two well-separated states are easier to program and read, and make the digital result exact.</p>",
"17d9f5c02e": "<p><b>Device model.</b> The Stanford-PKU compact model (the equations of SkyWater's open model): current falls exponentially with the gap "
              "between filament tip and electrode, and the tip moves exponentially faster with voltage and temperature, giving a sharp switching "
              "threshold. Python, ngspice and Verilog-A implementations agree. It has no forming, retention loss or cycle-to-cycle randomness.</p>",
"af5a84b946": "<p><b>Fit to SkyWater's silicon.</b> SkyWater publishes one yield figure: one 1 µs pulse resets 90.83 % and sets 97.45 % of cells. "
              "Fitting the reset rate and device spread to it (over three transistor widths and three pass criteria, which are not published) "
              "bounds the spread to 0.53–3.48 × the baseline, a factor of seven only measurement can narrow, and requires the published reset rate "
              "to be raised by 2.3–8.9 orders of magnitude.</p>",
# 3 structure
"f9acad36aa": "<p>A chip is a stack on silicon: transistors at the bottom, alternating metal wiring and insulating glass above. sky130B adds the ReRAM "
              "device between metal1 and metal2. Every picture here is drawn from the design's layout file (GDS) or the process data; where data "
              "are not published, the picture says so.</p>",
"98c6d00520": "<figcaption>The 2.92 × 3.52 mm user area, rendered from the chip's GDS (metal3 teal, metal4 orange, metal5 grey; other layers as in the cell legend). The pads are in the surrounding harness. Rendered from revision 4.5; revision 4.7 re-routed the digital block in the same footprint.</figcaption>",
"8d49f33875": "<figcaption>Top-left of the analog macro: the array and the word-line wiring to the drivers.</figcaption>",
"6bbda1b5ab": "<figcaption>Corner of the array, about 6 × 8 of the 1,728 cells; the pattern repeats 24 × 72 times.</figcaption>",
"250d97e2e1": "<figcaption>One 2T2R cell (3.6 × 3.0 µm), every rectangle from the GDS (hover for sizes). The two select transistors share the polysilicon word line; on each drain a contact stack climbs to a metal1 pad carrying the ReRAM, under the metal2 bit line. The joined sources go to the metal1 source line. A and B mark the cuts below.</figcaption>",
"bc16a3a375": "<p>The cell as built, oxide removed. Drag to turn; point at a part to see its material; click to change the stored weight and see the read-current path (double-click resets; arrows and Enter on a keyboard).</p>",
"85db31a53b": "<p>Materials and formulas of each layer, with their sources; where SkyWater publishes nothing, the table says so.</p>",
"c16bbe0edc": "<figcaption>Cut A–A′ through the BL+ transistor and its ReRAM. Lateral positions from the GDS, heights from the open_pdks sky130B stack (via1 is 0.295 µm taller than in sky130A to make room for the ReRAM). Dashed contacts lie 0.085 µm off the cut plane. The 11.6 nm gate oxide is too thin to show; isolation oxide and n+ depth are not in the open data and are not drawn.</figcaption>",
"c45ff8c2bd": "<figcaption>Cut B–B′ along the row through both ReRAMs: bit lines on metal2 above, source line on metal1 between.</figcaption>",
"d7a49318c2": "<figcaption>The ReRAM stack (TiN / Ti / HfO<sub>2</sub> / TiN, from SkyWater's documentation) and its states. Oxide thickness (5 nm) and filament limits (3.3–4.9 nm, gap 0.1–1.7 nm) are the Verilog-A model's parameters, to scale vertically; electrode and Ti thicknesses are unpublished and drawn for order only. Vacancies and filament shape are schematic.</figcaption>",
"de717b266a": "<p>The device cut through its filament, with the gap under your pointer; numbers from the design model.</p>",
"f886177819": "<p><b>Switching</b> (SkyWater's description). The field across the oxide creates and moves oxygen vacancies in HfO<sub>2</sub>; aligned "
              "vacancies form a filament, and the remaining gap sets the resistance, because current tunnels across it. The Ti layer is commonly an "
              "oxygen-exchange layer; SkyWater shows it but does not describe its role.</p>",
"62c1dea222": "<li><b>Forming, once.</b> A fresh device conducts below 0.1 µS; a first, higher pulse (2.2–3.1 V, 1 µs) creates the filament (30–120 µS). The test board does it through the normal programming path with a higher word-line rail. Not simulated: the model has no fresh state.</li>",
"c44f87b627": "<li><b>Set.</b> Bit line (top electrode) positive, source line grounded; the word-line voltage limits the current and so the final state. Proposed: word line 2.0 V, VPRG = 1.4 V + 0.1 V per step, until the device reads above the set target (24 µS nominal).</li>",
"d7595c5f9c": "<li><b>Reset.</b> Opposite polarity: source line at VPRG, bit line grounded. Proposed: steps 0–5 raise the word line from 2.5 V by 0.1 V with VPRG 2.4 V; from step 6 the word line stays at 3.0 V and VPRG rises from 2.5 V, until the device reads below the reset target (8 µS nominal).</li>",
"f25336f3ba": "<li><b>Read.</b> Bit line at 0.2 V, source line grounded; the sense amplifier compares the current with a reference (section 4). Read disturb and retention on SkyWater's devices are not in the model; the chip will measure them.</li>",
"3a00f1da11": "<p class=\"note\">Sources: layer stack from open_pdks <code>sky130B.tech</code>; layer meanings from SkyWater's GDS layer table; ReRAM materials, stack and switching from SkyWater's <code>sky130_fd_pr_reram</code> documentation and Verilog-A model; gate oxide from the <code>nfet_g5v0d10v5</code> model card; TiN and aluminum (not stated by SkyWater) from T. Edwards' open_pdks slides.</p>",
# hands-on
"82b82b150e": "<p>Each panel runs the device equation of the chip simulations or replays the stored simulation results; illustrative numbers are labelled.</p>",
"cd1bcc77f2": "<p class=\"hint\">Drag the slider: the filament grows across the 5 nm oxide, and the remaining gap sets the current at the 0.2 V read.</p>",
"aa7c17a547": "<p class=\"fine\">I = I<sub>0</sub>·exp(−g/g<sub>0</sub>)·sinh(V/V<sub>0</sub>), I<sub>0</sub> = 61.4 µA, g<sub>0</sub> = 0.2751 nm, V<sub>0</sub> = 0.43 V, gap 0.1–1.7 nm (SkyWater's parameters, as in <code>macro_sim.py</code>). References 8 / 12 / 24 µS nominal (shaded: range over corners). At the largest gap the model gives 0.31 µS, below SkyWater's measured 4.5 µS reset state.</p>",
"9f2c376b93": "<p class=\"hint\">Pick a case and press <b>Next pulse</b>: one 1 µs pulse through the drawn drivers, then a verify read, replayed from the stored simulation.</p>",
"10412e12ac": "<p class=\"fine\">Set starts at 4.5 µS and must pass the highest set-verify trip; reset starts at 60 µS and must fall below the lowest reset-verify trip. \"Slower\" devices reset 10–10,000 × slower than the fitted rate. Source: <code>results/sky130_chip/macro_sim*.json</code>.</p>",
"ae18998c32": "<p class=\"hint\">Click a weight to cycle +1 → 0 → −1, click an input to change it, then press <b>Step</b>. Each read compares every device with the 12 µS reference; the pair of answers is the weight. (This model shows revision 4.5's rule, which skipped rows with input 0.)</p>",
"d5d1881af2": "<p class=\"fine\">An 8 × 6 corner of the array; digital rule from <code>rtl/tcim_core.sv</code>. Conductances are <b>illustrative</b> (log-normal around 60 µS set, 4.5 µS reset, spread of your choice). A wide spread lets a device cross the read reference, which verify-after-programming prevents.</p>",
"f35fe6b912": "<p class=\"hint\">Step through one set pulse: the bit line's ground switch opens before the pulse rail connects.</p>",
"6587f9b9c5": "<p class=\"fine\">States from <code>rtl/chip/tcim_actl.sv</code>; ground = NOR(prg, bl_sen, flt). Durations not to scale.</p>",
# 4 reading
"60af43960d": "<figcaption>Read path of one bit line, transistor by transistor, from the simulated and drawn netlist (<code>periph.spice</code>, <code>sa</code>, <code>bld</code>). The cell's conductance is compared with a reference; one generator serves all 48 sense amplifiers with three selectable levels.</figcaption>",
"77825f3a3a": "<p>The three reference levels (2, 3 and 6 units of about 0.8 µA at 0.2 V: 8, 12 and 24 µS) are the <b>reset target</b>, the <b>read "
              "reference</b> and the <b>set target</b>. The gaps between them are guard bands: a device that passes verify is far from the read reference.</p>",
"78bb35e9f7": "<figcaption>Simulated trip points (green) over 45 cases: 5 corners × −40 / 27 / 125 °C × 1.62 / 1.80 / 1.98 V; whiskers: mismatch range (200 runs, reduced library; 48, full library).</figcaption>",
"3acb2076a6": "<p><b>Margins.</b> Under mismatch the read reference spans 10.40–14.46 µS, between the reset state (about 4.5 µS) and the lowest set state "
              "(30 µS). The lowest set target (21.55 µS) lies 7.1 µS above the highest read reference, so every verified set device reads as set. "
              "A read settles within 13.68 ns on the worst drawn bit line, inside the 4-cycle read window.</p>",
# 5 programming
"2cc79ec5b3": "<figcaption>IHP's published scheme, used unchanged: 1 µs pulses, amplitude rising one step per pulse over codes 0–20, a verify read after each.</figcaption>",
"87a96b9d38": "<p>The word line limits the device current and so sets where a set lands. Amplitudes come from the test board: the chip signals the next "
              "pulse (<code>pk</code>, <code>pamp</code>, <code>pstb</code>) and the board sets the rails, so the scheme can change after the first measurements.</p>",
"8d09bec9a5": "<p>Programming was simulated cell by cell through the drawn drivers with SkyWater's parameters and the fitted reset rate. Because a 1 µs "
              "pulse is too stiff for the transient solver, each pulse is integrated quasi-statically; where the transient converges, both agree within about 0.4 %.</p>",
"468ab855f4": "<figcaption>Slow corner, −40 °C, nominal wiring; target 27.36 µS (highest corner trip of the set verify).</figcaption>",
"7796be8cf9": "<figcaption>Worst drawn bit and source lines in series; target 29.84 µS (highest set-verify trip under mismatch).</figcaption>",
"ed8ca28231": "<p>SkyWater's set condition (1.7 V word line) misses the target at the slow corner, because the 1 µm select transistor limits the current. "
              "At <b>2.0 V</b> every corner reaches it in 7–8 pulses (9–11 with worst wiring). Reset takes 1–2 pulses at the fitted rate and up to 8 for "
              "cells three decades slower; cells four decades slower fail at the slow corner and −40 °C. No unselected device changed. Proposed board "
              "map: set at 2.0 V word line, VPRG 1.4 V + 0.1 V per code; reset stepped from 2.5 V.</p>",
# 6 chip
"f66ca2e8e3": "<p>SkyWater's ReRAM layer, rules and model are public, so a complete ReRAM chip can be drawn and checked with open tools. It is drawn for "
              "ChipFoundry's Caravan analog harness: 2.92 × 3.52 mm user area, 27 general-purpose and 11 direct analog pads, 1.8 V and 3.3 V supplies. "
              "All ReRAM levels are ≤ 3.3 V, so array-side circuits use SKY130's 5 V transistors on 3.3 V; logic and sensing use 1.8 V core devices.</p>",
"0c2052c33f": "<figcaption>New for the chip: the array controller, which turns each row request into timed line controls, and the analog macro, which level-shifts every control to 3.3 V.</figcaption>",
"dc2b2c07a6": "",
# 7 controller
"543e7ed94e": "<p>Each bit line goes to the pulse rail VPRG when its <code>prg</code> is high, to its sense amplifier when the shared <code>bl_sen</code> is high, "
              "and to ground otherwise (a 3.3 V NOR of <code>prg</code>, <code>bl_sen</code>, <code>flt</code>), so lines are grounded by default.</p>",
"c430fbc1ec": "<figcaption>Level shifters switch at different speeds, so a line driven straight from ground to VPRG could briefly short the rail. The controller raises <code>flt</code> one cycle before any mode change and drops it one cycle after: every line floats briefly between states.</figcaption>",
"7893e09c00": "<p>A request runs IDLE → BRK → MAKE → SETL → WLON → WLOFF → REL → BRK2 → GND → IDLE, with every macro control straight from a flip-flop. "
              "Durations are set by pins: T_SETTLE = 2<sup>ts+1</sup>, T_PULSE = 2<sup>tp+2</sup>, T_SENSE = 2<sup>tr+2</sup> cycles (16 MHz, <code>tp = 2</code>: 1 µs).</p>",
"395fc690f6": "<p>In a reset pulse a device that must not change keeps its bit line at VPRG with the source line (inhibit). Break-before-make lowers the "
              "peak rail current during a reset from 1,004 to 685 µA in simulation of the drawn slice.</p>",
"d22694e911": "<p><b>Test.</b> The full TCIM0 test bench runs through the controller and a line-level macro model that checks every cycle: no rail short, "
              "no driven sense input, at most one word line, no line floating under a word line or for more than two cycles, exact pulse and sense "
              "lengths. Current numbers are in the box above.</p>",
# 8 logic
"8f1fa62076": "<p>The SystemVerilog logic is identical in simulation, on the FPGA and on the chip: a four-wire serial port, a register block and three sequencers.</p>",
"550ed3bdd3": "<p>Offsets as in <code>rtl/tcim_core.sv</code>. Slot 11 and interrupt 7 in REBEL-6's address map are a proposal to be agreed with USN.</p>",
"ddcccb25f7": "<figcaption>A 4 × 3 corner computed by the sequencer's rule and checked against the plain sum. Each weight arrives as two sense bits (BL+, BL−): (1, 0) = +1, (0, 0) = 0, (0, 1) = −1; (1, 1) is invalid, flagged WERR and counted as 0.</figcaption>",
"2a31a6fee5": "<p><b>Programming a row</b> (PCMD = +) compares PDATA with each device's state and runs pulse-and-verify (section 5): reset, then set, "
              "pulsing only devices that still fail verify, over codes 0–20. Since 4.6 every step runs (an empty pulse once all devices have verified), "
              "so every command takes the same time. A device not verified after the last step sets WERR; PITER counts real pulses. <b>Read-back</b> "
              "(PCMD = −) fills PDATA from the array.</p>",
"b69d94eead": "<p><b>Why fault injection.</b> A passing test proves little alone: every copy of the logic with one planted fault must fail. The revision 3 "
              "bench passed 60,401 checks yet missed 30 of 66 faults and two real bugs. Every LVS, DRC, proof and gate-level run was also run once with a planted error.</p>",
"2fc0bc755f": "<p>Gate-level runs use Verilator (CXXRTL mis-simulated the flattened netlist; cause not found); the run fails as it must with one gate changed and with a clock gate stuck.</p>",
# 9 FPGA
"0c4caf4183": "<p>The logic ran on a Sipeed Tang Nano 9K (Gowin GW1NR-9) on 10 October 2026 with the array <b>emulated</b> in the FPGA: this tests the "
              "logic, serial protocol and programming loop at speed on hardware, not the ReRAM devices.</p>",
"5a946de546": "<figcaption>Set-up: host <code>tools/fpga_host.py</code>; FPGA design <code>rtl/fpga/</code>; bitstream SHA-256 in <code>results/fpga/bitstream_sha256.txt</code>.</figcaption>",
"49b6850acd": "<p><b>One run</b> programs a random 72 × 24 matrix (one third zeros) with pulse-and-verify, reads it back, and checks 100 digital and 100 analog "
              "products against exact arithmetic, for emulated device spreads of × 1, × 2 and × 3 the published value.</p>",
"f9de6f6893": "<figcaption>Weights wrong after programming, board and simulation; they draw different random devices, so they agree statistically.</figcaption>",
"023aa55c3f": "<p><b>Result.</b> At the published spread every weight programs correctly and every digital product is exact, on the board and in simulation. "
              "At × 2 and × 3 some devices cannot be programmed in 21 steps and the sequencer flags WERR rather than compute with wrong weights, as designed. "
              "The analog mode (not on the SKY130 chip) is off by 1–2 in most products, as expected without calibration. Gate-level and RTL simulations agree.</p>",
"8134bfceb3": "<p><b>What only the board caught.</b> The first bitstream computed every negative analog sum wrongly while all simulations passed: the emulator "
              "used the FPGA's signed hard multiplier, whose simulation model did not match the silicon. The emulator now uses unsigned products, and the "
              "build fails on a signed multiplier. TCIM0 was not affected; the lesson—a gate-level run is only as good as its cell models—applies to the chip.</p>",
"c85213f096": "<p>The evidence (files of 10 October, a hashed bitstream, the sources) is sound engineering evidence but <b>not yet publication-grade</b>; "
              "see <code>docs/FPGA_EVIDENCE.md</code>.</p>",
"52cea555f7": "<li>Every digital result of the 6 directed cases equals the dot product recomputed from the stored weights.</li>",
"e0f19fcf2f": "<li>Board and simulation agree where the design is deterministic and differ like independent draws where the emulated devices are random.</li>",
"b807a0810a": "<li>The board found a fault every simulation missed, and confirmed its fix.</li>",
"2a90e0ac16": "<li>No byte-level serial record or internal timestamps; files come from our own host program.</li>",
"263c3e97ed": "<li>No record of the board identity (JTAG IDCODE) or the bitstream load.</li>",
"b1d476e80d": "<li>No photo or video; no independent run.</li>",
"f8d7fe9a63": "<li>The source state was fixed only by the bitstream hash (the repository is now under version control).</li>",
"d2a9eaa759": "<p><b>Closing the gaps.</b> The host now records every serial byte with timestamps, host, bitstream and RTL hashes "
              "(<code>fpga_host.py --transcript</code>); <code>tools/fpga_verify.py</code> independently rebuilds every weight, input and result from that "
              "record and recomputes every product. On the simulation model it reproduced runs at × 1 and × 2 exactly and caught one altered byte. "
              "A recorded board re-run takes about 15 minutes (<code>docs/FPGA_EVIDENCE.md</code>).</p>",
# 10 layout
"2140cd4b9d": "<figcaption>Analog cells are written once as SPICE, simulated and drawn from the same netlist, and LVS proves the match; the logic goes through synthesis and place-and-route; all is assembled and checked.</figcaption>",
"3187258a14": "<p>All layout is generated by script in Magic. Twelve periphery cells, the analog macro (1,436.7 × 1,391.7 µm) and the user area each pass "
              "full-rule DRC and LVS, each with a planted error caught. The array is 86.4 × 216 µm: 3.6 × 3.0 µm cells, select transistor 1.0 / 0.5 µm.</p>",
"a4470a5106": "<figcaption>During plasma etching a long wire on a gate collects charge that can damage the oxide; a small diode gives it a path.</figcaption>",
"6f9971d3dc": "<p>At the top level 64 diodes protect inputs on long tracks. In revision 4.5 the two checkers disagreed inside the logic block (Magic's via4 "
              "figure is about four times stricter than OpenROAD's rule file); the block was re-routed with a 76 % repair margin until both reported 0. "
              "Revision 4.7 repeated this with a final 15 % pass (box above).</p>",
# 11 ChipFoundry
"b68e5c994d": "<p>ChipFoundry's precheck pins Magic 8.3.471, netgen 1.5.272, CVC 1.1.7, KLayout 0.29.12 and open_pdks 3e0e31d. Running it in these "
              "versions in October exposed two PDK-version differences:</p>",
"9af6524b9e": "<li><b>LVS</b>: a property error in the tie cell <code>conb_1</code>, whose resistor markers differ in length between versions.</li>",
"42af5194de": "<li><b>FEOL</b>, with every cell from their PDK: one npc.2 violation, where the older <code>and2_0</code>'s notched NPC shape leaves 0.16 µm against 0.27 µm required.</li>",
"5930dbead6": "<figcaption><code>conb_1</code> from both libraries, to scale (1.38 × 2.72 µm): LVS compares the marked resistor length with the netlist.</figcaption>",
"390ebc4fac": "<figcaption>The npc.2 finding, from the two cells' NPC shapes as placed (instance _09919_).</figcaption>",
"c88f53cfa3": "<p>Only four cells differ in geometry and only <code>conb_1</code> in netlist, so the chip takes <code>conb_1</code> from ChipFoundry's PDK and all "
              "other cells from the newer one (<code>layout/sky130/periph/stdcells_cf</code>). Result: LVS without property errors, DRC 0, antenna 0, and the precheck in their versions:</p>",
"9745e3f39a": "<p>CVC notes six soft 'unexpected voltage' entries on undriven controls of unused pads (io_out[0], io_out[1], io_oeb[0]); the check passes.</p>",
"3d6a968c2e": "<p>With <b>sky130A</b> (the template's default) LVS fails: sky130A has no ReRAM layer, so the 3,456 devices are not extracted. The chip must be processed as sky130B (a question for ChipFoundry).</p>",
# 12 limits
"aebbe1554b": "<p>The design meets device uncertainty structurally: a two-state read tolerant of twice the published spread, a digital mode independent of "
              "analog accuracy, verified programming, board-set levels, and a test cell with direct pad access.</p>",
"6fb5c6b8f7": "<p><b>Simplifications</b>:</p>",
"53a8aad30a": "<li>Analog cells were simulated from schematics (LVS-matched); long macro wires were assessed separately; short internal wiring was not back-annotated.</li>",
"346605738c": "<li>The set target's spread under mismatch may be up to 1.6 × the simulated one; covered by the worst-case programming run and read margin.</li>",
"6b78ed42b5": "<li>The two antenna checkers differ by about 4 × on one via figure; the block was routed until both pass.</li>",
"885ddebfff": "<li>CVC soft warning on undriven controls of unused pads 0–4 (as in ChipFoundry's own example).</li>",
# 13 security
"7d725a7156": "<p class=\"lede\">A review document (<i>AI Hardware Hacking</i>, @m1, 4 November 2026) lists attacks that recover weights or inputs from "
              "compute-in-memory chips and a twelve-item checklist. Each of its statements was checked against TCIM0 and each leak measured on TCIM0's "
              "model. Revision 4.6 applied the checklist; an independent review found four gaps, closed in 4.7 (<code>studies/hw-security-2026-11/</code>).</p>",
"39d284ea76": "<p>The sense amplifier's supply current (DC, SkyWater models, <code>sa_power.py</code>) follows a high-resistance device's conductance but is "
              "clamped for every low-resistance one, so the set-state spread does not reach the supply. Mismatch (100 samples) leaves frozen differences of "
              "0.1111 µA (LRS) and 0.0184 µA (HRS), standard deviation.</p>",
"a44a077c16": "<figcaption>One sense amplifier, tt 27 °C, read reference, DC. The supply sees how many devices of a row are low-resistance, not the weights' signs: with 2T2R a row draws more current the fewer zeros it holds.</figcaption>",
"c8e0bb82e0": "<p>Fixed-versus-random Welch t-test on this model (<code>tools/tvla_tcim0.py</code>: 5 µA noise per row read, 0.15 µA per flipping accumulator bit, LFSR start rows, mismatch as above; pass |t| &lt; 4.5):</p>",
"b423cb8f6f": "<figcaption>150,000 traces per group; red leaks, green passes. Zero-skipping leaked the inputs through product duration (|t| = 580.75); 4.6 removed that, but accumulator bit flips still followed the partial sums (19.55); 4.7's random offset removes it (3.59). The 2T2R read current still shows the weights' sparsity (14.24); constant-conductance cells (one-of-three, 4T4R) pass.</figcaption>",
"53d530b1cf": "<p>The one-of-three cell needs 4.7's uniform start row (with 4.6's folded start rows it leaks, 7.34). At 1 µA noise it still passes, near the "
              "limit (4.08): a small residual difference remains. Start rows: 4.6 gave rows 0–55 1,024 LFSR states each and rows 56–71 512; 4.7 (LFSR mod 72) gives 910 or 911.</p>",
"6754bd48d2": "<p>Programming (20,000 traces): stopping at verify leaks through duration (|t| = 48.94); constant step count removes that (0.0), but the "
              "pulse profile still leaks (65.67), because which devices each pulse selects depends on the data. Program weights in a trusted place.</p>",
"156ca55a81": "<p><b>Idle supply impedance</b> (DExiM-type attack; <code>idle_impedance.py</code>): one powered, idle column, all devices LRS versus all HRS, "
              "1 kHz–1 GHz. Largest relative |Z| difference: vdda 5.2e-07, vccd 3.3e-09, vprg 9.5e-07, vwl 5.8e-08 (a read in progress gives 0.49, so the "
              "method can see stored states). Not modelled: parasitics, device capacitance, package, unpowered chip.</p>",
"e6562589d4": "<p><b>Revision 4.6</b> (4 November): fixed-latency products (all 72 rows from an LFSR start row); constant-activity accumulation (dummy "
              "accumulators, ACT +50); constant-time programming (21 + 21 steps with empty pulses); SEC register (+3) with opt-ins ZSKIP, VARPROG, NOSHUF and "
              "a set-only LOCK; margin check (PCMD 0,+; MARG +52).</p>",
"b184a423f2": "<p>A SEC write while a command runs is ignored, so firmware should read SEC back after setting LOCK.</p>",
"996c6d0293": "<p class=\"note\">Found during verification and fixed: an untested MARG clear (test added); a planted proof fault that did not compile (rewritten); "
              "a planted gate fault on a dummy accumulator (moved to a real register); a start-row fault missed at proof depth 3 (now depth 20); one net 5 % "
              "over the antenna limit in Magic (final repair pass, block routed again).</p>",
}
