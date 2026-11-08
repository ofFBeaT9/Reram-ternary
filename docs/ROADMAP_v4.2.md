# Balanced-Ternary ReRAM Accelerator for REBEL-6

Verified roadmap with simulation results, revision 4.2

9 October 2026. Prepared for the ReRAM ternary project.

Replaces the draft "Monolithic Multi-Level ReRAM Balanced Ternary Accelerator: Process Integration, Circuit Co-Design, and Co-Processor Interfacing for the REBEL-6 Architecture". The draft was checked claim by claim against primary sources: IHP's open PDK repository and process specification, the IHP and Europractice price and schedule pages, the REBEL-6 specification published by the USN research group, the peer-reviewed IHP device papers and component data sheets. Its arithmetic was re-run.

**Revision 3** parked tape-out and added the design work done in simulation (sections 18 and 19).

**Revision 4** is an audit of revision 3. Every quoted number was traced to a stored result, key results were derived a second time by a different method, the logic was attacked with deliberately broken copies to see whether its test bench notices, the code was read line by line, and the external facts were read again at their sources. Section 20 reports what held, what was wrong and what was changed. Corrections are made in place in sections 1 to 4, 6, 8 to 10, 12 to 14 and 16 to 19. The design repository reram-ternary is delivered with this document.

**Revision 4.1** (7 October 2026) adds section 21: static timing analysis, which found and removed one path too slow for the assumed clock; the trit code of the REBEL group's tools as a verified build option; and two equivalence proofs. The numbers of the logic in sections 1, 12, 18 and 19 are those of the present design. Section 20 still describes the audit as it was done on 6 October.

**Revision 4.2** (8 and 9 October 2026) adds section 22: place and route on IHP SG13G2 and SKY130 with timing after layout and gate-level runs of the routed netlists; lint, a second simulator and formal proofs; one change to the product sequencer; the array transistors drawn and checked with the PDK's full rule deck; first periphery circuits; the read path over temperature and supply; programming with device-to-device spread; and the cell on SkyWater's models. Sections 1 to 21 keep the numbers of revision 4.1, whose files are kept in results/rev41.

**Contents**

> 1 Summary
>
> 2 The corrections that change the plan
>
> 3 Routes to silicon
>
> 4 Device baseline
>
> 5 Compact model and simulation
>
> 6 Array architecture
>
> 7 Readout
>
> 8 Programming, verify and forming
>
> 9 REBEL-6 integration
>
> 10 Design flow
>
> 11 Test hardware and characterization
>
> 12 Game plan
>
> 13 Questions to send before spending money
>
> 14 Claim-by-claim ledger
>
> 15 Audit of the draft's references
>
> 16 What was not verified
>
> 17 Sources
>
> 18 Design results from simulation
>
> 19 Hand-over: continuing in Claude Code
>
> 20 Audit of revision 3
>
> 21 Changes after the audit (revision 4.1)
>
> 22 Changes of 8 and 9 October (revision 4.2)
>
> Appendix A Calculations

## 1 Summary

The idea in the draft is sound. Storing ternary weights {−1, 0, +1} in pairs of HfO<sub>2</sub> ReRAM cells, computing dot products in or beside the array, and presenting the block to a REBEL-6 processor uses building blocks that have each been demonstrated in published 130 nm silicon. The draft's route to building it does not hold up. Five findings decide the plan.

- **The open IHP flow has no ReRAM.** IHP's open-source PDK and its open-source shuttle runs contain no ReRAM device, model or design rule. ReRAM at IHP is a paid add-on module (MEMRES) with its own design kit. A minimum-size chip costs about €8,800 at 2026 list prices.

- **The material stack is not yours to design.** The layer thicknesses, the Al<sub>2</sub>O<sub>3</sub> barrier and the deposition recipes in the draft cannot be ordered on any shuttle, because the foundry's stack is fixed. The thermodynamic argument given for the Al<sub>2</sub>O<sub>3</sub> layer is also backwards.

- **The model parameters were never measured.** The table of "extracted" values mixes numbers copied from a published IHP paper with altered numbers and invented tolerances.

- **The readout cannot resolve its own output, and an analog sum cannot be exact.** The time-to-threshold converter separates at best 15 of the 129 possible results. With published IHP device spread, a 64-row analog sum has a standard deviation of 0.5 to 1.4 result steps.

- **The CPU interface contradicts the REBEL-6 specification.** REBEL-6 registers and data words are 24 trits (only instructions are 32 trits), its memory-mapped I/O layout is already defined, and it already has a ternary dot-product instruction, TMAC.T. The draft's "T-Bus", register addresses and custom opcodes are inventions.

Revision 2 kept the 2T2R ternary cell and replaced the rest: it uses the foundry's stack, makes multi-level programming optional (the 2T2R encoding needs only two states per device), adds an exact digital read mode beside the experimental analog mode, sizes the array to REBEL-6's 24-trit word, replaces the bus with a memory-mapped device that follows the published platform layout, and gives a staged plan whose first five phases, 0 to 4, cost nothing and run on your PC.

#### What revision 3 adds

Tape-out is parked. Design comes first, and this revision reports the design work that could be done in simulation with open tools: the device model, the cell with IHP's real transistor models, the tile in both read modes, a first read circuit, and the digital logic with its test bench. Section 18 gives the results and section 19 the hand-over. The main results:

- **The digital read mode is exact under the published device statistics**, with about 12 standard deviations of margin, and in the tile model it stays exact when the spread is doubled.

- **The analog mode is approximate by nature.** Device spread alone gives an RMS error of 0.41 result steps on a 72-row sum. A small ternary network still reaches the software accuracy.

- **In simulation the cell switches with IHP's real 3.3 V transistor model** when the select transistor is 4.5 µm wide. A 1.5 µm transistor cannot reset it.

- **The digital logic is written and verified**: 81,966 checks without a failure in each of two trit codes, every injected fault detected, and the synthesized netlist returns exact results. Before layout it meets the assumed 10 ns clock at all three corners of the IHP library (section 21).

- **One published parameter set does not reproduce its own paper.** The kinetic parameters had to be re-fitted (section 18.2). This also corrects a verdict in revision 2.

- **Energy is not the argument for this tile.** At this size the clocked logic dominates, and plain CMOS is in the same range. The argument is non-volatile storage in a fraction of the area.

#### What revision 4 corrects

Revision 4 is the audit of revision 3. Section 20 gives the method and the complete list. No simulated device, cell, tile or read-path result changed, and the cell count and energy estimate of the logic moved by about 1 % with its fixes. These findings change a statement or the design:

- **IHP's open-source runs are not free any more.** The free runs of 2023 to 2025 were paid for by a funded project. An open-source design now costs €2,800 per mm<sup>2</sup> in SG13G2. Revision 3 still called this route free (section 3).

- **IHP states that the MEMRES kit includes a Verilog-A simulation model.** It was not available here. It is the most valuable single item to ask for, because it replaces the stand-in model on which sections 18.2 to 18.6 rest (section 13).

- **Two faults in the digital logic were found by reading the code, and fixed.** After a failed command the interrupt could not be acknowledged, and the clocks after the 16th byte of an over-long serial frame were decoded as a new frame. Neither affected a computed result (section 20.3).

- **The test bench was weaker than its check count suggested.** Of 66 deliberately injected faults, the revision 3 test bench let 30 pass unnoticed. The extended test bench detects all 66 (section 20.4).

- **One description and one conclusion were wrong.** The tile model has a source line per column pair, not per row. Each source line then carries at most 1.2 mA while programming, which a 1 µm line is rated for. The 12 to 29 mA of a row is a requirement on drivers and supply, not on the lines (section 18.3).

- **The array area now has a lower bound from layout rules**, 0.018 mm<sup>2</sup>, beside the assumed 0.023 mm<sup>2</sup> (section 18.3).

#### What revision 4.1 adds

- **Timing analysis found one path too slow for the assumed 100 MHz clock**: 13.9 ns through the conversion of a register value to balanced ternary on its way to the serial port. Everything else had at least 4.5 ns to spare. The conversion is now a table, proven equal to its definition, and the logic has 3.3 ns to spare at the slow corner before layout (section 21.3).

- **The REBEL group's own tools use a two-bit trit code, BSD-PNX**, that differs from the code TCIM0 used. The REBEL-6 specification defines none. TCIM0 now builds with either code, and both pass the complete test bench and the fault campaign (section 21.2).

- **The logic of revision 4.1 was proven to be the same sequential function as the logic audited in revision 4**, at 2,410 comparison points (section 21.4).

#### What revision 4.2 adds

Revision 4.2 (8 and 9 October 2026) adds section 22. Place and route ran in Docker on your PC; the sandbox gained Verilator, SymbiYosys and SkyWater's transistor models. Sections 1 to 21 keep the numbers of revision 4.1; section 22 gives the present ones.

- **The logic meets the 10 ns clock after place and route** on IHP SG13G2 at all three corners (smallest setup slack 1.90 ns, slow corner; all hold slacks positive) and on SKY130 at the typical corner. On SKY130 the routed block passes the design-rule check and its layout matches its netlist; on IHP the only markers are chip-level metal-density rules. The routed netlists of both processes pass the complete test bench (sections 22.1, 22.2).

- **Lint, a second simulator and formal proofs** are now in place: no lint warning, the same results on Verilator as on CXXRTL, and unbounded proofs of the serial port and of the programming and product sequencers, each shown able to fail by injected faults (section 22.3).

- **One change to the logic**: a digital product now reads only the rows with a non-zero input, back to back. The estimated energy of the logic per product falls from 3.50 to 1.54 nJ. The change passed every check above and 74 injected faults (80 in the second code), all detected (section 22.4).

- **The array transistors are drawn and pass the PDK's full rule deck**, after fixing one rule that the rule count of section 18.3 had missed: 1.085 × 4.75 µm per device, about 0.021 mm<sup>2</sup> for the tile without the ReRAM element, whose layers are not public (section 22.7).

- **The read path holds over −40 to 125 °C and ±10 % supply**: trip current 24.24 to 24.86 µA, at least 9.4 µA from the six-sigma device tails. First periphery circuits (level shifter, word-line driver on the drawn poly word line, column switch) work at all corners (sections 22.5, 22.6).

- **Reset is the weak phase of programming.** With an assumed device-to-device spread, up to 12 of 100 simulated devices do not reset within the 21-step ladder at the published 2.7 V gate; at 3.0 or 3.3 V all do. Set always finishes (section 22.8).

- **SkyWater's ReRAM model has the same equations as ours**, and in that model the reset at SkyWater's published 1T1R conditions does not complete; it needs about 2.75 to 3.25 V on the word line. A question for ChipFoundry (section 22.9).

> **Limits of this document.** Facts that carry a source tag such as \[S8\] were checked on 6 October 2026 against that source, and the ones the plan depends on were read a second time from the page text for revision 4 (section 20.2). Sections 2 to 17 are the review of revision 2, with corrections marked where simulation changed a statement. Section 18 reports simulations. A simulation result is a statement about the models, and the models rest on published data from IHP's older 0.25 µm arrays. No measured data and no MEMRES design kit were available. Nothing in this document can state that the silicon will work; section 18.9 says what can and cannot be made certain. Design choices introduced here are marked **Proposal**.

## 2 The corrections that change the plan

Each row gives what the draft said, what the evidence shows, and what it does to the plan. The full claim-by-claim ledger is in section 14.

| **\#** | **Draft said** | **Evidence** | **Effect on the plan** |
|---|---|---|---|
| 1 | The IHP SG13G2 open PDK supports HfO<sub>2</sub> ReRAM cells between Metal1 and Metal2. | The open PDK (main branch of 1 Sep 2026 and dev branch of 6 Oct 2026) has no ReRAM device, model, DRC or LVS rule. Its only trace is a layer definition, "HafniumOx 143/0, MEMRES dielectric layer", which the decks subject to generic grid and angle checks only. IHP sells ReRAM as the MEMRES module for SG13G2. IHP's 2021 announcement places the cell between Metal2 and Metal3. \[S1, S2, S3, S5\] | ReRAM silicon needs a paid run and IHP's own design kit, or a different foundry (section 3). |
| 2 | A custom TiN / HfO<sub>2</sub> / Al<sub>2</sub>O<sub>3</sub> / Ti / TiN stack with chosen thicknesses and ALD recipes. | A shuttle customer cannot change the stack. Published IHP devices are TiN 150 nm / Ti 7 nm / Al-doped HfO<sub>2</sub> 6 nm / TiN 150 nm. None of the draft's thicknesses or recipes appears in the sources it cites. IHP's 2021 announcement of the module does say that HfO<sub>2</sub> and Al<sub>2</sub>O<sub>3</sub> switching layers are used in combination, without figures, so a two-layer oxide in the foundry module is possible. \[S5, S8, S9, S10, S27\] | The stack section is removed. Design starts from the foundry's published electrical data. |
| 3 | Al<sub>2</sub>O<sub>3</sub> is a better oxygen barrier because its enthalpy of formation (−1675.7 kJ/mol) is more negative than that of HfO<sub>2</sub> (−1144.7 kJ/mol). | The numbers are standard, the comparison is not. Per mole of oxygen the order reverses: HfO<sub>2</sub> −572, Al<sub>2</sub>O<sub>3</sub> −559, TiO<sub>2</sub> −472 kJ/mol. | The justification is deleted. It has no effect on the design because the stack is fixed. |
| 4 | Model parameters "extracted from IHP SG13G2 test vehicles" with tolerances. | No measurement exists. Two values come from a published IHP fit (g<sub>0</sub> 0.28 nm; I<sub>0</sub> 850 against 854 µA). Others differ from it: E<sub>a</sub> 0.98 against 0.6 eV, γ<sub>0</sub> 18.5 against 20, R<sub>th</sub> 2.1 × 10<sup>5</sup> against 1.5 × 10<sup>3</sup> K/W, oxide 7.7 against 6 nm. All tolerances are invented. \[S9\] | The parameter table is replaced by the published one (section 5) and labeled as a starting point. |
| 5 | A stabilized intermediate resistance state is the prerequisite for ternary storage. | The draft's own 2T2R encoding uses only HRS and LRS: +1 = (LRS, HRS), 0 = (HRS, HRS), −1 = (HRS, LRS). The paper it cites does the same with two-state devices. \[S11\] | Multi-level programming becomes an optional research track. First silicon needs two states. |
| 6 | The 2T2R array gives more than 38 dB common-mode rejection from −40 to 125 °C (ref. 2). | Ref. 2 reads each synapse digitally with a precharge sense amplifier, states that it does not sum currents, simulates 0 to 60 °C corners, gives no rejection figure, and reports 6.5 % and 18.5 % errors for the zero state. \[S11\] | The rejection figure is dropped. A digital read mode is added as the safe baseline. |
| 7 | A 6-bit time-to-threshold converter at 1 GHz digitizes each column. | 64 rows give 129 possible results. Time is proportional to 1/current, so codes bunch: at best 15 distinct codes for the 64 positive results, and zero or negative results never trigger. With the draft's 50 to 200 fF capacitor and a 0.5 V threshold, every result of 7 or more lands in the first clock period. | Readout is redesigned as a linear, signed conversion (section 7). |
| 8 | Bitline voltage drop stays below 2.1 % of the read voltage; results are compared with a bit-exact model. | With IHP's Metal2–5 sheet resistance (88 mΩ/sq) and published cell currents, a 64-row line at twice minimum width loses 8 to 24 % of the read voltage at its far end, for a cell pitch of 2 to 3 µm. Published device spread gives a result standard deviation of 0.5 to 1.4 steps for 64 rows. \[S2, S8\] | Analog mode is treated as approximate, with top-metal bitlines and limits on rows per read. Exactness comes from digital mode. |
| 9 | REBEL-6 uses 32-trit words; the accelerator sits on a "T-Bus" at tryte addresses 000001 to 000007 and adds four opcodes. | The specification gives 32-trit instructions, 24-trit registers and data words, 729 registers, 24-trit addresses, device windows of 6,561 trytes with slots 11 to 15 reserved, and a packed ternary dot product, TMAC.T. It defines no T-Bus. \[S13\] | The interface is rewritten as a memory-mapped device with 24-trit registers (section 9). |
| 10 | A QFN-64 chip talks to a Kria KV260 over a 32-trit bus; TPS7A4700 regulators supply 1.2 V; bitlines carry picoamperes. | The draft's bus has 152 wires. The KV260 has one 12-pin Pmod. The TPS7A4700 cannot regulate below 1.4 V. Published cell currents are 3 to 44 µA at 0.2 V. \[S23, S24, S8\] | The test chip gets a 4-wire serial port and about 25 pads (section 11). |

## 3 Routes to silicon

> **Parked.** No route is chosen and no money is committed until the design gates of section 12 are passed. This section is kept as reference for that later decision.

Status on 6 October 2026. Prices are list prices before tax. In revision 4 the prices and dates of IHP, Europractice, Tiny Tapeout and ChipFoundry were read again from the text of the pages themselves (section 20). They change, so confirm them before committing.

| **Route** | **What it provides** | **Design kit and tools** | **Cost** | **Schedule and conditions** |
|---|---|---|---|---|
| **A. IHP SG13G2 with MEMRES**, ordered from IHP or through Europractice | 130 nm BiCMOS with IHP's HfO<sub>2</sub>-based ReRAM module. 40 diced samples by default. \[S3, S4, S6\] | IHP's own kit. IHP states that the module comes with a process design kit that includes layout and a Verilog-A simulation model \[S3, S5\]. IHP's MPW page lists a Cadence-based kit and a Keysight ADS kit \[S32\]. MEMRES is absent from the open PDK. Which tools the MEMRES kit supports is an open question (section 13). | €7,300/mm<sup>2</sup> plus €2,500 per run plus €600/mm<sup>2</sup>. Minimum 0.8 mm<sup>2</sup>: **€8,820**. 1.0 mm<sup>2</sup>: €10,400. 1.5 mm<sup>2</sup>: €14,350. Europractice member rate for 0.8 mm<sup>2</sup>: €7,372. \[S3, S4\] | IHP lists MEMRES tape-ins on 7 Dec 2026 (shipment 2 Jul 2027), 31 May 2027 (3 Feb 2028) and 6 Dec 2027 (30 Jun 2028), each marked as a run with lower priority. Europractice lists its 2026 MEMRES deadlines as 5 May and 6 Nov. Europractice membership is for academic and public research bodies; companies can order at list price. \[S3, S4, S22\] |
| **B. IHP open-silicon MPW runs** for open-source designs | The devices of the open PDK: CMOS, SiGe HBT, resistors, capacitors. **No ReRAM.** Runs in SG13G2, and in SG13CMOS5L, a reduced CMOS option for open-source designs with four thin metals and one thick metal, no MIM capacitor and no isolated NMOS. 40 bare dies. \[S36\] | Fully open: Xschem, ngspice, KLayout, LibreLane. | **Not free.** SG13G2: €2,800 per mm<sup>2</sup>. SG13CMOS5L: €1,500 per mm<sup>2</sup>, falling to €900 as a run fills. The design is released under Apache 2.0, must work with open tools and is published in IHP's repository; a participation agreement is signed. Packaging is offered, for example 10 parts in QFN-32 for €710 plus €320 setup. The free runs of 2023 to September 2025 were paid for by the German FMD-QNC project. \[S36, S4, S7\] | SG13G2 open-source runs: 29 Sep 2026 (registration closed 21 Sep) and 4 Oct 2027. SG13CMOS5L: 9 Nov 2026 (registration until 26 Oct; the run starts only when 90 mm<sup>2</sup> are booked), then 30 Mar 2027 and 15 Nov 2027. Processing takes about 4 months for CMOS and 6 months for SG13G2. \[S3, S36\] |
| **C. Tiny Tapeout on IHP SG13G2** | A few tiles on a shared chip, with up to 6 analog pins. **No ReRAM.** \[S20\] | Fully open. | Analog projects need at least a 1×2 tile (from €140), plus €40 per pin for the first two analog pins and €100 per pin after that. \[S20\] | Shuttle dates vary. The prices on the page are given for the SKY130 shuttles. On 6 Oct 2026 the IHP analog templates listed there offer the core supply only and no 3.3 V analog supply, which the 3.3 V circuits of this design need. \[S20\] |
| **D. SkyWater SKY130 with ReRAM**, through ChipFoundry | 130 nm CMOS with a ReRAM option. An open ReRAM library exists, with layout cells, a Verilog-A model and DRC/LVS test cells. Its documentation reports forming at 2.2 to 3.1 V and a post-forming LRS of 30 to 120 µS. ChipFoundry continued these shuttles after Efabless closed in March 2025. \[S15, S19, S30\] | Fully open. The Verilog-A model uses the Stanford model equations. | ReRAM pricing is not published. For scale, a standard chipIgnite project is \$14,950 for 100 packaged parts, and the FAQ says chipIgnite "does not initially support ReRam"; ReRAM is offered on "ChipCreate" shuttles. \[S19\] | The ReRAM page names a November 2025 shuttle. The FAQ mentions three shuttles planned for 2026 without dates. Ask ChipFoundry. \[S19\] |
| **E. CEA-Leti MAD**, through CMP | ST 130 nm base wafers with Leti's HfO<sub>2</sub>/Ti OxRAM added on top. \[S21\] | Kit supplied through CMP. | Not public. | Announced in August 2018. Current availability was not verified. |

The draft also named Fraunhofer EMFT as a ReRAM shuttle provider. No public ReRAM multi-project offering from EMFT was found.

#### Recommendation

Do all modeling, circuit design and digital design with the open IHP PDK, and prove the readout chain on a CMOS-only chip through route B or C. Revision 2 called route B free; it now costs €2,800 per mm<sup>2</sup> in SG13G2, and route C's IHP templates list no 3.3 V supply, so cost and supply have to be checked before Phase 5 is planned. In parallel, obtain written answers and quotes for routes A and D (section 13). Choose the ReRAM route at Gate G3 in section 12. The December 2026 MEMRES run is too close for a design that does not exist yet, so plan for mid-2027 or December 2027.

Pad count sets the die size, and die size sets the price. The PDK's I/O cells are 80 µm wide and 180 µm deep with 180 µm corners \[S1\], so a square die of 0.8 mm<sup>2</sup> holds 24 pads, 1.0 mm<sup>2</sup> holds 32 and 1.5 mm<sup>2</sup> holds 40. The draft's 64-pin package needs at least 2.69 mm<sup>2</sup>, which costs €23,750 with MEMRES.

## 4 Device baseline

The design basis is IHP's published data, because that is the device a MEMRES run would deliver. The draft's device section is replaced by the table below.

**Table 4.1 Published IHP ReRAM data**

| **Item** | **Published value** | **Source** |
|---|---|---|
| **Stack** | TiN 150 nm / Ti 7 nm / Al-doped HfO<sub>2</sub> 6 nm (about 10 % Al, atomic layer deposition) / TiN 150 nm. Electrodes and Ti are sputtered. Cell area about 0.4 µm<sup>2</sup>. | S8, S9, S10 |
| **Integration** | A metal–insulator–metal cell between Metal2 and Metal3, added in 18 process steps (2021 announcement, SG13S). The same announcement says that HfO<sub>2</sub> and Al<sub>2</sub>O<sub>3</sub> switching layers are used in combination; the device papers describe a single Al-doped HfO<sub>2</sub> layer. The 2026 price lists offer the module for SG13G2. | S5, S3, S4 |
| **Arrays behind the statistics** | 4-kbit arrays of 64 × 64 one-transistor–one-resistor cells. The select transistor is an NMOS in 0.25 µm CMOS. | S8, S10 |
| **Forming** | Gate 1.5 V. Pulse amplitude swept from 2.5 to 5.0 V in 0.01 V steps, 10 µs pulses, until the read current reaches 42 µA. | S8 |
| **Reset** | Gate 2.7 V. Amplitude 0.5 to 2.5 V in 0.1 V steps, 1 µs pulses, target 6 µA. | S8 |
| **Set, three levels** | Gate 1.0, 1.2 and 1.5 V for targets of 16, 29 and 42 µA. Amplitude 0.5 to 2.5 V in 0.1 V steps, 1 µs pulses. | S8 |
| **Read** | 0.2 V, with the gate at 1.7 V. | S8 |
| **Read current after programming** | HRS 2.85 ± 1.85 µA. LRS1 18.08 ± 1.96 µA. LRS2 31.01 ± 1.60 µA. LRS3 43.59 ± 1.55 µA. Mean ± standard deviation of Gaussian fits. | S8, Table 2 |
| **Quasi-static resistance, 130 nm devices** | LRS1 16 kΩ, LRS2 11 kΩ, LRS3 8 kΩ at gate voltages of 1.0, 1.2 and 1.6 V. HRS 170 kΩ. | S9, Table 1 |
| **Endurance shown for multi-level use** | 1,000 reset–set cycles with the levels still separated. | S8, S10 |
| **Retention** | Stable at 85 °C. Strong drift at 200 °C. Ten years below 100 °C by extrapolation. Activation energy 0.97 to 1.16 eV depending on the level. | S10 |
| **Instability after programming** | After forming, about 13 % of cells fell below the target and about 3 % crossed into the neighboring level. The effect is much smaller after set. | S10 |

#### What this means for the design

- **The on/off ratio is small.** LRS1 is 6.3 times the HRS current and LRS3 is 15 times. An HRS cell still conducts about 2.85 µA at 0.2 V (about 70 kΩ), so the zero state is not free of current.

- **Two states are far apart.** HRS and LRS3 are separated by 12 combined standard deviations. Adjacent levels of the four-level scheme are separated by 3.6 to 4.0, which meets the draft's 3σ criterion.

- **Three levels per cell are plausible.** HRS, LRS1 and LRS3 are separated by 4.0 and 7.3 combined standard deviations. This supports a one-trit-per-cell memory as a later research track.

- **The voltages need thick-oxide transistors.** The publications use a 2.7 V gate and forming sweeps up to 5 V, on 0.25 µm transistors. SG13G2 offers 1.2 V transistors (gate limit 1.65 V) and 3.3 V thick-oxide transistors with a minimum length of 0.45 µm \[S2\]. Whether the SG13G2 module forms within the 3.3 V ratings is a question for IHP.

- **The statistics are optimistic for a new design.** They come from the 0.25 µm arrays and were read directly after programming. Expect wider distributions after relaxation and on a first layout.

#### Correction to the thermodynamics

| **Oxide** | **Standard enthalpy of formation, per formula unit** | **Per mole of oxygen atoms** |
|---|---|---|
| Al<sub>2</sub>O<sub>3</sub> | −1675.7 kJ/mol | −558.6 kJ/mol |
| HfO<sub>2</sub> | −1144.7 kJ/mol | −572.4 kJ/mol |
| TiO<sub>2</sub> (rutile) | −944.0 kJ/mol | −472.0 kJ/mol |

The first two values are the ones the draft quotes, and they are standard handbook values. Oxides must be compared per oxygen atom, and on that basis HfO<sub>2</sub> is the most stable of the three. The claim that aluminum binds oxygen more strongly than hafnium does not follow. The same comparison suggests that titanium cannot reduce stoichiometric HfO<sub>2</sub> wholesale; a titanium layer takes up a limited amount of oxygen at the interface, which is why the publications call it a scavenging layer. Forming is still required: the draft says the titanium layer removes the need for forming and later describes forming sweeps in its own bring-up section.

## 5 Compact model and simulation

### 5.1 Equations

The Stanford-PKU model has one state variable, the gap g between the filament tip and the electrode. The forms below are those of the published model and of the open SKY130 implementation \[S9, S15\].

Current through the cell:

> I = I<sub>0</sub> · exp(−g / g<sub>0</sub>) · sinh(V / V<sub>0</sub>)

Gap dynamics, with separate activation energies for vacancy generation and recombination:

> dg/dt = −v<sub>0</sub> · \[ exp(−E<sub>a,g</sub> / kT) · exp(+γ a<sub>0</sub> qV / (t<sub>ox</sub> kT)) − exp(−E<sub>a,r</sub> / kT) · exp(−γ a<sub>0</sub> qV / (t<sub>ox</sub> kT)) \]

When the two energies are equal this reduces to the single hyperbolic-sine form used in the IHP paper, with the factor of two absorbed into v<sub>0</sub>. The field enhancement factor depends on the gap:

> γ = γ<sub>0</sub> − β · (g / g<sub>1</sub>)<sup>3</sup> , g<sub>1</sub> = 1 nm

Filament temperature, as a thermal resistance and capacitance:

> C<sub>th</sub> · dT/dt = \|V · I\| − (T − T<sub>0</sub>) / R<sub>th</sub>

IHP's multi-level extension ties the smallest reachable gap to the gate voltage of the select transistor:

> g<sub>min</sub> = K<sub>th</sub> · (W / L) / V<sub>gate</sub> + C

Three points in the draft's version are wrong. Its current equation uses sinh(qV/αkT) in place of sinh(V/V<sub>0</sub>); V<sub>0</sub> is a fitted constant of 0.35 to 0.43 V, not a thermal voltage. It calls v<sub>0</sub> a jump-attempt frequency; v<sub>0</sub> is a velocity in meters per second. It presents the model as a merger of the Stanford-PKU and JART models; these are separate model families, and only one should be used.

### 5.2 Parameters

**Table 5.1 Model parameters: published values against the draft**

| **Parameter** | **Stanford defaults in the open SKY130 model \[S15\]** | **IHP fit, Stanford-PKU modified model \[S9, Table 3\]** | **Draft** | **Verdict on the draft** |
|---|---|---|---|---|
| I<sub>0</sub> | 61.4 µA | 854 µA | 850 ± 45 µA | Value copied; tolerance invented |
| g<sub>0</sub> | 0.275 nm | 0.28 nm | 0.28 ± 0.02 nm | Value copied; tolerance invented |
| V<sub>0</sub> | 0.43 V | 0.35 V | replaced by αkT/q | Wrong form |
| v<sub>0</sub> | 150 m/s | 0.4 m/s | "1.0 × …" (cut off), called a frequency | Wrong |
| E<sub>a</sub> | 1.501 eV generation, 1.500 eV recombination | 0.6 eV | 0.98 ± 0.04 eV | Not the printed IHP value. Close to the 1.0 eV this project now uses (section 18.2); tolerance invented |
| a<sub>0</sub> | 0.25 nm | not listed | 0.25 nm | Correct |
| t<sub>ox</sub> | 5 nm | 6 nm | 7.7 nm | Belongs to the hypothetical stack |
| γ<sub>0</sub> | 16.5 | 20 | 18.5 | Matches neither |
| β | 1.25 | 0.4 | not given | Missing |
| α | exponent of the gap term fixed at 3 | 3 (meaning not confirmed; probably the same exponent) | used as a different symbol inside sinh | Not comparable |
| R<sub>th</sub> | 7.2 × 10<sup>5</sup> K/W (from τ = 0.23 ns and C<sub>th</sub>) | 1,500 K/W | 2.1 × 10<sup>5</sup> K/W | Within the literature range; not IHP's value |
| C<sub>th</sub> | 0.318 fJ/K | none (static thermal model) | 0.18 fJ/K | Not in the cited source \[S26\] |
| Gap limits | filament 3.3 to 4.9 nm of a 5 nm oxide | maximum gap 1.8 nm; K<sub>th</sub> 0.52 nm·V; C 0.35 nm | not given | Missing |

Use the IHP column as the starting set and treat it as a starting set only. It was fitted to quasi-static sweeps of single devices in the IHP paper, not to pulsed array data, and it has not been checked against the SG13G2 MEMRES module. The four gap values the IHP paper uses for its levels are 0.95, 0.85 and 0.73 nm for LRS1 to LRS3 and 1.88 nm for HRS \[S9, Table 2\].

> **Correction in revision 3.** Revision 2 judged the draft's activation energy of 0.98 eV as matching neither source. Simulation shows that the printed IHP kinetic values (0.6 eV with v<sub>0</sub> = 0.4 m/s) do not reproduce the switching voltages measured in the same paper, and that a value near 1.0 eV does. The draft's number is still unsourced and its tolerance invented, but it is not far from a workable value. The static parameters of the IHP column are confirmed as usable. Details are in section 18.2.

### 5.3 Tool chain

- **Compiler.** Use OpenVAF-Reloaded (binary openvaf-r). The original OpenVAF has had no support since the end of 2023. The compiler writes an OSDI library, a .osdi file. \[S16\]

- **Simulators.** ngspice loads OSDI libraries; version 44 or later reads both OSDI 0.3 and 0.4, and version 43, which the PDK's version file lists, reads only 0.3. VACASK also loads them. Xyce does not: the IHP PDK builds Xyce plug-ins with ADMS through a separate script. \[S16, S1\]

- **Transistor models.** The IHP open PDK models its MOSFETs with PSP 103, compiled to psp103.osdi. The draft's "foundry BSIM4 models" do not exist in this PDK. \[S1\]

- **Model code (Proposal).** The published Stanford code advances the gap with a manual time-step update. Before relying on it under an OSDI simulator, rewrite the gap and the temperature as internal nodes integrated with ddt(), and confirm that it compiles and converges. This is the first task of Phase 1.

- **Variability (Proposal).** Model device-to-device spread as per-instance parameter variation in Monte Carlo runs, calibrated to the read-current statistics of Table 4.1. Add cycle-to-cycle spread by re-drawing parameters for each programming event in the test bench.

- **A second open flow.** The PDK also carries Verilog-A model sources with a Gnucap flow (libs.tech/gnucap): the PSP 103 models are compiled with gnucap-modelgen-verilog and come with reference tests, corners and a mismatch model. This flow was built and used for section 18, because OpenVAF could not be installed in the review environment. \[S1, S33\]

- **Calibration data.** No foundry test coupons are available to you. Calibrate against the published curves until a MEMRES kit or your own silicon provides data.

## 6 Array architecture

Everything in this section that is not a published number or a calculation from one is a **Proposal** to be confirmed in Phases 2 and 3.

### 6.1 The cell

Each weight uses two ReRAM devices and two select transistors on a pair of bitlines. This is the draft's encoding, and it is correct. It needs two resistance states per device.

| **Weight** | **Device on BL+** | **Device on BL−** | **Mean differential current at 0.2 V** |
|---|---|---|---|
| +1 | LRS | HRS | +40.7 µA with LRS3, +15.2 µA with LRS1 |
| 0 | HRS | HRS | 0, with a standard deviation of 2.6 µA |
| −1 | HRS | LRS | −40.7 µA with LRS3, −15.2 µA with LRS1 |

Multi-level programming still has three uses. The choice of LRS level trades signal against current. A one-trit-per-cell memory (HRS, LRS1, LRS3 in a single device) would give REBEL-6 a dense non-volatile ternary store, and Table 4.1 supports it. Weights with more than three values are possible later. None of these is needed for first silicon.

### 6.2 Two read modes

**Digital mode, the exact baseline.** One row is selected at a time. Each bitline current is compared with a reference between the HRS and LRS currents, each device is read as HRS or LRS, and the weight is recovered exactly. A counter per column then adds or subtracts the weight according to the input trit. With LRS3 and a reference near 25 µA the published distributions put the two states 12 standard deviations apart. With LRS1 the separation is 4.0, which predicts about 0.1 misread device in a 3,456-device tile. A matrix–vector product takes at most one read per row, and rows whose input trit is zero are skipped. The paper the draft cites for its cell also reads row by row \[S11\]. The difference proposed here is to sense each device against a reference instead of sensing the pair differentially, because that paper's differential sensing misread the zero state in 6.5 % to 18.5 % of cases.

**Analog mode, the experiment.** Several rows are selected together, their currents add on the bitlines, and the difference between BL+ and BL− is converted to a number. It is faster per product and it is approximate. The published 130 nm chip that works this way reports task accuracies, such as 99.0 % on MNIST and 85.7 % on CIFAR-10, and not exact arithmetic \[S12\].

Building both modes on the same array lets the first chip deliver a correct function whatever the analog results are, and lets the measurements decide whether analog mode earns its place.

### 6.3 Signed inputs in analog mode

A wordline can switch a row on or off. It cannot apply a negative input. A ternary input vector is therefore evaluated in two phases: phase P selects the rows whose input is +1, phase N selects the rows whose input is −1, and the result is P minus N. This doubles the read time and adds no cell area. The draft's "wordline DACs" do not solve the problem, because a transistor gate is not a linear multiplier.

### 6.4 Tile size

The draft's tile of 64 rows by 32 ternary columns does not fit REBEL-6's 24-trit word: 64 input trits are 2.67 words. A tile of **72 rows by 24 ternary columns** takes its input as exactly three words, stores one row of weights as exactly one word, and returns 24 results. Each result lies between −72 and +72 and fits in one 6-trit tryte, whose range is ±364. The tile has 1,728 weights and 3,456 devices. The draft's sixteen 64 × 64 tiles would hold 65,536 devices; first silicon should carry one tile and a set of single-cell test structures.

### 6.5 What the numbers allow

**Table 6.1 Analog-mode result error from device spread alone**

| **Rows active in one read** | **LRS1: standard deviation in result steps** | **LRS1: chance the result is off by one or more** | **LRS3: standard deviation in result steps** | **LRS3: chance the result is off by one or more** |
|---|---|---|---|---|
| 24 | 0.87 | 56 % | 0.29 | 8.5 % |
| 64 | 1.42 | 72 % | 0.47 | 29 % |
| 72 | 1.50 | 74 % | 0.50 | 32 % |

Calculated from the Table 4.1 statistics with a Gaussian model, all weights non-zero. One result step is the LRS-minus-HRS current. The error is fixed at programming, so one chip returns a repeatable but shifted result. Read noise, drift and voltage drop come on top.

An exact integer result from a 64- or 72-row analog sum is out of reach with these devices. The spread corresponds to roughly 5 to 6 bits of resolution over the full range with LRS3, and about 4 to 5 bits with LRS1. LRS3 is the better level for accuracy and the worse one for current.

**Table 6.2 Far-end bitline voltage error, 72-row line, all rows selected and in LRS**

| **Bitline metal and drive** | **LRS1, 2 µm pitch** | **LRS1, 3 µm pitch** | **LRS3, 2 µm pitch** | **LRS3, 3 µm pitch** |
|---|---|---|---|---|
| Metal2–5, 0.4 µm wide, clamped at one end | 9.6 % | 13.9 % | 20.8 % | 28.7 % |
| Metal2–5, 1.0 µm wide, clamped at one end | 4.0 % | 6.0 % | 9.3 % | 13.4 % |
| Metal2–5, 0.4 µm wide, clamped at both ends | 2.6 % | 3.8 % | 6.1 % | 8.9 % |
| TopMetal1, 1.64 µm wide, clamped at one end | 0.5 % | 0.8 % | 1.2 % | 1.9 % |

Percent of the 0.2 V read voltage. Resistive-ladder solution with IHP sheet resistances of 88 mΩ/sq for Metal2–5 and 18 mΩ/sq for TopMetal1 \[S2\]. The cell pitch is an assumption; the real value comes with the foundry's cell. A design-rule estimate for the 4.5 µm transistor of section 18.3 gives a row pitch near 1.1 µm, which would roughly halve these figures.

The draft's remedy, twice-minimum width with ground straps every 16 columns, does not reach its claimed 2.1 %. Ground straps do not lower bitline resistance. TopMetal1 bitlines do reach it, at the price of a bitline pitch of at least 3.28 µm, because TopMetal1's minimum width and spacing are both 1.64 µm \[S2\].

**Table 6.3 Current limits from the IHP process specification**

| **Layer** | **Limit, 11 years at 105 °C** | **Relevance** |
|---|---|---|
| Metal1 (0.42 µm thick) | 0.36 mA for widths of 0.16 to 0.36 µm; 1 mA per µm above that | Equals 2.4 × 10<sup>5</sup> A/cm<sup>2</sup>. The draft states 1.5 × 10<sup>5</sup> A/cm<sup>2</sup>. |
| Metal2 to Metal5 (0.49 µm thick) | 0.6 mA for widths of 0.2 to 0.3 µm; 2 mA per µm above that | A 72-row bitline carries up to 3.14 mA with LRS3 and 1.30 mA with LRS1, which needs 1.6 µm or 0.65 µm of width. |
| TopMetal1 (2 µm thick), TopMetal2 (3 µm thick) | 15 mA per µm and 16 mA per µm | These are the thick metals. The draft calls Metal4 and Metal5 thick; they are thin. |
| Vias | 0.4 mA per via between thin metals; 1.4 mA per TopVia1; 10 mA per TopVia2 | Use via arrays on bitlines and supply trunks. |

Source: SG13G2 Process Specification Rev. 1.2, sections 2.13, 2.15 and 2.16 \[S2\].

The draft's electromigration paragraph has three errors. Its 1.6 mA is the total of 32 bitlines; each bitline carries 50 µA, which a minimum-width Metal1 line carries seven times over. Its fix, a 0.48 µm Metal1 line, could not carry 1.6 mA in any case: the limit for that width is 0.48 mA. The shared supply trunk is what needs width: 1.6 µm of Metal1, 0.8 µm of Metal2–5, or any TopMetal1 line.

Leakage of unselected rows is small and not zero. The specification gives 0.1 nA per µm typical and 1 nA per µm maximum for thin-oxide NMOS, and 0.3 pA per µm typical for thick-oxide NMOS, at 27 °C \[S2\]. Seventy-one unselected rows add a few nanoamperes to bitlines that carry microamperes. This holds for any one-transistor cell and is not a property of the 2T2R pairing.

### 6.6 Design consequences

- Use two states, HRS and LRS3, for first silicon. Revisit the LRS level in Phase 2 with current and voltage drop included.

- Make digital mode the functional baseline and analog mode a measured experiment.

- In analog mode, run the bitlines in TopMetal1 or clamp them at both ends. With that wiring the simulation in section 18.4 shows no benefit from limiting a read to 24 rows, so the limit proposed in revision 2 is dropped.

- Keep the input resistance of the analog-mode bitline clamp below about 5 Ω (section 18.4).

- Give each column an offset and gain calibration. Per-cell error cannot be calibrated away and has to be carried as weight noise in training and evaluation.

- Compare analog-mode silicon with a noise-aware model, and digital-mode silicon with the exact model.

## 7 Readout

### 7.1 Why the draft's converter fails

The draft charges a capacitor with the differential current and records the count of a 6-bit, 1 GHz counter when the capacitor reaches a threshold:

> t<sub>int</sub> = C<sub>int</sub> · V<sub>ref</sub> / I<sub>diff</sub>

The formula is right and the architecture is not, for four reasons.

- **Range.** Sixty-four rows give results from −64 to +64, which is 129 values. Six bits give 64 codes.

- **Non-linearity.** Time goes as one over current. If the capacitor is chosen so that a result of 1 takes the full 64 ns window, results of 8 and above are less than one clock period apart, and the 64 positive results share 15 codes. That best case needs a capacitor of about 2 pF with LRS1 currents and a 0.5 V threshold.

- **The stated capacitor.** With the draft's 50 to 200 fF, a 0.5 V threshold and the published cell currents, a result of 1 takes 0.6 to 6.6 ns, and every result of 7 or more falls inside the first clock period.

- **Sign and zero.** A zero or negative differential current never reaches the threshold, so zero, a frequent result when weights and inputs are sparse, has no code.

The draft's comparison with a flash converter (1450 against 320 µm<sup>2</sup>, 1.8 mW against 45 µW, "up to 70 % of macro area") has no source and no design behind it, and is removed. Its conclusion that the scheme saves more than 75 % of peripheral area and an order of magnitude of power falls with it.

### 7.2 Digital mode (Proposal)

Each bitline is clamped near 0.2 V and the cell current is compared with a reference of about 25 µA for LRS3. The comparator output is latched as one device state; two latches give one weight. A tile needs 48 comparators, or 24 used twice.

A first version of this circuit was simulated with the PDK's transistor models (section 18.6). It uses a plain clamp transistor biased from a replica in place of the regulated cascode proposed in revision 2. That is cheaper and it resolves the two states in about 3 ns, but it lets the bitline rise to about 0.3 V when the cell current is small. Whether that is acceptable depends on read disturb, which only measurements can settle.

### 7.3 Analog mode (Proposal)

The converter must be signed, must have a code for zero, and must be linear in current. Two options meet this.

- **Charge-packet counting over a fixed window.** Each mirrored bitline current charges a capacitor. Every time the capacitor crosses a threshold, a fixed packet of charge is removed and a counter steps up for BL+ or down for BL−. After a fixed window the count is proportional to the differential current. An illustrative sizing for LRS3: a 1:32 mirror, a 1 pF capacitor and a 0.5 V threshold give a 0.5 pC packet and 2.5 MHz per result step. Seventy-two steps give 183 MHz. A 1.6 µs window gives four counts per step and a full scale of ±288, which a 10-bit up/down counter covers.

- **A shared successive-approximation converter** after a current-to-voltage stage. The published 130 nm chip uses voltage-mode sensing with a charge-based binary search \[S12\].

Phase 3 chooses between them by simulation across corners and mismatch.

## 8 Programming, verify and forming

Closed-loop programming is necessary, as the draft says. Its numbers (1.6 V, 25 ns pulses, 25 mV gate steps, 16 attempts) have no source: the paper it cites describes a 22 nm FinFET ReRAM macro. Start from the algorithm IHP has published for this device, in Table 4.1.

- **Published scheme.** The gate voltage is fixed per target level and sets the current limit. The pulse amplitude steps up by 0.1 V from 0.5 to 2.5 V, at most 21 pulses, with a read at 0.2 V after each pulse. Pulses are 1 µs for set and reset and 10 µs for forming.

- **Pulse length.** A 25 ns pulse is unproven for this device. Begin at 1 µs and shorten it by experiment.

- **Forming.** Every cell needs one forming operation before use, with the current limited by the gate voltage.

- **Relaxation.** Read each cell again after a delay and re-program the ones that moved. The published 130 nm chip uses a ±1 µS acceptance window and three programming passes for this reason \[S12\].

- **On-chip circuits needed.** A wordline driver with selectable levels (1.0, 1.2, 1.5, 1.7 and 2.7 V in the publications), an amplitude-programmable driver for bitline and source line, a path for the forming voltage, level shifters between the 1.2 V and 3.3 V domains, and the verify comparator.

- **Simulated in revision 3 (section 18.3).** The select transistor must be about 4.5 µm wide at 0.45 µm length. One gate voltage per level does not survive process corners, so the two-state design uses one generous gate voltage (1.7 V) and stops on the verify read. A device draws about 0.5 mA during a set or reset pulse, so a row programmed in parallel needs 12 to 29 mA from its drivers; a source line that serves one column pair carries at most 1.2 mA of it.

- **Where the sequencer lives (Proposal).** For first silicon keep the pulse sequencing in the host FPGA, driven through the serial port. The algorithm will change during characterization, and a sequencer in the FPGA can change with it. Move it on chip in the second version.

## 9 REBEL-6 integration

### 9.1 What the specification says

The facts below come from the REBEL-6 documents in the USN research group's public repository, at the commit of 11 August 2026 \[S13\]. The specification is still changing, so re-check it when you start the digital work.

**Table 9.1 REBEL-6 facts that bear on the accelerator**

| **Item** | **Specification** |
|---|---|
| Widths | Instructions are 32 trits. Registers and data words are 24 trits. A word is four 6-trit trytes, stored little-endian. |
| Registers | 729, numbered X−364 to X+364. X0 reads as zero. The negative range holds system and streaming state, so not all 729 are general purpose. |
| Memory | Harvard. Instruction space is addressed in instruction slots, data space in trytes. Addresses are 24 trits. |
| Memory-mapped I/O | The region of the data space whose most significant trit is −. Each device occupies one or more slots of 3<sup>8</sup> = 6,561 trytes. Slots 0 to 10 and 16 to 26 are assigned; slots 11 to 15 are reserved. |
| Access rules | Reads and writes happen exactly as issued. Tryte access is allowed and is the natural width for control registers. Misaligned access is an error. Control trits use 0 for off and + for on; − is reserved unless stated. |
| Interrupts | A ternary interrupt controller with up to 24 sources. Sources 1 to 6 are assigned; 7 to 24 are for the platform. |
| Ternary dot product | The P extension defines TMAC.T: rd = rs3 + Σ rs1\[i\]·rs2\[i\] over the 24 trit lanes, with TDOT.T as its pseudo-instruction, TSUM.T for a trit sum and QNT.T to ternarize activations. |
| Opcode space | Extensions live in one opcode group. Three opcodes in it are unallocated and one is reserved for growth of the P extension. Allocation belongs to the maintainers. |
| R2R | RV32IToREBEL, a translator and simulator that turns RV32I assembly produced by GCC into REBEL-6 assembly. It is not a C compiler. |
| Wire-level encoding of trits | Not defined by the specification. The group's own tools write binary-coded ternary as BSD-PNX: 10 for +1, 11 for 0, 01 for −1, 00 illegal \[S13, S37\]. |

### 9.2 What changes in the draft

- Data paths are 24 trits, which is 48 wires at two bits per trit. The draft's 32-trit, 64-wire data buses are wrong.

- The "T-Bus" is not part of REBEL-6. An on-chip bus is your own design choice and should carry 24-trit addresses and data.

- The register addresses "@tryte 000001" to "000007" are not balanced-ternary numbers (the digits 2 to 7 do not exist) and ignore the device-slot layout. Fields are trits, not "bit 0, bit 1, bit 2".

- The four custom instructions are unnecessary for a first version and are not yours to allocate. TMAC.T already defines what the software sees.

- The claim of a 30 % saving in switching power against RV32I is not in the specification. The paper it is attributed to could not be read for this review.

### 9.3 Proposed device: TCIM0 (Proposal)

A memory-mapped device in slot 11, the first reserved slot. Agree the slot with the maintainers before publishing anything that depends on it. Offsets are in trytes from the slot base. Word registers sit at multiples of four trytes.

| **Offset** | **Register** | **Access** | **Function** |
|---|---|---|---|
| +0 | CTRL | RW, tryte | t0 EN. t1 IE: the interrupt line is high while DONE is set. t2 MODE: 0 digital, + analog. t3 GO: write + to start a product; reads as 0. |
| +1 | STAT | RO, tryte | t0 BUSY. t1 DONE, cleared by reading STAT or by the next command. t2 WERR: a program-and-verify step failed, the row index was outside 0 to 71, or a cell was read with both devices in LRS. t3 SAT: an analog result clipped. WERR and SAT describe the last command and are cleared when the next one starts. |
| +2 | TILE | RW, tryte | Tile select. Zero on a one-tile chip. |
| +4, +8, +12 | X0, X1, X2 | RW, word | Input vector of 72 trits. Row r is trit (r mod 24) of word (r div 24). |
| +16 to +39 | Y\[0\] to Y\[23\] | RO, tryte | Column results: −72 to +72 in digital mode, the converter count clipped to ±364 in analog mode. Valid while BUSY is 0. |
| +40 | PROW | RW, tryte | Row index for programming and read-back, 0 to 71. |
| +44 | PDATA | RW, word | The 24 weights of the selected row, one trit per column. |
| +48 | PCMD | W, tryte | \+ programs the row from PDATA with verify. − reads the row into PDATA in digital mode. |
| +49 | PITER | RO, tryte | Number of pulses used by the last program command. |

The device raises interrupt source 7, the first platform source.

> **Changed in revision 4.** The interrupt follows DONE alone. In revision 3 it also followed WERR, which reading STAT does not clear, so the interrupt of a failed command could not be acknowledged. WERR never occurs without DONE, so nothing is lost. A trit received with the unused wire code is read as 0. On the test chip's serial port, clocks beyond the 8 bytes of a frame are ignored, and the serial clock may be at most one eighth of the system clock.

This register map is implemented in RTL and verified (section 18.7). The proposal of section 8 to keep the pulse sequencer in the FPGA for first silicon still stands; the RTL contains the sequencer so that either choice can be made.

### 9.4 Reference model

For column j the device returns the sum over the 72 rows of weight times input:

> Y<sub>j</sub> = Σ W<sub>r,j</sub> · X<sub>r</sub> , summed over rows r = 0 … 71

In REBEL-6 software the same number is three TMAC.T instructions per column, 72 per tile. In digital mode the device must return exactly what those instructions return, and the test bench checks equality. In analog mode the comparison is statistical.

### 9.5 Software, encoding and the chip port

- **Software.** Version 1 needs no new opcode. Programs use the existing load and store instructions on the device registers and fall back to TMAC.T when the device is absent. An instruction-set extension can follow once the device is proven, with encoding space from the maintainers.

- **Encoding.** The REBEL-6 documents define no two-bit code for a trit. The REBEL group's tools use BSD-PNX (10 for +1, 11 for 0, 01 for −1, 00 illegal) \[S13, S37\]. The draft's code has the same pairs for +1 and −1 but 00 for 0. TCIM0 builds with BSD-PNX or with a two's-complement code, and both are verified (section 21.2). Ask the maintainers which code REBEL-6 hardware uses before the device is attached to it.

- **Chip port.** Do not bring a parallel bus to the pads. Expose the register map through a 4-wire serial port in binary, and let the FPGA that hosts the REBEL-6 core bridge its memory-mapped accesses to that port. The chip then needs about 25 pads: 7 digital, 8 supply and about 10 analog.

- **Workload.** BitNet b1.58 has ternary weights and 8-bit activations \[S25\]. A device with ternary inputs runs it by splitting each activation into balanced-ternary digits and evaluating one digit plane at a time. The REBEL-6 documents describe the all-ternary kernel through TMAC.T and leave the 8-bit-activation path reserved \[S13\]. Start with a network whose activations are ternary.

## 10 Design flow

The open-source flow in the draft is close to workable for the CMOS part of the chip. The table lists what to change. Everything in the right-hand column was checked in the repository or document named.

| **Step** | **Draft** | **Use instead** |
|---|---|---|
| **Environment** | PDK installed with ciel and open_pdks. | The IIC-OSIC-TOOLS container, run with Docker and WSL2 on Windows. The image is about 4 GB and needs 20 GB of disk. It ships ihp-sg13g2 with Xschem, ngspice, OpenVAF-Reloaded, VACASK, Xyce, KLayout with KLayout-PEX, Magic, Netgen, LibreLane, OpenROAD, Yosys with the slang plug-in, Verilator and cocotb \[S17\]. ciel can also install ihp-sg13g2, identified by IHP-Open-PDK commit; open_pdks is its route for sky130 and gf180mcu only \[S18\]. |
| **Schematics** | Xschem. | Xschem. Correct. |
| **Analog simulation** | Verilog-A compiled by OpenVAF into ".so" libraries for ngspice and Xyce. | OpenVAF-Reloaded writes OSDI files for ngspice and VACASK. Xyce needs plug-ins built with ADMS \[S16, S1\]. |
| **Transistor models** | Foundry BSIM4 models. | PSP 103 \[S1\]. |
| **Supply domains** | 1.8 V wordline drivers; rails of 1.2, 1.8 and 3.3 V. | 1.2 V core transistors with a 1.65 V gate limit, and 3.3 V thick-oxide transistors. The I/O cells are 3.3 V with a 1.2 V core side. SG13G2 has no 1.8 V device class \[S2, S1\]. |
| **Mixed-signal simulation** | Xyce and ngspice co-simulation. | ngspice with digital co-simulation. The container includes spicebind, which couples ngspice to an HDL simulator, and cocotb \[S17\]. |
| **Synthesis** | Yosys from SystemVerilog. | Yosys with the slang plug-in for SystemVerilog \[S17\]. |
| **Place and route** | OpenLane and OpenROAD. | LibreLane, the successor of OpenLane, for which the PDK carries a configuration, or OpenROAD flow scripts. Standard cells are characterized at 1.2 V and 1.5 V \[S1, S17\]. |
| **Analog layout** | KLayout and Magic. | KLayout is the reference tool. Magic and Netgen support for SG13G2 is a beta pre-release that needs Magic 8.3.573 or later \[S1\]. |
| **DRC** | KLayout foundry deck, including "MemCell" constraints. | The KLayout decks in the PDK. They define the HafniumOx layer and apply only generic grid and angle checks to it. There are no ReRAM rules \[S1\]. |
| **LVS** | Netgen. | KLayout LVS from the PDK, which extracts no ReRAM device. A Netgen setup exists as part of the beta support \[S1\]. |
| **Parasitic extraction** | Magic. | KLayout-PEX, or Magic within its beta support \[S17, S1\]. |
| **ReRAM layout rules** | A "MemCell" layer between Metal1 and Metal2, 120 nm Metal1 enclosure, 150 nm via spacing. | No such layer or rule exists in the open PDK. Its layer table names HafniumOx (143/0) and gives no rules. The real rules come with the MEMRES kit \[S2\]. |
| **Metal stack** | Thick Metal4 and Metal5 for supply trunks. | Metal1 is 0.42 µm thick and Metal2 to Metal5 are 0.49 µm. The thick layers are TopMetal1 (2 µm) and TopMetal2 (3 µm) \[S2\]. |
| **Tape-out** | An open IHP shuttle or a CEA-Leti consortium run. | See section 3. The open-source runs have no ReRAM, and they are no longer free. |

## 11 Test hardware and characterization

| **Item** | **Draft** | **Corrected** |
|---|---|---|
| **Package** | QFN-64 in a zero-insertion-force socket. | About 25 pads, so a 28- or 32-lead package or chip-on-board. IHP delivers diced samples, so packaging has to be arranged separately. |
| **Host** | Kria KV260 driving a 32-trit bus over ribbon cables. | Any FPGA board with eight free 3.3 V pins, for the serial port. The KV260 has one 12-pin Pmod and no general expansion header \[S24\]. |
| **Regulators** | TPS7A4700 for 1.2, 1.8 and 3.3 V. | The TPS7A4700 output range is 1.4 to 20.5 V from an input of 3 V or more. It suits the 3.3 V rail and cannot make 1.2 V. Choose a low-noise regulator whose range includes 1.2 V. No 1.8 V rail is needed \[S23\]. |
| **Noise target** | Ripple below 4 µV RMS on every rail. | 4 µV RMS is the regulator's own output noise from 10 Hz to 100 kHz, not a board-level result \[S23\]. Specify what the circuit needs instead: the stability of the 0.2 V clamp and of the reference current. One percent of an LRS3 result step is 0.4 µA. |
| **Current scale** | Picoampere bitline sensing. | 3 to 44 µA per cell and up to about 3 mA per bitline \[S8\]. |
| **Analog access** | Bitlines through unity-gain buffers to SMA connectors for a parameter analyzer. | A buffer passes voltage and blocks the current the analyzer has to measure. Bring selected bitline and source-line nodes to pads through an on-chip analog multiplexer, with separate force and sense connections. |
| **Pulses** | 25 ns pulses, with source-measure units named as the instrument. | Source-measure units cover DC and slow pulses. Microsecond and faster pulses need the pulse module of the analyzer, or the chip's own drivers. |
| **First tests** | Boundary-scan tests. | No scan chain is defined. Proceed in this order: supplies, serial register loop-back, digital-mode read of unformed cells, forming of a few cells from the analyzer, forming on chip, set and reset, level distributions, analog mode. |
| **Forming** | Compliance of 20 µA. | No source. The published recipe uses a 1.5 V gate and stops when the read current reaches 42 µA \[S8\]. |
| **Endurance** | 10<sup>7</sup> cycles with 25 ns pulses. | Run it as a test to failure. The published multi-level demonstration is 1,000 cycles \[S8, S10\]. |
| **Retention** | 500 hours at 85 °C and 125 °C; differential rejection cancels the drift. | Keep the test. The published claim is ten years below 100 °C by extrapolation, so 125 °C lies outside it. Drift depends on the level, so it does not cancel between an LRS device and an HRS device \[S10\]. Also record relaxation from one second to one day after programming. |
| **Accuracy** | Comparison with a bit-exact software model. | Exact for digital mode. Statistical, against a noise-aware model, for analog mode. |

## 12 Game plan

Eight phases with three decision gates. Phases 0 to 4 need only your PC. The exit criteria are proposals; tighten them as data arrives.

> **Order of work, decided on 6 October 2026.** Tape-out is not considered until the design is complete and verified. Phases 5 to 8 stay in the plan unchanged and are not started. Table 12.2 shows where Phases 0 to 4 stand after the simulation work of revision 3 and the audit of revision 4.

| **Phase** | **Work** | **Exit criterion** |
|---|---|---|
| **0. Tool chain** | Install the IIC-OSIC-TOOLS container. Clone IHP-Open-PDK, ternary-workbench, RV32IToREBEL and the SKY130 ReRAM library. Create one project repository and record every tool version. | ngspice runs a PDK test bench with the PSP models. The REBEL-6 assembler builds. The R2R simulator runs a compiled C program. |
| **1. Device model** | Compile the open Stanford model with openvaf-r, rewriting the state equations if needed. Create the IHP parameter set with its gate-voltage extension. Build a one-transistor test bench with the 3.3 V NMOS. Add device-to-device spread. | The published levels are reproduced within ±15 %: 16, 11 and 8 kΩ and 170 kΩ quasi-static, and the read currents of Table 4.1. A 1,000-run Monte Carlo of the 2T2R cell converges every time. |
| **2. Array model and architecture** | In Python, model the 72 × 24 tile: sampled devices, bitline and source-line resistance, clamp error, quantization, two-phase inputs and digital-mode read errors. Compare with the exact dot product. Measure the accuracy of a small ternary network against device spread. Synthesize a digital 24-lane TMAC.T datapath in IHP standard cells as an area and energy baseline. | **Gate G1.** A written specification: rows per read, LRS level, bitline metal, converter resolution and error budget. Analog mode stays in the plan only if it beats the digital baseline in energy per operation, latency or area. |
| **3. Circuits** | Design in Xschem and ngspice: cell and drivers, bitline clamp, digital-mode comparator, analog converter, programming driver, level shifters and analog test multiplexer. Simulate process corners, −40 to 125 °C, and mismatch. | Every block meets the Phase 2 specification across corners. A full-tile transient reproduces the Phase 2 error budget. |
| **4. Digital and REBEL-6** | Write the TCIM0 register block, sequencers, accumulators and serial port. Verify with cocotb or Verilator against the Python model. Attach a device model to the R2R simulator, or to a REBEL-6 core that follows the published specification. Run on an FPGA with a behavioral array. | One C program gives identical results with software TMAC.T and with the digital-mode device. |
| **5. CMOS-only test chip** | Lay out the periphery with a switched resistor array standing in for ReRAM. Sign off with KLayout DRC and LVS and extract parasitics. Submit to one of IHP's open-silicon runs or to Tiny Tapeout (section 3). | **Gate G2.** Measured converter linearity and noise agree with simulation. The open flow has produced working silicon. |
| **6. ReRAM tape-out** | **Gate G3:** choose the route from the written answers and quotes. Obtain the kit. Port the cell to the foundry's ReRAM cell. Tape out one tile, an 8 × 8 array and single cells with direct pad access, on about 25 pads. | Clean sign-off in the foundry's flow. Design submitted. |
| **7. Bring-up** | Follow the test order of section 11. | Level distributions, relaxation, endurance, retention and both read modes measured and compared with the models. |
| **8. System demonstration** | Run REBEL-6 on the FPGA with the chip as TCIM0. Measure accuracy, latency and energy against the digital baseline. Publish the design and the data. | A result that others can reproduce. |

**Table 12.2 Status of Phases 0 to 4 after revision 4**

| **Phase** | **Done in simulation** | **Still open** |
|---|---|---|
| **0. Tool chain** | Gnucap with the PDK's PSP 103 models, ngspice 46 and Yosys built from source. The PDK's 26 MOS reference tests give identical output, and 16 current sweeps agree with the PDK's ngspice reference data within 0.1 %. | The container flow on your PC (Xschem, KLayout, OpenVAF, LibreLane, Verilator). The R2R simulator and the REBEL-6 assembler were not built. |
| **1. Device model** | Verilog-A model with the state on a node, compiled and cross-checked in three solvers. Kinetics re-fitted. One-transistor test bench with the real 3.3 V NMOS. | The exit criterion is not met as written: at the published gap values the model is within ±15 % for LRS2 and LRS3, at −16 % for LRS1 and at +90 % for HRS (Table 18.2). No device-to-device spread inside the compact model yet; the tile model samples the published distributions instead. No forming, retention or temperature. |
| **2. Array and architecture** | Tile model with wiring, clamp, both read modes, a ternary network, energy and time. Digital baseline synthesized. Provisional Gate G1 decision: digital mode is the product (section 18.8). | G1 becomes final when the circuits of Phase 3 confirm the energy and time figures. |
| **3. Circuits** | Cell and select transistor sized. First-cut sense amplifier across five corners with mismatch. | Everything else: drivers, level shifters, references, analog-mode clamp and converter, test multiplexer, temperature, layout parasitics. |
| **4. Digital and REBEL-6** | TCIM0 RTL with serial port, self-checking test bench (81,966 checks, no failure; 69 of 69 injected faults detected), synthesis, gate-level check. | Clock gating and speed-up. A second simulator, lint, formal proofs of the sequencers. Place and route, and timing after it (timing before layout and two equivalence proofs are done, section 21). Connection to REBEL-6 RTL or the R2R simulator. FPGA run. |

#### Workstreams

The draft divided the work among seven agent roles. The division is kept, with corrected scopes: the device stream no longer defines a material stack, and the foundry stream handles access, not process recipes.

| **Workstream** | **Owns** | **Hands over** |
|---|---|---|
| **Device and model** | Published device data, the Verilog-A model, parameter sets and the variability model. | A compiled model and its statistics, to the array and circuit streams. |
| **Array architecture** | The Python tile model, the error budget and the Gate G1 specification. | The specification, to the circuit and digital streams. |
| **Analog circuits** | Cell, drivers, clamp, comparator, converter and programming driver. | Schematics and corner results, then layout. |
| **Digital and REBEL-6** | TCIM0 RTL, serial port, test benches, reference model and software. | RTL and the reference model. |
| **Physical design** | Layout, DRC, LVS, extraction and chip assembly. | The layout database for tape-out. |
| **Foundry liaison** | The questions of section 13, kit access, run dates and quotes. | The route decision at Gate G3. |
| **Bring-up** | Test board, scripts and measurements. | Measured data, back to the device and array models. |

#### Cost

Phases 0 to 4 have no fabrication cost. Phase 5 costs about €2,800 per mm<sup>2</sup> on an IHP open-source SG13G2 run, less on SG13CMOS5L, or a few hundred euros on Tiny Tapeout if a template with a 3.3 V supply exists there. Phase 6 costs €8,820 to €14,350 at IHP list price for 0.8 to 1.5 mm<sup>2</sup>, plus packaging, a test board and access to a parameter analyzer with a pulse module.

#### Next

The ordered list of next tasks is in section 19.3. The questions of section 13 cost nothing to send and their answers take time, so send the technical ones (device data, voltages, kit) now even though tape-out is parked: the design needs those answers.

## 13 Questions to send before spending money

#### To IHP

- IHP states that MEMRES comes with a design kit that includes layout and a Verilog-A simulation model. How is the kit obtained, under which agreement, and which tools does it support? Can a design made with the open PDK and KLayout include the MEMRES cell and be signed off?

- What are the stack, the cell dimensions and pitch, and the metal levels of the current module?

- Which forming, set and reset voltages does IHP recommend in SG13G2, and which transistor types may carry them?

- What is the kit's Verilog-A model calibrated to, and are measured statistics for the SG13G2 module available: level distributions, relaxation, read disturb, temperature?

- Who may order? Can an individual or a small company order directly, and under which agreements?

- What are the confirmed 2027 tape-in and delivery dates, the minimum area and the packaging options?

- What is the minimum area on the open-silicon runs, and is there an SG13G2 open-source run between 29 September 2026 and 4 October 2027?

#### To the REBEL-6 maintainers at USN

- May an experimental device use memory-mapped slot 11 and interrupt source 7?

- Is there a reference RTL implementation, and does it use the BSD-PNX code of the group's tools (10 for +1, 11 for 0, 01 for −1) on wires?

- Would they reserve encoding space for an accelerator extension once the device works?

#### To ChipFoundry

- What are the price, user area, part count and dates of the next shuttle that includes ReRAM? Are the open sky130_fd_pr_reram cells and rules the sign-off set?

Europractice member prices are open to academic institutions and publicly funded research laboratories \[S22\]. A university partner could therefore order route A at the lower rate.

## 14 Claim-by-claim ledger

The draft's technical claims, in the draft's order. Tool-flow and laboratory items are also covered in sections 10 and 11. "Unsupported" means that no source was given or that the cited source does not contain the claim. "Not verifiable" means the source could not be opened.

| **Draft claim** | **Verdict** | **Evidence** |
|---|---|---|
| **Orchestration framework** |  |  |
| The method is built on the open-source m1frame role-based framework. | **Correct** | The repository exists and describes itself as a portable multi-agent AI framework \[S29\]. It organizes work and is not a technical dependency. |
| A foundry agent covers IHP SG13G2 and shuttle runs at CEA-Leti and Fraunhofer EMFT. | **Partly correct** | Leti announced an OxRAM shuttle with CMP in 2018 \[S21\]; its present availability was not verified. No EMFT ReRAM shuttle was found. |
| A 400 °C anneal limit makes the device agent change the titanium thickness, which makes the circuit agent resize the compliance transistor. | **Not applicable** | A shuttle customer cannot change layer thicknesses. No 400 °C figure was found in IHP's public documents. |
| **Process and material stack** |  |  |
| The IHP SG13G2 open PDK supports HfO<sub>2</sub> ReRAM cells between Metal1 and Metal2. | **Wrong** | No ReRAM device, model or rule in the open PDK \[S1, S2\]. ReRAM is the paid MEMRES module \[S3, S4\]. IHP places the cell between Metal2 and Metal3 \[S5\]. The reference cited for this claim is a ResearchGate listing of fault-tolerance papers. |
| CEA-Leti and Fraunhofer EMFT provide mature TiN/HfO<sub>2</sub>/Ti/TiN modules with characterized multi-level storage (ref. 10). | **Unsupported** | Ref. 10 is a single-author simulation proposal with no fabricated devices and no foundry \[S27\]. |
| Intermediate states in single-layer devices drift through runaway electro-thermal feedback, so a bilayer is required. | **Partly correct** | Thermal feedback during set is real and is why the current is limited. IHP nevertheless shows four separated levels in a single Al-doped HfO<sub>2</sub> layer with a verify algorithm \[S8\]. IHP's 2021 announcement mentions HfO<sub>2</sub> and Al<sub>2</sub>O<sub>3</sub> layers used in combination for analog switching \[S5\], so the foundry module may itself be a two-layer stack; no details are public. |
| Stack of TiN 80 nm / HfO<sub>2</sub> 6.5 nm / AlOy 1.2 nm / Ti 7.0 nm / TiN 50 nm; TEMAH and water at 275 °C; TMA and water at 300 °C. | **Unsupported** | None of these values is in the cited references. The published IHP stack is TiN 150 / Ti 7 / Al:HfO<sub>2</sub> 6 / TiN 150 nm \[S8, S9, S10\]. Only the 7 nm of titanium agrees. |
| Aluminum binds oxygen more strongly than hafnium, as the enthalpies −1675.7 and −1144.7 kJ/mol show. | **Wrong** | The values are standard; the comparison must be per oxygen atom, where HfO<sub>2</sub> (−572) is more stable than Al<sub>2</sub>O<sub>3</sub> (−559). See section 4. |
| The titanium layer removes the need for electroforming. | **Wrong** | IHP forms with sweeps from 2.5 to 5.0 V \[S8\]; SKY130 ReRAM forms at 2.2 to 3.1 V \[S15\]. The draft itself forms its cells during bring-up. |
| The TiN bottom electrode blocks metal cation migration. | **Not applicable** | HfO<sub>2</sub> cells of this type switch by oxygen vacancies, not by metal cations. |
| A 15 µA compliance gives the intermediate state, which conducts by trap-assisted and direct tunneling and is stable over extended cycling. | **Unsupported** | No source for 15 µA or for the cycling claim. The Stanford model does describe conduction through the gap as tunneling. IHP's lowest LRS target is a 16 µA read current, which is a different quantity \[S8\]. |
| **Compact model** |  |  |
| Current: I = I<sub>0</sub> exp(−g/g<sub>0</sub>) sinh(qV/αkT). | **Wrong** | The published form is sinh(V/V<sub>0</sub>) with a fitted V<sub>0</sub> \[S9, S15\]. |
| Gap equation with v<sub>0</sub> as an ionic jump-attempt frequency and an added noise term. | **Partly correct** | It is the simplified Stanford form. v<sub>0</sub> is a velocity. The gap dependence of γ is omitted. |
| Temperature: C dT/dt = \|IV\| − (T − T<sub>ambient</sub>)/R. | **Correct** | Standard form \[S15, S26\]. |
| Parameters were extracted from IHP SG13G2 test vehicles by a genetic algorithm. | **Wrong** | No measurement exists. See Table 5.1 for each value. |
| OpenVAF compiles the model into C shared libraries for ngspice and Xyce. | **Partly correct** | It produces OSDI libraries for ngspice. Xyce uses ADMS plug-ins. The maintained compiler is OpenVAF-Reloaded \[S16, S1\]. |
| Levels must satisfy μ(k+1) − μ(k) ≥ 3 (σ(k+1) + σ(k)). | **Correct** | A valid criterion, and a weak one: at exactly 3σ, 0.135 % of cells cross each boundary from each side, which is 5.5 cells in 4,096. Published IHP levels reach 3.6 to 4.0. |
| Open-loop programming gives σ/μ above 0.40. | **Unsupported** | The reference is a presentation uploaded to Scribd. |
| The gate voltage sets the current limit through I = ½ μ C (W/L)(V<sub>G</sub> − V<sub>th</sub>)<sup>2</sup>. | **Partly correct** | Gate-voltage control of the level is right and is what IHP does \[S8\]. The long-channel formula ignores the voltage across the ReRAM in series; use the PSP model. |
| **2T2R cell** |  |  |
| +1 = (LRS, HRS), 0 = (HRS, HRS), −1 = (HRS, LRS). | **Correct** | Matches ref. 2 \[S11\]. It also shows that no intermediate state is needed. |
| I<sub>diff</sub> = V<sub>read</sub> (G+ − G−). | **Correct** | For an ideal clamp. |
| Common-mode rejection above 38 dB from −40 to 125 °C (ref. 2). | **Unsupported** | Ref. 2 gives no such figure and simulates corners at 0, 27 and 60 °C \[S11\]. |
| The zero state needs no reference and holds the differential current at zero. | **Partly correct** | The mean is zero. The pair has a standard deviation of 2.6 µA with published statistics, and ref. 2 reports 6.5 % and 18.5 % zero-state errors \[S8, S11\]. |
| The (HRS, HRS) state minimizes static current. | **Partly correct** | It is the lowest-current state, but an HRS cell conducts about 2.85 µA at 0.2 V. An all-zero column of 72 rows draws about 410 µA across the pair. |
| Sneak paths are completely suppressed; off resistance exceeds 10<sup>11</sup> Ω. | **Partly correct** | True of any one-transistor cell and not specific to 2T2R. Leakage is small, not zero. The figure holds for thick-oxide transistors at 27 °C; a 1 µm wide thin-oxide transistor gives about 10<sup>10</sup> Ω \[S2\]. |
| Differential sensing raises the signal-to-noise ratio by more than a factor of two. | **Partly correct** | The signal doubles against a mid-point reference. The spread of two devices adds, so the gain is about √2 when device spread dominates. |
| Voltage drops are balanced and cancel on the two bitlines. | **Wrong** | The two bitlines carry different, data-dependent currents. |
| **Parasitics and sizing** |  |  |
| Sheet resistance of about 0.12 Ω/sq for lower metals. | **Partly correct** | Metal1 is 0.110 Ω/sq (0.085 to 0.135). Metal2 to Metal5 are 0.088 Ω/sq \[S2\]. |
| Up to 35 % compression of output currents in large arrays (ref. 3). | **Not verifiable** | Ref. 3 is a real paper on voltage-drop-immune binarized networks; the page could not be opened. The calculation here gives a 2 to 27 % loss of summed current for a 64-row line on Metal2–5, for widths from 1.0 down to 0.2 µm. |
| Twice-minimum-width bitlines and Metal3 ground straps keep the drop below 2.1 % of the read voltage. | **Wrong** | 8 to 24 % at the far end of a 64-row line under the same assumptions. See Table 6.2. |
| A 64 × 64 tile is 32 ternary columns by 64 rows. | **Correct** | Arithmetic is right. The size does not match REBEL-6's 24-trit word. |
| **Readout** |  |  |
| Compute-in-memory arrays typically use flash converters with 2<sup>N</sup> − 1 comparators that take up to 70 % of macro area (ref. 4). | **Unsupported** | The comparator count is right. Ref. 4 says converters limit efficiency; the 70 % figure was not found in it \[S31\]. |
| t = C V<sub>ref</sub> / I<sub>diff</sub>, captured by a 6-bit Gray counter at 1 GHz. | **Wrong** | The formula is right; the converter cannot represent the result range. See section 7.1. |
| Readout table: 1450 against 320 µm<sup>2</sup> and 1.8 mW against 45 µW per column. | **Unsupported** | No source and no design. |
| A 0.2 V read clamp avoids read disturb. | **Correct** | IHP reads at 0.2 V \[S8\]. |
| Integration capacitor of 50 to 200 fF. | **Wrong** | Inconsistent with the 1 GHz counter and the cell currents. See section 7.1. |
| **Write and verify** |  |  |
| Programming with 1.6 V, 25 ns pulses, 25 mV gate steps and at most 16 attempts (ref. 13). | **Unsupported** | Ref. 13 is a 22 nm FinFET macro. IHP steps the pulse amplitude by 0.1 V at a fixed gate voltage, with 1 µs pulses \[S8\]. |
| Open-loop single-pulse programming is not viable for multi-level cells. | **Correct** | All the published multi-level work uses verify loops \[S8, S10, S12\]. |
| **REBEL-6 interface** |  |  |
| REBEL-6 was developed at the University of South-Eastern Norway. | **Correct** | \[S13, S28\] |
| REBEL-6 operates on 32-trit words. | **Wrong** | Instructions are 32 trits. Registers and data words are 24 trits \[S13\]. |
| Memory is addressed in 6-trit trytes. | **Correct** | For the data space \[S13\]. |
| 729 general-purpose registers, addressed by a 6-trit field. | **Partly correct** | 729 registers with 6-trit fields; X0 is zero and the negative range holds system and streaming state \[S13\]. |
| Dual-rail trit code 10 / 00 / 01 with 11 as a trap (ref. 1). | **Unsupported** | The specification defines no wire encoding. The REBEL group's tools use BSD-PNX, which has the same pairs for +1 and −1 but 11 for 0 and 00 as the illegal pair \[S13, S37\]. |
| A tryte spans −364 to +364, 729 states, on 12 wires. | **Correct** | Arithmetic is right. |
| A 32-trit word maps onto 64 wires. | **Wrong** | The data word is 24 trits, 48 wires. |
| The T-Bus is a balanced-ternary extension of Wishbone B4 (ref. 1). | **Unsupported** | Not in the REBEL-6 documents. It is the draft's invention. |
| Registers at tryte addresses 000001 to 000007 with bit flags, in the upper I/O segment. | **Wrong** | Digits 2 to 7 are not balanced-ternary digits. Memory-mapped I/O is the − region with 6,561-tryte device slots, and fields are trits \[S13\]. |
| Four custom instructions in unallocated opcode fields. | **Unsupported** | Reserved opcodes exist, but allocation belongs to the maintainers, and TMAC.T already defines the operation \[S13\]. |
| C code is generated by the USN R2R compiler pipeline. | **Partly correct** | R2R translates RV32I assembly from GCC into REBEL-6 assembly and simulates it \[S14\]. |
| A projected saving of more than 30 % in dynamic switching power against RV32I (ref. 1). | **Not verifiable** | Not in the specification. The paper's text could not be opened. |
| **Design flow** |  |  |
| Schematics in Xschem. | **Correct** | \[S1, S17\] |
| Foundry BSIM4 NMOS models. | **Wrong** | PSP 103 \[S1\]. |
| 1.8 V wordline drivers. | **Wrong** | SG13G2 has 1.2 V and 3.3 V transistors \[S2\]. |
| Digital blocks through OpenLane and OpenROAD with IHP standard cells. | **Partly correct** | LibreLane is the maintained successor and the PDK configures it \[S1, S17\]. |
| A MemCell layer with 120 nm Metal1 enclosure and 150 nm via spacing. | **Wrong** | Not in the open PDK \[S2\]. |
| LVS in Netgen; extraction in Magic. | **Partly correct** | Possible within beta support. KLayout LVS is the PDK's reference \[S1\]. |
| Peak current 32 × 50 µA = 1.6 mA. | **Correct** | Arithmetic is right. |
| Electromigration limit of about 1.5 × 10<sup>5</sup> A/cm<sup>2</sup>. | **Wrong** | The specification gives 1 mA per µm for Metal1, which is 2.4 × 10<sup>5</sup> A/cm<sup>2</sup> \[S2\]. |
| Supply lines on thick Metal4 and Metal5; Metal1 bitlines widened to 0.48 µm. | **Wrong** | Metal4 and Metal5 are thin. A 0.48 µm Metal1 line carries 0.48 mA, and a single bitline needs no widening for 50 µA \[S2\]. |
| PDK set up with ciel and open_pdks. | **Partly correct** | ciel installs ihp-sg13g2 directly from IHP-Open-PDK commits \[S18\]. |
| Submit to an open IHP shuttle or a CEA-Leti consortium run. | **Wrong** | The open-source runs have no ReRAM \[S7, S36\]. |
| **Laboratory** |  |  |
| QFN-64 package with a 32-trit T-Bus to the FPGA. | **Wrong** | The bus has 152 wires. Sixty-four pads need a 2.69 mm<sup>2</sup> die. |
| TPS7A4700 regulators for 1.2, 1.8 and 3.3 V with ripple below 4 µV RMS. | **Wrong** | Minimum output 1.4 V. The 4 µV RMS figure is the device's intrinsic noise \[S23\]. |
| Picoampere bitline sensing. | **Wrong** | Microamperes to milliamperes \[S8\]. |
| Unity-gain buffers between bitlines and the parameter analyzer. | **Wrong** | A buffer blocks the current to be measured. |
| Kria KV260 as the host. | **Wrong** | One 12-pin Pmod \[S24\]. |
| Forming with a 20 µA compliance. | **Unsupported** | No source. The published recipe stops when the read current reaches 42 µA \[S8\]. |
| 10<sup>7</sup> write cycles with 25 ns pulses. | **Unsupported** | Published multi-level endurance is 1,000 cycles with 1 µs pulses \[S8, S10\]. |
| 1,024 cells split 341 / 342 / 341. | **Correct** | Arithmetic is right. |
| Retention at 85 and 125 °C for 500 hours, with drift canceled differentially. | **Partly correct** | A reasonable test. The cancellation claim is wrong because drift depends on the level \[S10\]. |
| BitNet b1.58 weights as the test kernel (ref. 30). | **Partly correct** | The weights are ternary and the activations are 8-bit \[S25\]. Ref. 30 is the REBEL-6 paper, not BitNet. |
| Results compared with a bit-exact software model. | **Partly correct** | Right for a digital read. Not achievable for an analog sum. |
| **Conclusions of the draft** |  |  |
| More than 75 % less peripheral area and more than ten times less static power. | **Unsupported** | Derived from the unsourced readout table. |
| "A verified path toward fabricating operational balanced ternary accelerators." | **Wrong** | The path as written could not be ordered or built. |

## 15 Audit of the draft's references

Thirty-one entries. "Opened" means the content was read for this review.

| **\#** | **As cited** | **Finding** |
|---|---|---|
| 1 | REBEL-6 paper, ResearchGate | Real: IEEE ISMVL 2025 \[S28\]. Text not opened. Cited for claims it cannot contain, such as the T-Bus and OpenLane. |
| 2 | Laborieux et al., ternary weights with resistive RAM, arXiv 2007.14234 | Opened. Supports the cell encoding. Contradicts the analog-summation and rejection claims \[S11\]. |
| 3 | Binarized networks immune to device variation and voltage drop, PMC11189464 | Real (Communications Engineering, 2024). Not opened. |
| 4 | RAELLA, arXiv 2304.07935 | Abstract opened. General statement on converter cost only \[S31\]. |
| 5 | GitHub profile ofFBeaT9 | A profile page. The m1frame repository exists \[S29\]. |
| 6 | Reddit post on a ternary FPGA processor | Not a technical source. |
| 7 | ResearchGate topic page, "Review articles in fault tolerance" | An unrelated listing. It is the cited source for the IHP ReRAM claims. |
| 8 | Open Circuit Design analog flow page | A general flow description. Not opened. It cannot be the source of IHP-specific rules that are absent from the IHP PDK. |
| 9 | Resistive switching devices review, PMC10976006 | Not opened. |
| 10 | Multi-level resistive synapses, arXiv 2606.22621 | Opened. A single-author simulation proposal with no devices and no foundry \[S27\]. Cited for the stack, the process temperatures and the foundry modules. |
| 11 | Stanford-PKU model with extended multilevel capability, ResearchGate | Real. Not opened. |
| 12 | Pérez-Bosch Quesada et al., compact modeling of multilevel 1T-1R devices | Opened. The real source of fitted parameters, misquoted by the draft \[S9\]. |
| 13 | 22 nm FinFET embedded ReRAM macro, ISSCC 2019 | Real by its title. A different technology. Not opened. |
| 14 | Spiking-network SoC with charge-injector synapses | Not opened. Unrelated to ReRAM column readout by its title. |
| 15 | Magic how-to | Tool documentation. |
| 16 | Frontiers in Neuroscience paper on binarized networks with differential HfO<sub>2</sub> memory arrays | Relevant by its title. Not opened. |
| 17 | REBEL-6 paper, IEEE Computer Society | Same paper as 1. |
| 18 | IHP TO_Sep2025 repository | Real. An open shuttle on SG13CMOS in September 2025, without ReRAM \[S7\]. |
| 19 | Scribd upload on ReRAM variability | Not a citable source. |
| 20 | Stochastic behaviors in cross-point arrays, arXiv 1606.07457 | Not opened. |
| 21 | Europractice schedules 2026 | Opened. Confirms SG13G2 and MEMRES prices \[S4\]. |
| 22 | open_pdks mirror | Real. Not the route ciel uses for IHP \[S18\]. |
| 23 | IRDS 2022, Beyond CMOS | Not opened. |
| 24 | Analog architectures for neural-network acceleration, Applied Physics Reviews | Not opened. |
| 25 | Thesis on ferroelectric memristors, Lund | Off topic: ferroelectric devices, not filamentary HfO<sub>2</sub> ReRAM. |
| 26 | Roldán et al., thermal models for RRAM | Opened. Gives ranges for thermal resistance and capacitance; the draft's values are not in it \[S26\]. |
| 27 | Survey of near-data processing architectures | Not opened. |
| 28 | Google Scholar profile | A profile page. |
| 29 | aiunderstand/ternary-workbench | Opened. Contains the REBEL-6 specification. The draft lists it and does not use it \[S13\]. |
| 30 | REBEL-6 paper, Semantic Scholar | Same paper as 1. Used as the BitNet citation. |
| 31 | LayoutEditor PDK installer | Not opened. Unrelated tool. |

## 16 What was not verified

- **Silicon behavior.** The simulations of section 18 use a device model fitted to published data from IHP's 0.25 µm arrays. The SG13G2 MEMRES devices may differ. Read disturb, relaxation, forming, retention and temperature behavior are not covered by the model.

- **Most circuits.** Only the cell and a first read circuit were simulated. Drivers, references, level shifters and the analog-mode converter do not exist yet.

- **Energy figures.** The digital figures come from a zero-delay toggle count without clock tree or wiring and are likely low by a factor of 1.5 to 3.

- **The REBEL-6 paper.** Its text could not be opened. REBEL-6 facts come from the maintainers' specification repository, which is more recent than the paper.

- **The MEMRES module in SG13G2.** Its kit, cell size, voltages, tool support and metal position were not available. The Metal2–Metal3 position comes from a 2021 statement about SG13S.

- **Dates and prices.** Read again from the text of the IHP and Europractice pages on 6 October 2026 (section 20). They change; confirm before committing.

- **Device statistics.** The values in Table 4.1 were read twice from the paper's PDF with the same result. They describe 0.25 µm arrays directly after programming.

- **Cell pitch.** The 2 to 3 µm pitch behind Table 6.2 is an assumption.

- **ChipFoundry's ReRAM terms and Leti's current offer.** Each needs a direct answer from the provider.

- **References marked "not opened"** in section 15.

- **Handbook enthalpies.** The values in section 4 are standard handbook values and were not re-fetched from a database.

## 17 Sources

**S1** IHP-Open-PDK repository, main branch at commit 5e6d592 (1 Sep 2026) and dev branch at e8fba18 (6 Oct 2026). <https://github.com/IHP-GmbH/IHP-Open-PDK>

**S2** SG13G2 Process Specification Rev. 1.2 and SG13G2 Layout Rules, in S1 under ihp-sg13g2/libs.doc/doc. <https://github.com/IHP-GmbH/IHP-Open-PDK/tree/main/ihp-sg13g2/libs.doc/doc>

**S3** IHP, MPW schedule and price list. <https://www.ihp-microelectronics.com/services/research-and-prototyping-service/mpw-prototyping-service/schedule-price-list>

**S4** Europractice, schedules and prices 2026. <https://europractice-ic.com/schedules-prices-2026/>

**S5** IHP news, 8 June 2021, access to memristive technology. <https://www.ihp-microelectronics.com/news/detail/ihp-offers-access-to-memristive-technology-for-edge-ai-computing-or-hardware-artificial-neural-networks-applications>

**S6** IHP, SiGe:C BiCMOS technologies and modules. <https://www.ihp-microelectronics.com/services/research-and-prototyping-service/mpw-prototyping-service/sigec-bicmos-technologies>

**S7** IHP-Open-DesignLib, renamed IHP-Open-FMD_QNC-Tapeouts in June 2026: the free runs of 2023 to 2025, funded by the FMD-QNC project. <https://github.com/IHP-GmbH/IHP-Open-DesignLib>

**S8** E. Pérez et al., "Optimization of Multi-Level Operation in RRAM Arrays for In-Memory Computing", Electronics 10, 1084 (2021). <https://doi.org/10.3390/electronics10091084>

**S9** E. Pérez-Bosch Quesada et al., "Toward Reliable Compact Modeling of Multilevel 1T-1R RRAM Devices for Neuromorphic Systems", Electronics 10, 645 (2021). <https://doi.org/10.3390/electronics10060645>

**S10** E. Pérez et al., "Toward Reliable Multi-Level Operation in RRAM Arrays: Improving Post-Algorithm Stability and Assessing Endurance/Data Retention", IEEE Journal of the Electron Devices Society (2019). <https://iris.unife.it/retrieve/e309ade2-48bf-3969-e053-3a05fe0a2c94/JEDS.pdf>

**S11** A. Laborieux et al., "Implementation of Ternary Weights with Resistive RAM Using a Single Sense Operation per Synapse". <https://arxiv.org/abs/2007.14234>

**S12** W. Wan et al., "A compute-in-memory chip based on resistive random-access memory", Nature (2022). <https://pmc.ncbi.nlm.nih.gov/articles/PMC9385482>

**S13** REBEL-6 ISA, platform and extension specifications, ternary-workbench repository at commit 4ed77bb (11 Aug 2026). <https://github.com/aiunderstand/ternary-workbench>

**S14** RV32IToREBEL (R2R). <https://github.com/Soppe/RV32IToREBEL>

**S15** SKY130 ReRAM library, with Verilog-A model and technology notes. <https://github.com/google/skywater-pdk-libs-sky130_fd_pr_reram>

**S16** OpenVAF-Reloaded. <https://github.com/OpenVAF/OpenVAF-Reloaded>

**S17** IIC-OSIC-TOOLS. <https://github.com/iic-jku/IIC-OSIC-TOOLS>

**S18** ciel. <https://github.com/fossi-foundation/ciel>

**S19** ChipFoundry, ReRAM page and FAQ. <https://chipfoundry.io/reram>

**S20** Tiny Tapeout, analog specifications. <https://www.tinytapeout.com/specs/analog>

**S21** eeNews Europe, 3 Aug 2018, Leti and CMP shuttle with OxRAM. <https://www.eenewseurope.com/en/leti-and-cmps-joint-multi-project-wafer-service-integrates-silicon-oxram/>

**S22** Europractice, foundry access and membership. <https://europractice-ic.com/access-and-registration/foundry-access-and-membership/>

**S23** Texas Instruments, TPS7A47 data sheet. <https://www.ti.com/lit/ds/symlink/tps7a47.pdf>

**S24** AMD, Kria KV260 product brief. <https://www.mouser.com/pdfDocs/xilinx-kv260-product-brief.pdf>

**S25** Microsoft, BitNet b1.58 2B4T model card; S. Ma et al., arXiv 2402.17764. <https://huggingface.co/microsoft/bitnet-b1.58-2B-4T>

**S26** J. B. Roldán et al., "On the Thermal Models for Resistive Random Access Memory Circuit Simulation", Nanomaterials 11, 1261 (2021). <https://doi.org/10.3390/nano11051261>

**S27** D. A. Trejo Pizzo, "Multi-Level Resistive Synapses for On-Chip Neural Networks", arXiv 2606.22621. <https://arxiv.org/abs/2606.22621>

**S28** IEEE Xplore record of the REBEL-6 paper. <https://ieeexplore.ieee.org/document/11038296/>

**S29** m1frame. <https://github.com/ofFBeaT9/m1frame>

**S30** eeNews Europe, 16 May 2025, Tiny Tapeout after the Efabless closure. <https://www.eenewseurope.com/en/tiny-tapeout-sees-industrial-boost-as-it-recovers-from-efabless-closure/>

**S31** RAELLA, arXiv 2304.07935. <https://arxiv.org/abs/2304.07935>

**S32** IHP, MPW and prototyping service. <https://www.ihp-microelectronics.com/services/research-and-prototyping-service/mpw-prototyping-service>

**S33** Gnucap and gnucap-modelgen-verilog, snapshot tag 20260729-dev. <https://github.com/gnucap/gnucap-modelgen-verilog>

**S34** ngspice 46. <https://github.com/imr/ngspice>

**S35** Yosys, commit 0605026 (6 Oct 2026), with the slang front end and the CXXRTL back end. <https://github.com/YosysHQ/yosys>

**S36** IHP, open-silicon MPW access: low-cost runs for open-source designs, prices, conditions, packaging. <https://www.ihp-microelectronics.com/services/research-and-prototyping-service/mpw-prototyping-service/low-cost-open-source-mpw-access-1>

**S37** S. Bos, doctoral thesis on ternary computing, University of South-Eastern Norway: section 4.3.4 and Table 4.1, variants of binary-coded balanced ternary. Read from a PDF copy on your PC (file name 2023_189_Bos); the link is the university's announcement of the defence. <https://www.usn.no/english/research/postgraduate-studies-phd/public-defences/steven-bos>

**S38** OpenSTA 3.1.0, commit b7d866f (6 Oct 2026), Parallax Software. <https://github.com/parallaxsw/OpenSTA>

**S39** OpenROAD-flow-scripts: platforms ihp-sg13g2 and sky130hd; the sky130_fd_sc_hd timing library used in section 21 is the copy in its sky130hd platform. <https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts>

## 18 Design results from simulation

This section reports what was designed and simulated after revision 2, in an isolated cloud environment with open tools. Every number comes from a script in the project repository and is stored in its results folder; section 19 says how to re-run them. Revision 4 audited this section (section 20); corrections are marked. Read each result as a statement about the models. The device model rests on IHP's published data, and no measured data or MEMRES kit was available.

### 18.1 Tools and checks

| **Tool** | **Version** | **Use, and the check that it works** |
|---|---|---|
| **Gnucap with gnucap-modelgen-verilog \[S33\]** | Snapshot tag 20260729-dev | Circuit simulation with the PDK's PSP 103 transistor models and a Verilog-A ReRAM model. The PDK's own reference tests for the low-voltage and high-voltage MOS models give output identical to the reference files: 26 of 26 tests, 6,625 lines compared. RF variants and the PDK's Monte Carlo tests were not run. Those reference files were made with Gnucap, so this shows a correct build, not a correct simulator. Added in revision 4: 16 current sweeps compared with the ngspice reference data in the PDK agree within 0.1 % at all 4,264 points above 100 nA. |
| **IHP-Open-PDK \[S1\]** | main, 1 Sep 2026 | Transistor models, five process corners, mismatch model, standard-cell timing library. |
| **ngspice \[S34\]** | 46 | A second simulator for the ReRAM model. |
| **Yosys with slang and CXXRTL \[S35\]** | 0.69+, 6 Oct 2026 | Elaboration of the SystemVerilog, a compiled simulation model for the test bench, synthesis on IHP standard cells. |
| **OpenSTA \[S38\]** | 3.1.0, 6 Oct 2026 | Added in revision 4.1. Static timing analysis of the mapped netlist (section 21.3). Built from source with Tcl, SWIG, CUDD and Eigen. |
| **Python with NumPy and SciPy** | 3.13 | Reference models, tile model, experiment drivers, and the independent re-derivations of the audit. |

OpenVAF, Xschem, KLayout, LibreLane and Verilator could not be installed there (section 19.4). The Gnucap flow is a second open route that the PDK supports; it is not the route revision 2 recommended, and the work should be repeated in the container flow on your PC as a cross-check.

### 18.2 Device model

The Stanford-PKU model of section 5 was written three times: a Python reference, a behavioral ngspice subcircuit, and Verilog-A with the gap held on a circuit node and integrated by the simulator, as section 5.3 proposed. The static parameters are IHP's published values (Table 5.1).

**Finding: the published kinetic values do not reproduce the published switching.** With E<sub>a</sub> = 0.6 eV and v<sub>0</sub> = 0.4 m/s the model sets at 0.21 V in a continuous ramp (0.25 V on a staircase of 0.05 V steps), and a 0.2 V read erases the high-resistance state within a second. The same paper measures set voltages of 0.65 to 0.75 V. Either the printed values belong to a different form of the rate equation, or they contain an error; the paper does not say. The kinetics were therefore re-fitted with two constraints: E<sub>a</sub> = 1.0 eV, inside the 0.97 to 1.16 eV range that IHP measured from retention \[S10\], and v<sub>0</sub> chosen so that the set voltage in the published sweep is 0.70 V. The result is **v<sub>0</sub> = 2.79 m/s**.

**Table 18.1 Switching behavior: published, printed parameters, re-fitted parameters**

| **Quantity** | **Published \[S9\]** | **Model, printed kinetics** | **Model, re-fitted** |
|---|---|---|---|
| Set voltage, 0.6 V/s ramp | 0.65 to 0.75 V | 0.21 V (0.25 V in 0.05 V steps) | 0.70 V |
| Reset voltage, quasi-static | 0.6 to 0.9 V | not evaluated | 0.55 to 0.85 V |
| HRS under a 0.2 V read | stable | erased within 1 s | gap moves 0.006 pm in 1 s and 6 pm in 1,000 s |

Reset voltages with the 4.5 µm select transistor of section 18.3. The fit uses one measured number, the set voltage. Everything that depends on time or on low voltages is therefore weakly constrained. The audit integrated the same equations with a general-purpose stiff solver and reproduced the ramp result of the three implementations within 0.3 mV (section 20.5).

The same paper has three smaller inconsistencies, found when its text was read again for revision 4: its equation 1 is printed with a positive exponent, the hopping distance a<sub>0</sub> is missing from its parameter table (0.25 nm is assumed here), and its HRS gap of 1.88 nm lies above its own upper gap limit of 1.8 nm. None changes a result here, but together with the kinetic values they say that the printed parameter set is not a complete, tested model.

> **The model to use is IHP's own.** IHP states that the MEMRES module comes with a process design kit that includes layout and a Verilog-A simulation model \[S3, S5\]. It was not available for this work. The model of this section is a stand-in built from published values. When the kit model is available, it replaces this one, and sections 18.2 to 18.6 are to be run again with it.

**Table 18.2 Static check at IHP's published gap values, read at 0.2 V**

| **Level (gap)** | **Published 1T1R resistance \[S9\]** | **Model, cell alone** | **Model, cell with a 1.5 µm select transistor** |
|---|---|---|---|
| LRS1 (0.95 nm) | 16 kΩ | 11.6 kΩ | 13.5 kΩ (−16 %) |
| LRS2 (0.85 nm) | 11 kΩ | 8.1 kΩ | 10.0 kΩ (−9 %) |
| LRS3 (0.73 nm) | 8 kΩ | 5.3 kΩ | 7.2 kΩ (−11 %) |
| HRS (1.88 nm) | 170 kΩ | 320 kΩ | 323 kΩ (+90 %) |

The published transistor belongs to IHP's 0.25 µm process and could not be reproduced, so the last column is indicative. The Phase 1 criterion of ±15 % is met for LRS2 and LRS3, missed by one point for LRS1 and missed for HRS. The HRS level of a programmed array is set by the reset target (2.85 µA mean, about 70 kΩ), not by this gap value.

**The three implementations agree.** On the cell alone: the set voltage in the ramp within 0.26 mV, the gap after a 1 µs pulse within 0.5 pm, the time to set after a 1.1 V step within 0.11 % and the time to reset after a −1.0 V step within 1.0 %. Agreement between solvers shows that the equations are implemented consistently. It says nothing about whether the equations describe the device.

#### What the model does not contain

- Forming. Every cell needs it once, and the forming voltage decides which transistors may be used (section 13).

- Retention loss without bias, and any temperature dependence of the read current.

- Cycle-to-cycle randomness and device-to-device spread. The tile model of section 18.4 samples the published distributions instead.

- A gradual reset. The model resets abruptly to its 1.8 nm limit (0.8 µA), while measured arrays stop near the 6 µA target with a mean of 2.85 µA.

### 18.3 Select transistor and programming

The cell was simulated with IHP's 3.3 V NMOS model at the minimum length of 0.45 µm. Pulse-and-verify follows the published scheme of section 8: 1 µs pulses, amplitude from 0.5 to 2.5 V in 0.1 V steps, a read at 0.2 V after every pulse.

**Table 18.3 Select-transistor width, typical corner**

| **Width** | **On-resistance at read** | **Gate voltage that reaches 18.1 / 31.0 / 43.6 µA** | **Reset of the 43.6 µA state, gate at 2.7 V** |
|---|---|---|---|
| 1.5 µm | 1.76 kΩ | 1.60 / 2.15 / 2.95 V | Fails, also with a 3.3 V gate |
| 3.0 µm | 0.85 kΩ | 1.20 / 1.45 / 1.70 V | At 2.1 V after 17 pulses |
| **4.5 µm** | 0.57 kΩ | 1.10 / 1.30 / 1.45 V | At 1.4 V after 10 pulses |
| 6.0 µm | 0.43 kΩ | 1.05 / 1.20 / 1.30 V | At 1.2 V after 8 pulses |

Reference model with a table of the transistor current taken from the PSP 103 model. Lowest gate voltage in 0.05 V steps.

A width of **4.5 µm** is the smallest of these that resets with margin, and it is the working value from here on.

**Cell area, corrected in revision 4.** Revision 3 quoted 6.6 µm<sup>2</sup> per device and 0.023 mm<sup>2</sup> for the 3,456 devices of a tile, from a pitch of 2.0 µm by 3.28 µm. That pitch was assumed before the transistor was sized, and a 4.5 µm wide transistor does not fit across 3.28 µm. A count of the PDK's layout rules for this transistor, with two rows sharing a source contact row, gives 1.085 µm along the bitline and 4.71 µm across: 5.1 µm<sup>2</sup> per device and 0.018 mm<sup>2</sup> per tile, in a block of about 78 µm by 226 µm. This is a lower bound: it contains the transistor only, not the ReRAM element, the routing or the substrate contacts. Until the foundry cell is known the array is taken as about 0.02 mm<sup>2</sup>. The assumed 2.0 µm row pitch stays in the tile model as the cautious value: with the 1.085 µm pitch the bitlines are shorter, and the uncalibrated analog error of the thin-metal case falls from 0.55 to 0.46 result steps.

**Table 18.4 Process corners at 4.5 µm width, full circuit simulation**

| **Corner** | **Saturation current** | **Set with the typical-corner gate voltages 1.10 / 1.30 / 1.45 V** | **Set with one gate voltage of 1.7 V, target 43.6 µA** | **Reset, gate 2.7 V** |
|---|---|---|---|---|
| Typical | 547 µA/µm | Reached: 18.2 / 31.1 / 44.0 µA | 44.2 µA at 1.3 V, 9 pulses | 1.4 V, 10 pulses |
| Slow | 479 µA/µm | **Missed**: 13.8 / 27.5 / 38.7 µA after all 21 pulses | 45.6 µA at 1.5 V, 11 pulses | 1.6 V, 12 pulses |
| Fast | 619 µA/µm | Reached: 18.2 / 32.5 / 44.9 µA | 50.3 µA at 1.3 V, 9 pulses | 1.4 V, 10 pulses |

Gnucap transients with the PSP 103 model and the Verilog-A cell, 1 ns maximum time step. A step five times smaller gave the same gaps in four test pulses.

- **The fast reference model can be trusted for sweeps.** For all three set levels and the reset at the typical corner, the Python model with the transistor table and the full Gnucap transient give the same amplitude and pulse count, gaps within 1 pm and verify currents within 0.1 µA.

- **A fixed gate voltage per level does not survive process corners.** The gate voltage sets the current limit, and the limit moves with the transistor. Multi-level programming therefore needs a gate voltage trimmed per chip, or a gate voltage that is stepped as well. The two-state design avoids the problem: one generous gate voltage and a stop on the verify read work in all three corners, at the price of a level that lands between 44 and 50 µA. Digital mode does not care where above the reference it lands.

- **Programming current, corrected in revision 4.** A device carries about 0.50 mA at the end of a set pulse and 0.52 to 0.60 mA at the start of a reset pulse. A row of 24 weights programmed in parallel draws 12 mA in the set phase and up to 29 mA in the reset phase. Revision 3 compared this total with the 2 mA rating of a 1 µm source line and concluded that the lines must be widened or the row programmed in parts. That comparison was wrong for the modeled array: its source lines run along the columns, one per column pair, so each carries the current of one cell: about 0.5 mA in a set pulse, and at most 1.2 mA in a reset pulse when both devices of a cell are reset together, as after forming. Both are inside the rating (Table 6.3). The total is a requirement on the bitline and source-line drivers, the supply pads and the ground return. A layout that shares one source line along a row would put the whole row current into that line and need about 15 µm of Metal2–5. Contacts are rated for 0.3 mA each and vias between the thin metals for 0.4 mA \[S2\], so the path of one device needs at least three contacts and two vias in parallel. The transistor has room for about 13 contacts per terminal.

### 18.4 Tile: analog mode

The tile model solves the resistive network of a 72 × 24 tile: two bitlines and one source line per ternary column, all three running along the column and the source line grounded at the clamp end, the cell currents sampled from the published distributions of Table 4.1, a clamp with input resistance and offset at the end of each bitline, a current mirror with gain error, and the two-phase evaluation of section 6.3. Inputs and weights are random with one third zeros. The fast solver was checked against a direct solution of the full network. Revision 3 described the source line as shared per row; the model has always had it per column, and its results are unchanged. In the audit the solver was compared with a second one that enters every resistor separately into a full matrix: the bitline currents agree to better than one part in 10<sup>10</sup>.

**Table 18.5 Analog-mode error of a 72-row result, in result steps**

| **Case** | **RMS error** | **Exact** | **Within ±1** | **Largest** |
|---|---|---|---|---|
| LRS3, published spread, TopMetal1 bitlines | 0.41 | 77 % | 99.97 % | 1.7 |
| LRS3, twice the published spread | 0.75 | 49 % | 95.4 % | 3.0 |
| LRS3, published spread, 0.4 µm Metal2–5 bitlines clamped at one end, uncalibrated | 0.55 | 63 % | 99.3 % | 2.2 |
| The same after per-column gain and offset calibration | 0.45 | 73 % | 99.9 % | 2.1 |
| LRS1, published spread | 1.20 | 33 % | 79 % | 5.1 |
| LRS1, twice the published spread | 2.26 | 18 % | 50 % | 10.1 |

The analytic figure of Table 6.1 is 0.50 for 72 rows with every weight and input non-zero. With one third zeros about 48 rows contribute, which gives 0.41. The closed-form value for these statistics is 0.42 (section 20.5).

- **Device spread is the floor.** Ideal wires give the same 0.41. Nothing in the periphery can go below it.

- **Wiring and rows per read matter little once the bitlines are in TopMetal1.** Reading 24 rows at a time instead of 72 changes nothing with TopMetal1, and little with thin metal after calibration. The 24-row limit of revision 2 is dropped (section 6.6).

- **The clamp must have a low input resistance.** Up to 5 Ω the error does not change. At 20 Ω the uncalibrated RMS error rises to 0.46 and at 50 Ω to 0.67, because a bitline with all rows selected has a resistance of only about 64 Ω.

- **Clamp offset and mirror gain error are minor**: 2 mV and 1 % together change the RMS error by less than 0.01.

- **LRS1 is not usable for analog sums.** It confirms the choice of LRS3 in section 6.6.

### 18.5 Tile: digital mode, and a network

**Table 18.6 Digital-mode read errors**

| **Level and spread** | **Wrong weights in 103,680** | **Products with an error, of 600** | **Analytic misread probability per device** |
|---|---|---|---|
| LRS3, published | 0 | 0 | 2 × 10<sup>−33</sup> |
| LRS3, twice published, 2 mV clamp offset | 0 | 0 | 1 × 10<sup>−9</sup> |
| LRS3, three times published | 4 | 24 | 3.2 × 10<sup>−5</sup> |
| LRS1, published | 2 | 14 | 3.2 × 10<sup>−5</sup> |
| LRS1, twice published | 4,616 | 600 | 2.3 × 10<sup>−2</sup> |

Sixty tiles of 1,728 weights for each case, ten products per tile, with the least favorable periphery of section 18.4: 0.4 µm Metal2–5 bitlines and a 50 Ω clamp. The analytic column uses a reference at the equal-margin point between the two levels; it predicts 6.7, 6.6 and 4,732 wrong weights for the last three rows (section 20.5).

With LRS3 the digital mode returns the exact product under the published statistics, and still does when every spread is doubled. That is the margin against the warning in section 4 that a first layout will be worse than the published arrays.

> **What "exact" means here (added in revision 4).** The result holds for bell-shaped distributions with the published means and standard deviations. Those figures are fits to 4-kbit arrays read directly after programming. They say nothing reliable about the far tails, about cells that drift after programming, or about cells that are stuck. On silicon, an exact digital mode will rest on the verify step, on read-back and on re-programming the cells that moved (section 8), not on a 12-sigma calculation.

**A network.** A small all-ternary network (72 inputs, 72 hidden units, 10 outputs; ternary weights, inputs and activations) was trained on the 8 × 8 digits set and run through the tile model. Software accuracy on the 360 held-out samples is 94.7 %. Digital mode gives the identical 94.7 % with no differing result. Analog mode gives 94.6 to 95.3 % across spread and wiring cases, although 25 to 83 % of its first-layer sums differ from the exact values: the threshold activation absorbs errors of one step. The data set is small and easy, so this shows that the approach is not broken, not that it scales. There is no separate validation set: the training settings were fixed with the 360 held-out samples in view, so 94.7 % is a little optimistic as an estimate of accuracy. The comparisons between software, digital mode and RTL do not depend on it.

### 18.6 Read path

A first read circuit for the digital mode was simulated with the PDK transistors: a 1.2 V current mirror that supplies the reference current, a clamp transistor between the mirror output and the bitline, a 3.3 V column switch, and an inverter as output stage. The clamp gate comes from a replica, a diode-connected copy of the clamp transistor that carries the reference current and stands on a 0.2 V reference. The replica makes the bitline sit at 0.2 V at the trip point in every corner. The two references are ideal sources in this version, and all sizes are first guesses.

**Table 18.7 First-cut sense amplifier**

| **Quantity** | **Result** |
|---|---|
| Trip current, five process corners | 24.61 to 24.66 µA for a 25 µA reference with a 5 µA keep-alive current |
| Trip current with transistor mismatch | mean 24.64 µA, standard deviation 0.24 µA, range 24.03 to 25.37 µA (200 Monte Carlo runs, PDK mismatch model, typical corner) |
| Distance from the trip point to the device distributions | LRS3 mean minus six standard deviations is 34.3 µA; HRS mean plus six is 14 µA |
| Output valid after the wordline rises, LRS3 at its mean | 2.1 to 2.2 ns |
| The same for LRS3 six standard deviations low | 2.9 ns typical, 3.1 ns slow, 2.75 ns fast |
| HRS up to six standard deviations high | Output stays low in the typical, slow and fast corners |
| Bitline voltage | 0.20 V at the trip point; 0.23 V for an HRS cell six standard deviations high; 0.29 V for a mean HRS cell; 0.32 V idle |
| Supply current per bitline | 30 µA for an LRS cell, 9.4 µA for a mean HRS cell; 60 µA of references that all columns can share |

Transients with the selected cell at 4.5 µm width and the other 71 cells of the column lumped into one scaled cell with its wordline low, in LRS and in HRS; 30 fF of wire. The state of the other cells changed the timing by 0.1 ns.

- **The two states are resolved in about 3 ns** with a trip point that mismatch moves by about 1 %. The reference is some 40 mismatch standard deviations away from either six-sigma device tail.

- **A keep-alive current is needed.** Without it nothing defines the voltage of an idle bitline, and the simulator settled at a meaningless value. With 5 µA the idle bitline sits at 0.32 V.

- **The plain clamp reads HRS cells at a higher voltage than LRS cells**: 0.29 V instead of 0.20 V. In the model this shortens the life of an HRS state under reading from 7 × 10<sup>11</sup> reads to 5 × 10<sup>10</sup> reads for a 10 % rise in current. These numbers come from the one-point kinetic fit and may be wrong by orders of magnitude in either direction. They show the direction of the risk. The remedies are a regulated clamp (which costs a permanent amplifier current per column), a lower read voltage, or a periodic refresh. Choose with measured data.

### 18.7 Digital design

TCIM0 is written in SystemVerilog with the register map of section 9.3: a 4-wire serial port, the register block, a sequencer for digital-mode products (one row read per non-zero input), one for the two-phase analog product, one for programming a row with pulse-and-verify, and read-back. The analog part connects through a request-and-acknowledge interface. Trits use two wires. The default is a two's-complement code (01 for +1, 00 for 0, 11 for −1); since revision 4.1 the BSD-PNX code of the REBEL group's tools is a build option, and the logic no longer depends on the code values anywhere outside one package file (section 21.2).

**Changed in revision 4.** Reading the code in the audit found two faults, both now fixed: the interrupt line followed WERR as well as DONE and could not be acknowledged after a failed command, and the serial port's bit counter wrapped, so clocks after the 16th byte of an over-long frame were decoded as a new frame. A third change makes every command clear the SAT flag, and the stated limit for the serial clock is corrected from a quarter to an eighth of the system clock. No computed result was affected. The test bench was then extended until it detects every fault of the mutation test described below.

**Table 18.8 Verification**

| **Test** | **Result** |
|---|---|
| Register access through the serial port, misaligned and unmapped access | Pass |
| Programming all 72 rows with verify, then read-back. *New:* a monitor on every pulse checks that the amplitude starts at 0 and rises one step per pulse, that reset pulses come before set pulses, that no pulse reaches a device that has passed its verify read or must not change, and that PITER equals the pulses delivered | Pass. 15.1 pulses per row on average in the behavioral array |
| 150 digital-mode products against the exact dot product, 24 columns each | Pass, all equal |
| Interrupt raised on completion and cleared by reading STAT. *New:* reported in the serial status byte; stays low with IE at 0; cleared by GO; can be acknowledged after a failed command; not cleared by a write | Pass |
| 40 analog-mode products against the expected converter counts. *New:* clipping at ±364 with the SAT flag, at full scale and one count beyond; SAT cleared by the next command | Pass |
| Error paths: a device that never sets, a cell with both devices in LRS. *New:* a device that never resets; an invalid cell seen by read-back; every row index a tryte can hold outside 0 to 71 (657 values) refused without an array access | Pass, each reported in STAT |
| *New:* the unused trit code read as 0 in inputs, weights and row index; every result value from −364 to +364 through the binary to balanced-ternary conversion | Pass |
| *New:* a device at 30 µA read as LRS and one at 20 µA as HRS; writes, a second GO and a mode change ignored while busy; nothing started with EN at 0; serial frames cut short and over-long; the serial clock at one eighth of the system clock with a host that samples on the rising edge | Pass |
| The digits network of section 18.5 through the RTL, 360 samples, four tiles of weights programmed through the register map | 341 correct, as in software; same class as software for all 360; no first-layer result differs |
| *New:* all 72 rows read back unchanged after the directed tests | Pass |
| Total | **81,966 checks, no failure**; 44.8 million clock cycles |
| *New:* mutation test, 69 copies of the logic with one deliberate fault each | All 69 detected. 66 of them date from the audit; the revision 3 test bench missed 30 of those |
| *Revision 4.1:* the whole test bench again on the logic built with the BSD-PNX trit code, and the fault campaign with the faults that only matter in that code | 81,966 checks, no failure. 75 of 75 faults detected |
| *Revision 4.1:* after reset every register reads zero trits over its whole 48-bit field; no data on MISO during a write | Pass |

Test bench in C++ on the simulation model that Yosys generates from the RTL. The array is behavioral: per-device currents drawn from the published distributions and random switching thresholds. Revision 3 reported 60,401 checks and revision 4 reported 71,598; the count says how much was compared, not how many kinds of fault would be noticed, which is what the mutation test measures.

**Table 18.9 Synthesis on IHP standard cells, typical corner, 1.2 V**

| **Block** | **Cells** | **Flip-flops** | **Cell area** | **Estimated switching energy** |
|---|---|---|---|---|
| TCIM0 with serial port | 7,560 | 844 | 0.111 mm<sup>2</sup> | not estimated |
| TCIM0 core alone | 7,146 | 668 | 0.098 mm<sup>2</sup> | 27.8 pJ per clock cycle, of which 20.4 pJ is the clock |
| Yardstick: 24-lane ternary dot product, registered (the arithmetic of one TMAC.T) | 680 | 116 | 0.011 mm<sup>2</sup> | 6.65 pJ per step |
| Yardstick: the same tile with its weights in flip-flops | 12,452 | 3,848 | 0.322 mm<sup>2</sup> | 138 pJ per cycle, 10.1 nJ per product |

Area is the sum of cell areas before placement. The energy estimate counts signal toggles in a zero-delay simulation of the mapped netlist and applies the library's pin capacitances and internal energies. It has no glitches, no clock tree and no wires, and none of the blocks is clock-gated. Expect real figures 1.5 to 3 times higher for the logic. Use it to compare orders of magnitude. The TCIM0 rows are for the logic of revision 4.1, in which the result conversion is a table (section 21.3); revision 4 had 7,737 and 7,234 cells, revision 3 had 7,765 and 7,282. This netlist is mapped for small area; section 21.3 uses a second netlist mapped for the clock period.

The mapped netlists were also checked for function at gate level: the TCIM0 core returned the exact result for 6 digital-mode products (144 values), the dot-product block for 1,199 random vectors, and the flip-flop tile for 12 products.

### 18.8 Energy, time and the provisional Gate G1 decision

**Table 18.10 One 72 × 24 product in digital mode, random data**

| **Contribution** | **Energy** | **Basis** |
|---|---|---|
| Cell currents at 0.2 V | 0.03 nJ | Tile model, 47.9 rows read, 4 ns per read |
| Sense amplifiers, from the 1.2 V supply | 0.19 nJ | Simulated supply currents, 4 ns per read. 0.49 nJ if the amplifiers stay on for a 10 ns clock period |
| Wordlines | 0.06 nJ | 454 fF of gate capacitance per row, 1.7 V swing |
| Digital logic as synthesized | 3.5 nJ | 123 clock cycles at 27.8 pJ, plus three register writes; estimate of Table 18.9 |
| Time | 1.23 µs | At a 100 MHz clock; 2.6 cycles per row read in the present sequencer. Before layout the logic meets 10 ns at all three library corners (section 21.3) |

The first row is what the array itself dissipates and is contained in the second: the cell current is drawn from the 1.2 V supply through the sense amplifier, so the supply pays about six times as much.

- **The clocked logic dominates.** Three quarters of its energy is clock power, most of it in flip-flops that do not change during a product. Clock gating and a sequencer that needs one cycle per row are the first optimizations, ahead of anything in the array. They are not done yet.

- **Analog mode costs more energy, not less.** Its bitline currents flow for the whole conversion. With clamps on a 1.2 V supply and 200 ns per phase that is about 9 nJ per product before the converter is counted, against about 0.3 nJ for the analog part of digital mode. What analog mode can offer is time: two conversions, about 0.4 µs, against 1.2 µs.

- **Plain CMOS is in the same range.** The arithmetic of 72 TMAC.T steps is about 0.48 nJ by the same estimate, without the processor's own cost of fetching 72 words of weights and executing the instructions. A tile with flip-flop weights takes about 10 nJ ungated and 0.32 mm<sup>2</sup>.

**Provisional decision at Gate G1.** Digital mode is the product: it is exact under the published statistics with a wide margin, its analog energy is small, and it does not depend on any analog accuracy. Analog mode stays on the first chip as an experiment for latency, as section 6.2 intended, and is not on the critical path. At this tile size the case for ReRAM is not energy per operation. It is that 1,728 weights are stored without power in about 0.02 mm<sup>2</sup> of array (section 18.3), between a seventh and a tenth of the 0.17 mm<sup>2</sup> of flip-flops that would hold them, and are used where they are stored. The array's periphery is not counted in that comparison. The decision becomes final when the remaining circuits confirm the figures of Table 18.10.

### 18.9 What these results establish, and what they cannot

You asked for a design that is certain to work before tape-out is considered. Three kinds of certainty are involved, and only two of them can be had from simulation.

| **Kind** | **Can be made certain before silicon** | **Status** |
|---|---|---|
| **Logic** | Yes. The RTL is compared with an exact reference, and properties can be proven formally. | Verified by simulation at RTL and gate level, and the test bench itself is measured by fault injection (section 20.4). Since revision 4.1 the logic is proven equal to the audited logic and its timing is analyzed before layout (section 21). Formal proofs of the sequencers, a second simulator and timing after place and route are still to do. |
| **Circuit margins** | Yes, against a stated range of device behavior, by simulating corners, mismatch, temperature and extracted layout. | Done for the cell and a first read circuit at three to five corners and with mismatch. Not done: temperature, layout parasitics, and every other circuit. |
| **Device behavior** | No. Whether the cells on the wafer fall inside the assumed range is not knowable from simulation. | Assumed from published data of an older process. The kinetics rest on one fitted number. |

The plan answers the third kind with margin and with structure, not with more simulation: a two-state read that tolerates twice the published spread, a digital mode whose correctness does not depend on analog accuracy, programming that stops on a verify read instead of trusting a recipe, single-cell test structures with direct pad access on the first chip, and a host-side sequencer that can be changed after measurement. The honest target before tape-out is therefore: logic proven, every circuit inside its margins over corners, mismatch, temperature and extraction, for a device range that IHP's own data confirm. The last clause needs the answers to section 13.

## 19 Hand-over: continuing in Claude Code

### 19.1 The repository

The work of section 18 is one folder, reram-ternary, delivered with this document. Its file CLAUDE.md is the project memory that Claude Code reads on start, and docs/STATUS.md lists what is verified and what is open.

| **Folder** | **Content** |
|---|---|
| **model** | ReRAM model in Python, Verilog-A and ngspice form; calibration; pulse-and-verify; transistor sizing; read disturb; the three-solver check |
| **array** | Tile model and its experiments: analog error, digital mode, network, energy |
| **circuits/gnucap** | Gnucap decks driven from Python: transistor tables, the 1T1R cell, the sense amplifier, Monte Carlo, the PDK reference check |
| **circuits/ngspice** | ngspice decks for the cell model |
| **rtl** | TCIM0 in SystemVerilog, and the two digital yardsticks |
| **tb** | The self-checking test bench, its vectors, and the mutation test |
| **tests** | The audit: independent re-derivations, and a check of every number quoted in sections 18, 20 and 21 against the stored results. In tests/equiv, the equivalence proofs and the revision 4 logic they refer to |
| **synth** | Synthesis scripts, Liberty reader, gate-level simulator and energy estimate; the timing-driven synthesis and the OpenSTA script of section 21.3 |
| **flow/orfs** | Configuration for place and route with OpenROAD-flow-scripts on IHP SG13G2 and on SKY130, with the design as plain Verilog. Run on the PC in revision 4.2 (section 22.1) |
| **results** | Every number quoted in section 18, as JSON files and logs |
| **docs** | Status, this document, and the audit report |
| **tools** | A script that builds the simulators at the versions used here |

### 19.2 Re-running the results

With the tools on the path and two environment variables set (the PDK's Gnucap folder and the standard-cell library; tools/build_tools.sh prints them), the Makefile reproduces each group of results:

| **Command** | **What it does** |
|---|---|
| **make pdk-check** | Runs the PDK's 26 MOS reference tests in Gnucap and compares 16 sweeps with the PDK's ngspice reference data |
| **make check-model** | Re-fits the kinetics and compares the three implementations of the device model |
| **make cell** | Builds the transistor table, sizes the select transistor, confirms set and reset in full transients at three corners |
| **make sense** | Runs the read path: corners, transients, mismatch Monte Carlo, read disturb |
| **make array** | Runs the tile experiments (tens of minutes) |
| **make rtl** | Builds and runs the TCIM0 test bench |
| **make mutation** | Injects the faults one at a time and reports which the test bench detects (about an hour on two cores) |
| **make rtl-pnx, make mutation-pnx** | The same test bench and fault campaign on the logic built with the BSD-PNX trit code |
| **make equiv** | Proves that the conversion table equals its definition, that the logic equals the logic of revision 4, and that the place-and-route source equals the RTL |
| **make sta** | Timing-driven synthesis and OpenSTA at three IHP corners for both trit codes, and on SKY130 if its library is given |
| **make test** | Runs the independent re-derivations and checks the quoted numbers against the stored results |
| **make synth** | Synthesizes the three blocks and runs the gate-level checks and energy estimates |

### 19.3 Next tasks, in order

1.  **Set up the PC.** Your PC already holds part of the tool chain from earlier projects: OpenROAD-flow-scripts and OpenLane in Docker, with the platforms ihp-sg13g2 and sky130hd, and QuestaSim, Vivado and Icarus Verilog. Start with flow/orfs/run_orfs_docker.bat for place and route of the logic. For the analog work install the IIC-OSIC-TOOLS container (section 10), copy the repository into it, and re-run section 19.2. Build Gnucap inside it with tools/build_tools.sh if it is not there. Repeat the device and cell simulations with OpenVAF and ngspice or VACASK as an independent check of the Gnucap results.

2.  **Ask IHP for the MEMRES design kit with its Verilog-A model**, and send the other technical questions of section 13: device data, forming voltage, cell size. The design needs them whether or not a tape-out is planned. With the kit model, re-run make check-model cell sense array and compare.

3.  **Digital clean-up.** Clock gating, one cycle per row read, lint, a second simulator (Verilator, Icarus or QuestaSim), formal checks of the sequencers with SymbiYosys, place and route with OpenROAD-flow-scripts for real area, wire delay and energy, then timing again on the routed design. Timing before layout is done (section 21.3). Keep the mutation test passing after every change, and add a fault to it for every bug found.

4.  **Circuits.** In this order: wordline driver with selectable levels; bitline and source-line drivers sized for the programming current, or a serialized scheme; level shifters; reference current and the 0.2 V reference; the read path over temperature and supply with the references included; the test multiplexer. Then, only for the experiment, the analog-mode clamp (below 5 Ω at 3 mA) and converter.

5.  **Device model.** Add device-to-device and cycle-to-cycle spread and a gradual reset to the compact model, calibrated to Table 4.1, so that programming can be simulated statistically and not only read-out.

6.  **REBEL-6.** Build the R2R simulator and the assembler, attach a model of TCIM0, and run one program against software TMAC.T. Ask the maintainers about slot 11 and interrupt 7, and whether REBEL-6 hardware uses the BSD-PNX code.

7.  **Layout study.** Draw one 2T2R cell with the 4.5 µm transistor in KLayout to replace the rule count of section 18.3 with a real cell, decide where the source lines run, and extract one bitline.

8.  **Close Gate G1** with the simulated energy and time of the complete read path and the optimized logic.

### 19.4 Limits reached in the sandbox

- **No package sources.** Python, Node, Rust and most system packages could not be installed; only source code from GitHub could be fetched. That excluded OpenVAF (needs Rust and LLVM), KLayout, Xschem, LibreLane, Verilator, cocotb and SymbiYosys, and it is why Gnucap, ngspice and Yosys were built from source. OpenSTA was built the same way for revision 4.1, with its four dependencies. OpenROAD needs many more and was not attempted.

- **Two processor cores and no graphics.** A transient with the PSP models runs at about 3 ms per time step, so a programming pulse takes 4 to 8 s and a statistical study of programming was out of reach. Schematic entry and layout need a display.

- **No foundry data.** No MEMRES kit, no measured curves. This is a limit of the project, not of the sandbox, and it is the one that matters most.

- **Nothing persists.** The environment is deleted when the session ends. Everything worth keeping is in the delivered repository and in this document.

## 20 Audit of revision 3

You asked for revision 3 to be evaluated heavily and fact-checked. This section is the report. The audit asked six questions, each with a method that could prove the work wrong (Table 20.1). It did prove parts of it wrong. Every finding is either corrected in this revision or listed as open in section 20.6.

> **Result.** The simulated results of sections 18.2 to 18.6 held: every quoted number matches its stored result, the key ones were reproduced by a second method, and the transistor models agree with reference data from a different simulator. The digital logic had two faults and its test bench had blind spots; both are repaired, and the repair is measured. Four statements about the outside world were out of date or incomplete. One of them, the free shuttle, changes the cost of the plan, and one, the Verilog-A model in IHP's kit, changes what to ask IHP first. One conclusion about programming current was wrong. Nothing found puts the architecture in question. The largest uncertainty is where it was before: the device data.

### 20.1 Method

**Table 20.1 The six questions of the audit**

| **Question** | **Method** | **Outcome** |
|---|---|---|
| **Does every number in section 18 match a stored result?** | A script compares each quoted number with the result files (tests/test_claims.py). | 232 numbers, none stale |
| **Are the results right, or only reproducible?** | Key results derived a second time with a method that shares no code with the first (tests/test_independent.py). | 9 checks, all agree (Table 20.6) |
| **Do the tools agree with a reference from outside this project?** | Transistor currents from the Gnucap build compared with the ngspice reference data shipped in the PDK. | 4,264 points within 0.1 % |
| **Would the test bench notice a broken design?** | Mutation test: 66 copies of the logic, each with one deliberate fault, run against the test bench (tb/mutation_test.py). | Revision 3 test bench: 30 faults unnoticed. Now: none |
| **Is the code right?** | The logic, the device model and the experiment scripts were read line by line against the text that describes them. | Two faults in the logic, a wrong speed limit, one wrong description, one wrong conclusion (Table 20.3) |
| **Are the external facts still right?** | Each fact the plan depends on was read again from the text of its source page on 6 October 2026. | Four changes (Table 20.2) |

### 20.2 External facts

**Table 20.2 Statements that changed**

| **Revision 3 said** | **The source says** | **Effect** |
|---|---|---|
| Route B is IHP's free open-source shuttle; ask whether the program continues. | The free runs of 2023 to September 2025 were funded by the FMD-QNC project. IHP now offers open-silicon runs at €2,800 per mm<sup>2</sup> in SG13G2 and €1,500 falling to €900 per mm<sup>2</sup> in SG13CMOS5L, with packaging as an extra \[S36, S7\]. | Section 3, route B, and the cost of Phase 5 are rewritten. The route is still the cheapest way to silicon with IHP, but it is not free. |
| The form of the MEMRES kit is unknown. | IHP states that the module comes with a process design kit that includes layout and a Verilog-A simulation model \[S3, S5\]. | The first question to IHP is now how to obtain that kit. Its model replaces the stand-in of section 18.2. |
| IHP's devices use a single Al-doped HfO<sub>2</sub> layer; a two-layer oxide is the draft's invention. | The device papers do describe a single layer \[S8 to S10\]. IHP's 2021 announcement adds that HfO<sub>2</sub> and Al<sub>2</sub>O<sub>3</sub> switching layers are used in combination, without figures \[S5\]. | The verdict on the draft's stack stays (its thicknesses and recipes are unsupported), but a two-layer oxide in the foundry module is possible. Sections 2, 4 and 14 say so. |
| MEMRES tape-ins on 7 December 2026, about 31 May 2027 and 6 December 2027. | The three dates stand. Shipments are listed for 2 July 2027, 3 February 2028 and 30 June 2028, and IHP marks each MEMRES run as a run with lower priority \[S3\]. | Section 3 carries the dates. Ask IHP what lower priority means for the schedule before planning around a run. |
| Tiny Tapeout offers analog tiles on IHP at the listed prices. | The listed analog prices are for the SKY130 process, and the IHP templates list no 3.3 V supply \[S20\]. | Route C needs a direct answer before it is planned: this design needs 3.3 V. |

**Read again from the page text and confirmed unchanged:** the device statistics of Table 4.1 and the programming scheme \[S8\]; the stack and the model tables of the compact-model paper, with the three slips noted in section 18.2 \[S9\]; activation energies, endurance and retention \[S10\]; the IHP and Europractice prices and the 0.8 mm<sup>2</sup> minimum \[S3, S4\]; the REBEL-6 word size, memory map and TMAC.T \[S13\]; sheet resistances, current limits and oxide thicknesses of the process specification \[S2\]; the figures quoted from Laborieux \[S11\], Wan \[S12\], the BitNet model card \[S25\] and the TPS7A47 data sheet \[S23\]; and ChipFoundry's price and its statement on ReRAM \[S19\].

**Read again through an automatic page reader, consistent with the text:** the Leti and CMP announcement \[S21\], the KV260 brief \[S24\], the thermal-model review \[S26\], the abstract of the synapse proposal \[S27\], the Tiny Tapeout news item \[S30\] and the RAELLA abstract \[S31\]. These support verdicts on the draft, not design numbers.

**Not read:** the text of the REBEL-6 paper \[S28\], whose page refuses automated access. REBEL-6 facts come from the maintainers' repository.

**A caution about method.** During this audit an automatic page summarizer returned table values for two IHP papers that are not in the papers. Every number in this document that comes from a web page or a paper was therefore taken from the page text itself. Treat any figure that an assistant quotes from a web page with the same caution, unless it shows the text.

### 20.3 Faults found in the design and in its description

**Table 20.3 Findings from reading the code and the text**

| **\#** | **Where** | **What was wrong** | **Consequence** | **Action** |
|---|---|---|---|---|
| 1 | Logic, interrupt | The interrupt line was IE and (DONE or WERR). Reading STAT clears DONE but not WERR. | After a failed command the interrupt stayed high until the next command. A handler could not acknowledge it. | Fixed: the line follows DONE alone. WERR never occurs without DONE. Tested. |
| 2 | Logic, serial port | The bit counter had 7 bits and wrapped after 128 clocks. | If the host kept the chip selected, the clocks after the 16th byte were decoded as a new frame and could write a register. | Fixed: the counter stops at 64 until chip select rises. Tested with frames of 9, 55, 128 and 192 clocks. |
| 3 | Logic, serial port | The source file stated that the serial clock may run at up to a quarter of the system clock. | At that speed every transfer is wrong: the output changes up to three clock cycles after the falling edge, and the host samples on the next rising edge. | Limit corrected to one eighth of the system clock and tested at that speed. |
| 4 | Logic, flags | A program or read-back command cleared WERR but left SAT from an earlier analog product. | A stale flag. No wrong result. | Fixed: every command clears both. Tested. |
| 5 | Sections 18.3, 18.4 | The text said the tile has a source line per row. The model has one per column pair. The programming current of a whole row was compared with the rating of one line. | A wrong conclusion: that source lines must be widened or rows programmed in parts. | Text corrected. Each line carries at most 1.2 mA. The 12 to 29 mA applies to drivers and supply. |
| 6 | Sections 18.3, 18.8 | The cell area used a pitch chosen before the transistor was sized; a 4.5 µm transistor does not fit in it. | An area figure without a basis. | A count of the layout rules gives a lower bound of 0.018 mm<sup>2</sup> per tile. The text gives both figures. |
| 7 | Section 18.1 | The PDK tests that give "identical output" compare Gnucap with Gnucap. | They prove the build, not the simulator. | A comparison with the PDK's ngspice reference data was added. |
| 8 | Section 18.2 | The set voltage of the printed kinetic values was given as 0.25 V. | True only on a 0.05 V staircase; 0.21 V in a continuous ramp. The finding itself stands. | Text corrected. |
| 9 | Section 18.5 | "Exact" was stated without its conditions, and the accuracy of the network without saying that no validation set was used. | Readers could take a result on bell-shaped model statistics as a promise about silicon. | Conditions stated. |
| 10 | Section 9.3 | The register table gave the range of Y for digital mode only and one of three causes of WERR. | Incomplete specification. | Table completed. |
| 11 | Cell simulation script | After a reset pulse the circuit simulator can leave the gap up to 0.11 nm above the model's limit of 1.8 nm, an overshoot of its time step. The script stored that value and passed it on. | 3 stored gap values lay outside the model's range (1.80, 1.84 and 1.91 nm). No quoted number depends on them. | The script limits the value to the model's range. All three corners were run again: the other 139 stored values are reproduced exactly. |

Findings 1 and 2 were not caught by the revision 3 test bench, which is the subject of the next section.

**Left as it is, and now written down.** The result registers are valid only while BUSY is 0. A read of STAT clears DONE as soon as the address byte has arrived, even if the frame is then cut short. Clearing EN does not stop a command that is running. The logic assumes that the signals from the analog macro and the release of reset are in step with the system clock; the macro and the pad ring have to provide that.

### 20.4 The test bench under fault injection

A test bench that passes says the design matches the tests. It does not say the tests are good. To measure that, 66 copies of the logic were made, each with one deliberate fault of a kind a designer could make: a wrong sign, an off-by-one limit, a missing flag, a swapped register, a missing guard. A good test bench fails on every copy. A copy that passes shows something the test bench does not check.

**Table 20.4 Mutation test**

|  | **Revision 3 test bench** | **Revision 4 test bench** |
|---|---|---|
| **Checks in a run** | 60,401 | 71,598 |
| **Faults detected, of 66** | 36 | 66 |
| **Faults that passed unnoticed** | 30 | 0 |

Both columns use the logic as corrected in this revision. The list includes the two faults of Table 20.3 as they stood in revision 3. Full list with the first failing check for each fault: results/rtl_mutation.json.

**Table 20.5 The 30 faults that the revision 3 test bench let pass**

| **Area** | **Faults** | **What the fault does** |
|---|---|---|
| **Programming sequencer** | 7 | No pulse limit in the reset phase; no pulse limit in the set phase; reset pulses not counted in PITER; reset pulses repeated on devices that already passed verify; set amplitude not restarted after the reset phase; PITER not restarted by a new program command; pulse limit one step short. |
| **Reading, and cells with both devices in LRS** | 4 | A cell with both devices in LRS counted as +1; invalid cell not flagged during read-back; product read uses the set-verify reference; read-back of an invalid cell returns +1. |
| **Analog result and its SAT flag** | 5 | Positive clip limit off by one; negative clip limit off by one; SAT flag never set; SAT not cleared by GO; SAT not cleared by a read-back command. |
| **Flags and interrupt** | 5 | Interrupt ignores the enable trit; WERR not cleared by GO; interrupt held by WERR; DONE not cleared by GO; serial port: interrupt flag not reported. |
| **Guards: EN, BUSY, row index** | 6 | Negative row index accepted; register writes accepted while busy; program command works without EN; GO works without EN; read-back works without EN; MODE changed while busy. |
| **Trit code and serial port** | 3 | The unused trit code treated as −1; serial port: bit counter wraps on a long frame; serial port: a write frame also launches a read. |

Several of these would have mattered on silicon. Without a pulse limit, one stuck cell keeps the sequencer pulsing forever. A programming sequencer that keeps sending reset pulses to cells which have already passed their verify read, or that starts the set phase at the amplitude where the reset phase ended, defeats the purpose of pulse-and-verify and wears the cells. The old test bench saw only that the final state was right. The clipping of analog results and the guards on EN and BUSY had never been exercised at all.

**What was added.** A monitor inside the array model that watches every programming pulse; directed tests for each missed fault; and three exhaustive tests: every result value from −364 to +364 through the number conversion, every row index a tryte can hold, and the unused trit code in every register that takes trits. All 66 faults are now detected.

**What this does not show.** The mutation test covers single faults of the kinds listed. It does not prove the logic correct. A second simulator, formal proofs of the sequencers and timing analysis remained on the list (section 19.3). Timing analysis before layout and an equivalence proof followed in revision 4.1 (section 21).

### 20.5 Independent re-derivations

**Table 20.6 Results obtained a second time by a different method**

| **Result** | **First method** | **Second method** | **Agreement** |
|---|---|---|---|
| **Bitline currents of the tile** | Banded solver of the tile model | Every resistor entered separately into a full matrix, 8 configurations | Largest relative difference 5 × 10<sup>−11</sup> |
| **Analog RMS error, LRS3, published spread** | Monte Carlo on the tile model: 0.41 result steps | Closed-form sum of the device variances | 0.42 |
| **Wrong weights in digital mode** | Monte Carlo counts of Table 18.6: 4, 2 and 4,616 | Expected counts from the normal distribution | 6.7, 6.6 and 4,732 |
| **Set voltage of the cell in a 0.6 V/s ramp** | Python, ngspice and Gnucap implementations | A general stiff integrator (LSODA) on the equations as written in section 5 | 0.6695 V, within 0.26 mV |
| **Set voltage with the printed kinetic values** | Reference model: 0.25 V on the staircase | The same integrator, continuous ramp | 0.21 V. Far below the measured 0.65 to 0.75 V either way |
| **Read-disturb time of an HRS cell at 0.29 V** | Reference model with transistor: 200 s to a 10 % rise | The same integrator, cell alone | 183 s |
| **Cell currents at the published gap values** | Reference model | The current equation evaluated by hand | Equal to the last digit quoted |
| **Energy of Table 18.10** | Experiment script | Recomputed from the raw supply currents, the gate capacitance and the toggle counts | Equal: 0.19, 0.06 and 3.50 nJ |
| **Clock energy of the logic** | Toggle count on the netlist | Per flip-flop, against the library's own data | 30.5 fJ per flip-flop and cycle; plausible |
| **Transistor currents** | Gnucap build with the PDK's PSP 103 models | ngspice reference data in the PDK | 16 sweeps, largest difference 0.098 % |

The Monte Carlo counts of the third row are small numbers; 2 where 6.6 is expected happens by chance about once in 25 trials. What Table 18.6 is used for is the order of magnitude, and that agrees: a few wrong weights in 100,000 where that is predicted, and about 4 in 100 where that is predicted.

### 20.6 What the audit did not cover

- **It is not an independent review.** The audit was done by the same assistant that produced revision 3, with the same tools. Second methods and fault injection reduce that weakness. They do not remove it. A review by someone who has designed ReRAM circuits is worth more than another pass of this kind.

- **The device model is still unvalidated.** The audit checked that the model is implemented consistently and that its numbers are quoted correctly. It could not check the model against a device. Sections 18.2 to 18.6 stand or fall with the published data and the one-point kinetic fit.

- **The logic is tested, not proven.** No second simulator, no lint, no formal proof and no timing analysis were available in the sandbox at the time of the audit. Section 21 reports what revision 4.1 added.

- **The analog blocks around the logic do not exist yet.** The test bench talks to a behavioral array. The handshake it assumes, with inputs that change in step with the clock, becomes a requirement on the analog macro.

- **The energy estimate was checked for arithmetic and plausibility only.** Its method, toggle counts without wires or clock tree, is unchanged.

- **The read circuit is a first cut.** Its sizes were not optimized and it was not simulated over temperature. The audit re-read its numbers; it did not improve the circuit.

- **Sources.** Those listed in section 20.2 as read through a page reader or not read.

### 20.7 What changed in the repository

| **File** | **Change** |
|---|---|
| **rtl/tcim_core.sv, rtl/tcim_spi.sv** | Findings 1 to 4 of Table 20.3. Synthesis, the gate-level check and the energy estimate were run again. |
| **tb/tb_tcim.cc, tb/extra/spi_speed.cc** | Pulse monitor, two blocks of directed tests, exhaustive tests; 71,598 checks. A sweep of the serial clock speed. |
| **tb/mutation_test.py, tb/mutation_merge.py** | New. 66 faults. make mutation. |
| **tests/test_independent.py, tests/test_claims.py** | New. The re-derivations of Table 20.6 and the check of quoted numbers. make test. |
| **circuits/gnucap/pdk_check.py** | Comparison with the PDK's ngspice reference data added. |
| **model/cell_footprint.py, array/exp_pitch.py** | New. Cell area from the layout rules, and the effect of the row pitch on the analog error. |
| **circuits/gnucap/cell.py** | Gap passed between pulses limited to the model's range. |
| **docs/AUDIT.md, docs/STATUS.md, CLAUDE.md** | The audit report in short form; status and project memory updated. |

## 21 Changes after the audit (revision 4.1)

Revision 4.1 was made on 7 October 2026, one day after the audit. Two things prompted it. The folders of your earlier projects on the PC were read as context, and they hold tools and documents that the sandbox lacked. And the REBEL group's own tools were read again for the one REBEL-6 question that section 13 still had open, the two-bit code of a trit. The target stays REBEL-6 as published by the USN group. Nothing in TCIM0 was adapted to any other processor.

Three things changed in the design: a second trit code as a build option, the way a result is converted to balanced ternary, and the test bench. The rest of this section says what was found, what was changed and how each change was checked.

### 21.1 What the earlier project folders add

| **Found in the folders** | **Use for this project** |
|---|---|
| **OpenROAD-flow-scripts with the platforms ihp-sg13g2 and sky130hd, and your scripts that run it through Docker** | Place and route of the TCIM0 logic on the target process and on the alternative. The configuration is written (flow/orfs) and not yet run. The sky130_fd_sc_hd timing library of section 21.5 is the copy in this folder \[S39\]. |
| **An OpenLane run on SKY130 that completed with clean design-rule and layout-versus-schematic checks** | Shows that the route from netlist to checked layout works on this PC. It is a second route to a SKY130 layout. |
| **Log files of QuestaSim and Icarus Verilog runs** | Either is the second simulator that section 19.3 asks for. |
| **A Vivado project** | The tool for the FPGA run of Phase 4. |
| **Texts of two USN theses, by S. Bos and by V. Bodahl** | The Bos thesis gives the group's binary-coded-ternary codes \[S37\]. The Bodahl thesis describes REBEL-6 as it stood in 2024 and agrees with section 9 on word and instruction sizes. |

The folders were only read. The device shell that reaches the PC is a small Linux machine without Docker, so none of these tools was run for this revision. The status files in those folders were not used as evidence for anything in this document.

### 21.2 The trit code

The REBEL-6 documents define the machine in trits and say nothing about how a trit is carried on two binary wires \[S13\]. The group's tools do. The converter in the specification repository writes binary-coded ternary in one code only, which it calls BSD-PNX, and the Bos thesis proposes the same code and gives its reasons, among them that the pair 00 marks an uninitialized or faulty trit and that a ternary inverter becomes a swap of the two wires \[S13, S37\].

**Table 21.1 Two-bit codes of a trit**

| **Code** | **+1** | **0** | **−1** | **Illegal pair** |
|---|---|---|---|---|
| **BSD-PNX, the REBEL group's tools** | 10 | 11 | 01 | 00 |
| **Two's complement, TCIM0 until revision 4** | 01 | 00 | 11 | 10 |
| **The draft's code (section 14)** | 10 | 00 | 01 | 11 |

TCIM0 now builds with either of the first two. The default stays two's complement, so every result of sections 18 and 20 still describes the default build, and the definition TCIM_ENC_PNX selects BSD-PNX. In both an illegal pair is read as 0 and every trit the device produces is legal.

**A statement in the code was wrong.** The package file said that nothing outside it depends on the code values. That was not true: registers were reset to 0 bits and the unused trits of a read value were 0 bits, which is a field of illegal pairs in BSD-PNX. Registers now reset to zero trits and unused trits read as zero trits. In the default code a zero trit is 00, so the default logic is unchanged, which section 21.4 proves.

**Table 21.2 Verification in both codes**

|  | **Two's complement** | **BSD-PNX** |
|---|---|---|
| **Checks in a run of the test bench** | 81,966 | 81,966 |
| **Failures** | 0 | 0 |
| **Injected faults detected** | 69 of 69 | 75 of 75 |

The test bench is written in the two's-complement code. For the BSD-PNX build every data field is translated pair by pair on its way to and from the serial port, so the same 81,966 checks run on both. The BSD-PNX campaign has 6 more faults, which change nothing in the default code: registers reset to 0 bits, unused trits read as 0 bits, the pairs for +1 and −1 exchanged, and a zero trit produced as 00.

**Still open.** Which code REBEL-6 hardware uses is a question for the maintainers (section 13). The evidence is their tools, not a statement in the specification.

### 21.3 Static timing analysis

Section 18.8 gives the time of a product at a 100 MHz clock. Until this revision nothing had checked that the logic can run at 100 MHz. OpenSTA was built in the sandbox for that \[S38\]. The logic was synthesized a second time with the clock period given to the mapper, so that it sizes gates and inserts buffers, and each register-to-register path was timed with the delay tables of the foundry's library.

**What it found.** With a 10 ns clock the logic of revision 4 missed by 4.02 ns at the typical corner. One group of paths was responsible: 13.9 ns through 96 cells, from a register through the conversion of its value to balanced ternary and into the shift register of the serial port. The conversion was written as six divisions by three, one after the other. Every other register had at least 4.5 ns to spare.

**The change.** The conversion is now a table of 1,024 entries that is computed from the same arithmetic when the design is built. Measured alone between two registers, the chain of dividers takes 12.3 ns and 482 cells, and the table 1.7 ns and 392 cells. The function is the same for every input, which section 21.4 proves.

**Table 21.3 Timing before layout, clock period 10 ns**

| **Library and logic** | **Corner** | **Cells** | **Setup slack** | **Longest register-to-register path** | **Hold slack** |
|---|---|---|---|---|---|
| **IHP SG13G2, logic of revision 4** | typical, 1.20 V, 25 °C | 8,114 | **−4.02 ns** | 13.9 ns | +0.18 ns |
| **IHP SG13G2, present logic** | typical, 1.20 V, 25 °C | 7,951 | +4.67 ns | 3.3 ns | +0.18 ns |
| **IHP SG13G2, present logic** | slow, 1.08 V, 125 °C | 7,951 | +3.35 ns | 5.2 ns | +0.29 ns |
| **IHP SG13G2, present logic** | fast, 1.32 V, −40 °C | 7,951 | +5.47 ns | 2.2 ns | +0.12 ns |
| **IHP SG13G2, present logic, BSD-PNX** | typical, 1.20 V, 25 °C | 8,238 | +4.82 ns | 3.5 ns | +0.18 ns |
| **IHP SG13G2, present logic, BSD-PNX** | slow, 1.08 V, 125 °C | 8,238 | +3.59 ns | 5.4 ns | +0.29 ns |
| **IHP SG13G2, present logic, BSD-PNX** | fast, 1.32 V, −40 °C | 8,238 | +5.58 ns | 2.3 ns | +0.12 ns |
| **SkyWater SKY130, sky130_fd_sc_hd, present logic** | typical, 1.80 V, 25 °C | 8,014 | +2.62 ns | 5.1 ns | +0.33 ns |

OpenSTA 3.1.0. Slack is the time to spare on the worst path; a negative value means the clock is too fast. The worst path of the present logic starts at the array interface, where 30 % of the period is reserved for the analog macro, and ends in the SAT flag. The serial pins and the reset are asynchronous and are excluded. Cells are those of the netlist mapped for the clock period, which differs from the netlist of Table 18.9.

> **What this analysis does not include.** There are no wires in it: no wire capacitance and no wire resistance. The clock is ideal, with no tree and no skew. The reset pin drives all 844 flip-flops directly and exceeds the library's slew limit, and 431 nets on IHP exceed the library's default fan-out of 8; place and route repairs both. Every slack in Table 21.3 will be smaller after layout. For SKY130 only the typical library was at hand. The analysis shows that the logic has no path that is slow by construction. It does not show that the routed block meets 100 MHz.

### 21.4 Equivalence proofs

Revision 4 tested the logic. It did not prove anything about it. Revision 4.1 adds three proofs, run by make equiv with the SAT solver in Yosys.

| **Statement** | **Result** |
|---|---|
| **The conversion table equals its arithmetic definition** | Proven for all 1,024 input values, in both trit codes |
| **The present logic in the default code is the same sequential function as the logic of revision 4** | Proven by induction at 2,410 comparison points: every register and every output, matched by name. 0 unproven |
| **The plain-Verilog copy of the design for place and route equals the RTL** | Proven at 1,618 points. 0 unproven |

**The proof found a fault that no simulation had yet seen.** The first version of the table was read with a signed index, so every negative result would have been returned as 0. The second proof failed on exactly those twelve bits of the read data, before the test bench had been run on the new code. The index was corrected, the proof passed, and a fault of this kind is now one of the injected faults.

Because of the second proof, the fault campaign of the audit still applies to the present logic. The campaign was run again all the same (Table 21.2). The proof covers the default code only. The BSD-PNX build has no earlier logic to be compared with and rests on the test bench and its own fault campaign.

### 21.5 Numbers that changed

**Table 21.4 Revision 4 and revision 4.1**

|  | **Revision 4** | **Revision 4.1** |
|---|---|---|
| **Checks in a run of the test bench** | 71,598 | 81,966 |
| **Injected faults, all detected** | 66 | 69, and 75 in the BSD-PNX build |
| **TCIM0 with serial port, cells (Table 18.9)** | 7,737 | 7,560 |
| **TCIM0 with serial port, cell area** | 0.1116 mm<sup>2</sup> | 0.1108 mm<sup>2</sup> |
| **TCIM0 core, cells** | 7,234 | 7,146 |
| **Estimated energy of the logic per clock cycle** | 27.3 pJ | 27.8 pJ |
| **Estimated energy of the logic per product** | 3.43 nJ | 3.50 nJ |
| **Setup slack at 10 ns, typical corner, before layout** | −4.02 ns | +4.67 ns |

The test bench grew by the checks of Table 18.8 marked revision 4.1; almost all of the increase is one check on every write that the serial output stays silent. The three new faults are in the conversion table. The files of revision 4 are kept in results/rev4, and section 20 quotes them.

No device, cell, tile or read-path result changed. The energy estimate of the logic rose by about 2 %, which is inside the uncertainty stated under Table 18.9.

**On the second foundry's cells.** The same logic maps to 8,014 cells and 0.063 mm<sup>2</sup> in SKY130's sky130_fd_sc_hd library, against 0.114 mm<sup>2</sup> in IHP's, and has 2.6 ns to spare at 10 ns in the typical library before layout. The digital block is therefore not what would decide between the two processes. The cell, the read path and the programming voltages are, and they have not been simulated on SkyWater's models.

### 21.6 What is still open after this revision

- **Place and route.** Written for both processes, not run. It will give the real area, the wire delays and a clock tree, and the timing must then be analyzed again at the slow corner.

- **A second simulator, lint and formal proofs of the sequencers.** The proofs of section 21.4 compare two versions of the logic. They do not prove that either is right.

- **The trit code of REBEL-6 hardware**, to be confirmed by the maintainers.

- **Everything on the lists of sections 18.9, 19.3 and 20.6 that is not named above.** The device model is still a stand-in, the analog blocks around the logic do not exist yet, and no foundry data has been seen.

## 22 Changes of 8 and 9 October (revision 4.2)

Revision 4.2 was made on 8 and 9 October 2026. Docker was running on your PC, so the tools that the sandbox lacks could be used there: OpenROAD-flow-scripts for place and route and KLayout for design-rule checks. The sandbox gained Verilator, SymbiYosys and the SkyWater transistor models. Every open item of section 21.6 that needs no foundry data and no answer from someone else was worked on. The target stays REBEL-6 as published by the USN group.

Three kinds of work are reported. The first checks what was there: place and route on both processes, timing with the wires, a gate-level run of the routed netlist, lint, a second simulator and formal proofs (sections 22.1 to 22.3). The second is new design work: the transistor part of the array drawn and checked, first periphery circuits, the read path over temperature and supply, programming with device-to-device spread, and the port to SkyWater's models (sections 22.5 to 22.9). The third is one change to the logic, which the first measurement motivated: a digital product now reads only the rows with a non-zero input, back to back (section 22.4). Everything in section 22.1 to 22.3 was repeated after that change, and the numbers given are for the present logic.

### 22.1 Place and route on both processes

The plain-Verilog copy of the design (make orfs-src, proven equal to the RTL, section 22.3) was placed and routed with OpenROAD-flow-scripts in Docker on your PC, on IHP SG13G2 and on SkyWater SKY130 \[S39\]. The constraint file gives a 10 ns clock, treats the serial pins and the reset as asynchronous, and reserves 30 % of the period on each side of the array interface for the analog macro. After routing, the flow's design-rule check (KLayout) and, where the platform has one, its layout-versus-schematic check were run. The timing was then analyzed again in the sandbox with OpenSTA, the routed netlist and the parasitics the flow extracted (OpenRCX), at the three corners of the IHP library and with the one SKY130 library at hand (typical).

**Table 22.1 The routed TCIM0 block**

|  | **IHP SG13G2** | **SkyWater SKY130 (sky130_fd_sc_hd)** |
|---|---|---|
| **Standard cells (without fill)** | 12,033 | 12,385 |
| **Cell area** | 0.155 mm<sup>2</sup> | 0.086 mm<sup>2</sup> |
| **Block area (die), utilization** | 0.434 mm<sup>2</sup>, 40 % | 0.190 mm<sup>2</sup>, 46 % |
| **Flip-flops, clock buffers, buffers added for timing** | 837, 130, 1,452 | 837, 154, 637 |
| **Setup slack after routing** | +3.91 ns typical; **+1.90 ns slow**; +5.01 ns fast | +1.85 ns typical (only library at hand) |
| **Hold slack after routing** | +0.147 ns typical; +0.263 ns slow; **+0.079 ns fast** | +0.350 ns typical |
| **Clock skew** | 120 ps | 77 ps |
| **Design-rule check (flow's KLayout deck)** | 5 markers, all chip-level density rules (see below) | 0 violations |
| **Layout versus schematic** | not available in the flow's IHP platform | netlists match (KLayout) |

OpenROAD-flow-scripts image openroad/orfs:26Q4-71-g9b26ff8ff; OpenSTA 3.1.0 with the extracted parasitics (flow/orfs/post/sta_post.tcl). The parasitics were extracted once, at the flow's typical RC corner, and combined with each library corner. results/pnr.json, results/pnr/.

**The block meets the 10 ns clock after layout.** The smallest setup slack is 1.9 ns at the slow corner (before layout 3.3 ns), and every hold slack is positive. The fast-corner hold slack, 79 ps, is the tightest number in the table; it rests on parasitics extracted at the typical RC corner, so it should be checked again with a best-case extraction before a tape-out. The only limit the library flags is the root clock buffer, which drives 16 loads against a default fan-out limit of 8; that limit is a library default, not an electrical failure, and the clock tree was built and timed with it.

**The design-rule markers on IHP** are the global density of Metal2, Metal3 and Metal4 and the filler coverage of Metal2 and Metal3. Those rules are met at chip level, where the whole die is filled; a block of 0.43 mm<sup>2</sup> does not reach them on its own. The flow's IHP deck is a reduced set, so this is not a sign-off check; the full deck of the PDK was used on the array layout in section 22.7. On SKY130 the block is clean and its layout matches its netlist.

**Area.** Placed and routed, the logic needs 0.155 mm<sup>2</sup> of cells on IHP (0.112 mm<sup>2</sup> as synthesized for small area, Table 18.9) in a 0.43 mm<sup>2</sup> block at 40 % utilization. The increase over synthesis is mostly buffers that repair slew, fan-out and hold (1,452 of them) and the clock tree. The routed logic block is therefore about 21 times the area of the array tile of section 22.7, and its cells alone 8 times. The flow's power figure (14.8 mW on IHP) assumes a default switching activity and is not used.

The configuration of the first run, on the logic of revision 4.1, gave the same picture (slow-corner setup slack 1.83 ns, the same five density markers, SKY130 clean with matching netlists). Its files are kept in results/rev41/.

### 22.2 The routed netlist runs the full test bench

Place and route rewrites the netlist: it resizes gates, adds buffers and builds the clock tree. To check that the routed logic still computes the right thing, the routed netlist of each process was simulated with the complete test bench of section 18.7. Every standard cell is modelled from the logic function its own Liberty file states, and the result runs on Verilator with the same C++ test bench as the RTL (flow/orfs/post/gls.sh, make gls). This is a check of the function, without delays; the delays are what Table 22.1 checks.

**Table 22.2 Gate-level runs of the complete test bench**

| **Netlist** | **Checks** | **Failures** | **Result** |
|---|---|---|---|
| **IHP SG13G2, routed netlist** | 82,512 | 0 | passed |
| **SKY130, routed netlist** | 82,512 | 0 | passed |
| **IHP SG13G2, routed netlist with one XNOR gate replaced by an XOR** | 82,512 | 159 | detected |

The last row shows that the gate-level run can fail: one gate of 12,033 changed, and the test bench reports it. The equivalence check that the flow itself runs after layout found no outputs to compare (its log reports the comparison as vacuously equivalent), so it proves nothing and is not quoted.

### 22.3 Lint, a second simulator and formal proofs

Section 21.6 listed these as missing. All three are now part of the repository.

- **Lint** (make lint): Verilator 5.040 with all warnings enabled, in both trit codes: 0 warnings, 0 errors. Two signals carry a written waiver: an unused synchronizer stage of the chip select and an unused top bit of the serial input register. The first lint run also found a signed-width mismatch in the row-index check and two width warnings in the function that builds the conversion table; both were fixed without changing the logic (the proofs of section 21.4 cover that function).

- **A second simulator** (make rtl-verilator): the same C++ test bench runs on a Verilator model of the RTL through a small adapter (tb/verilator/tcim_top.h). 82,512 checks, 0 failures, in both codes, with the same number of array operations and clock cycles as the CXXRTL run. The two simulators share no code below the test bench.

- **Formal proofs** (make formal, SymbiYosys, unbounded proofs with the PDR engine of ABC). The properties are written into the RTL and hold for every sequence of bus accesses and array answers after a reset:

| **Property** | **Result** |
|---|---|
| Serial port: never a read and a write strobe in the same cycle; the bit counter stops at the end of a frame; a write strobe only in a write frame, a read strobe only in a read frame | proven |
| The array is never asked about a row that does not exist | proven, both codes |
| Pulses and verify reads happen only inside a program command, on its row, with PDATA unchanged; every pulse selects at least one device and stays inside the 21 amplitude steps | proven, both codes |
| A set pulse reaches only devices whose weight needs LRS, a reset pulse only devices that must be HRS; no reset pulse after a set pulse; at most 42 pulses per command; products and read-back never pulse | proven, both codes |
| Digital product: every result stays within ±72; exactly the rows with a non-zero input are read, each once, in increasing order, and the product ends only when all of them are read (revision 4.2) | proven, both codes |
| Every accepted command either runs (BUSY) or has already ended with DONE, and every command that ends sets DONE (revision 4.2) | proven, both codes |
| The interrupt line equals IE and DONE | proven, both codes |
| Progress: with an array that answers at once, every command ends within 200 clock cycles | proven |

A proof that cannot fail proves nothing, so 9 faults were injected one at a time into copies of the RTL (formal/check_faults.py): 9 of 9 made the proof that should catch them fail. **This check found weak properties twice.** The first version of the new product property was written in terms of the sequencer's own mask of non-zero rows, so a fault in that mask (every row marked non-zero) could not violate it: the proof would have passed on broken logic. The property now decodes the input registers itself, and the fault, together with a second one (rows with input −1 skipped), makes it fail. The second case, a DONE property that could not see a command that never started, is described in section 22.4. To make the proofs possible, out-of-range bit selects are given free values, which is the conservative choice.

**The equivalence proofs of section 21.4 were run again.** The conversion table still equals its definition in both codes, and the plain-Verilog copy used for place and route is proven equal to the present RTL at 1,697 points with 0 unproven. The comparison with the logic of revision 4.1 is now expected to fail, because the product sequencer was changed on purpose (section 22.4); it is run to show where the two differ.

### 22.4 One change to the logic: a row per request, back to back

Section 18.8 found that the clocked logic, not the array, dominates the energy of a digital product, and named two remedies: clock gating and one clock cycle per row. The second was done.

**Before.** The product sequencer visited all 72 rows, one clock cycle each, and for a row with a non-zero input it raised the request, waited for the answer and lowered the request again. A product took 122.7 clock cycles with an array that answers in one cycle, for 47.9 row reads on average.

**Now.** The first row with a non-zero input is found in the same cycle as GO, and when the answer for a row arrives, the next such row is put on the row lines in the same clock edge while the request stays high. Rows with input 0 cost no cycle, and the macro is never idle between two reads. An input vector of zeros finishes at once with a result of 0. The array protocol is the one the programming sequencer already used: a request held high after an answer is a new request.

**Table 22.3 Effect of the change**

|  | **Revision 4.1** | **Revision 4.2** |
|---|---|---|
| **Clock cycles per digital product (array answering in one cycle)** | 122.7 | 49.7 |
| **Estimated energy of the logic per cycle** | 27.8 pJ | 29.2 pJ |
| **Estimated energy of the logic per product** | 3.50 nJ | **1.54 nJ** |
| **TCIM0 with serial port, cells (synthesized for area)** | 7,560 | 7,892 |
| **Setup slack before layout, slow corner** | +3.35 ns | +3.34 ns |
| **Longest register-to-register path before layout, slow corner** | 5.2 ns | 6.5 ns (the search for the next non-zero row) |
| **Checks in a run of the test bench** | 81,966 | 82,512 |
| **Injected faults detected** | 69 of 69; BSD-PNX 75 of 75 | 74 of 74; BSD-PNX 80 of 80 |

Energy: zero-delay toggle count of the netlist synthesized for small area, as in Table 18.9, with the same uncertainty (no clock tree, no wires; expect 1.5 to 3 times more). The check count fell although checks were added: every poll of the status register is a serial transfer with its own checks, and faster products need fewer polls.

**How the change was verified.** Both test benches (CXXRTL and Verilator) and both codes pass. The test bench gained checks on every digital product of its main section: the number of row reads equals the number of non-zero inputs, and the request line never drops between two reads. Five faults specific to the new sequencer were added to the campaign (the next row taken as the next row rather than the next non-zero row, the search restarting at the row just read, the request dropped between rows, a zero input vector never finishing, the input of the wrong row used for the sign), and the existing product faults were rewritten for the new code. **The campaign found a gap in the test bench**: with the fault that lets an all-zero input vector end without setting DONE, the test bench still passed, because it waited for BUSY to fall and never looked at DONE, and the result of an all-zero product is 0 either way. The test bench now checks DONE at the end of every product. **The formal fault check then found the same gap in the first DONE property**: "every command that ends sets DONE" cannot see this fault, because the faulty sequencer never raises BUSY, so no command is seen to end. A second property now requires that every accepted command either runs or has already ended with DONE, and the fault makes it fail. The fault is detected by the test bench and by the proofs; every fault of both campaigns is now detected. The new formal property of section 22.3 states the sequencing completely: only rows with a non-zero input, each once, in order, and all of them before the end. The comparison with revision 4.1 leaves 628 of 2,392 points unproven, in 26 signals (results/equiv_unproven.txt): the sequencer state, the signals to the array, and the registers whose updates follow the state or BUSY (accumulator, status flags, pulse count and amplitude, the masks of devices still to program, and PDATA, which can only be written while BUSY is low). That is expected, because a product now ends earlier and everything that waits for BUSY moves in time. The serial port, the input, row and configuration registers and the serial output are proven unchanged. The changed behaviour itself rests on the test benches, the fault campaign and the proofs above, not on this comparison. Place and route, the timing after layout and the gate-level runs of sections 22.1 and 22.2 are for the changed logic.

**Clock gating was not done.** It needs a clock-gate cell from each library instantiated in the RTL, simulation models of those cells for the gate-level run (the Liberty files of both libraries give their gate cells no logic function), a multi-clock setup for the formal proofs, and a clock-tree check after layout. None of that is difficult, but it is a change to the clock network that this revision could not also verify on silicon-relevant terms. It is worth doing: 69 % of the estimated energy per cycle is the clock of ungated flip-flops, and if every flip-flop were clocked only in the cycles in which it takes a new value, the estimate would fall from 1.54 to 0.55 nJ per product. That figure is a lower bound (no gating cells, no clock tree), measured on the same simulation (synth/power_estimate.py). It is the first item of section 22.12.

### 22.5 Read path over temperature and supply

The first-cut sense amplifier of section 18.6 was simulated at five process corners, at −40, 27, 85 and 125 °C, and at 1.08, 1.20 and 1.32 V (circuits/gnucap/exp_sense_env.py, 60 cases). The trip current stays between **24.24 and 24.86 µA**. Against the published six-sigma device tails (HRS 14 µA, LRS3 34.3 µA) the smallest margin in any case is 9.44 µA. A mean HRS cell holds the bit line at 0.280 to 0.331 V instead of 0.2 V, which is the read-disturb concern of section 18.6 over the whole range. Transient reads of the worst-case cells at the hot slow and cold fast extremes (8 cases) all give the right answer, LRS within 3.75 ns, and the bit line never exceeds 0.360 V.

What varies is the transistors. The 25 µA reference and the 0.2 V reference are still ideal sources, and the ReRAM model has no temperature term in its conduction, so these are margins of the amplifier, not of the cell.

### 22.6 First periphery circuits

Three circuits that programming needs were drawn as transistor netlists with IHP's 3.3 V devices and simulated at five corners and three temperatures (circuits/gnucap/periphery.py). Sizes are first guesses that pass; nothing is optimized.

**Table 22.4 First-cut periphery, worst case over 15 corner and temperature combinations**

| **Circuit** | **What it is** | **Worst case** |
|---|---|---|
| **Level shifter 1.2 V to 3.3 V** | Cross-coupled thick-oxide pair with thick-oxide pull-downs and output inverter, 20 fF load | switches in every case; delay ≤ 2.74 ns; static current ≤ 0.61 nA |
| **Word-line driver** | Thick-oxide inverter on a 1.7, 2.7 or 3.3 V rail driving one row: 48 select gates (454 fF) on the drawn GatPoly word line, 509 squares at 7.8 Ω/sq, up to 5.2 kΩ at 125 °C | far end of the line settles to 90 % in ≤ 4.1 ns (rise 3.5 ns, fall 2.5 ns); reaches the full rail |
| **Column switch for programming** | Thick-oxide transmission gate (NMOS 20 µm, PMOS 40 µm) carrying one device's 0.6 mA, 0.5 to 3.0 V | drops at most 190 mV (ss 125 C) |

**What follows from it.** A word line of the full tile settles in about 4 ns at the slow hot corner even through 5.2 kΩ of salicided poly, so one row read per 10 ns clock cycle (section 22.4) is consistent with the word line; the sense amplifier adds up to 3.8 ns. Strapping the word line in metal is not needed for that. The column switch loses up to 0.19 V of a programming pulse; the verify loop absorbs this, but it shifts every amplitude step, so the switch should be sized up or the drop included in the amplitude ladder. The static current of the level shifter is leakage only (the sum of the three transistors that are off in each state). Not designed yet: the programming-voltage generator, the references, and the analog-mode clamp and converter.

### 22.7 Layout of the array transistors, checked with the full rule deck

Section 18.3 bounded the cell area by counting layout rules. The transistor part of the array is now drawn (layout/cell_2t2r.py): a block of 4 rows by 2 column pairs, 16 select transistors of 4.5/0.45 µm in thick oxide, two rows mirrored about a shared source, 13 contacts per terminal, the word line in GatPoly contacted at its end, the source line in Metal2 along each column pair with 4 vias per source strip (1.6 mA against a worst case of 1.2 mA), the drain taken up through Metal1, Via1, Metal2 and Via2 to the bit line in Metal3, and substrate ties for the latch-up rule.

It was checked with the PDK's own complete KLayout rule deck (main deck and the extended set, density excluded because a block this small cannot meet fill density; KLayout 0.30.12 in the place-and-route image on your PC). **The first run failed one rule the rule count had missed**: Gat.b1 requires 0.25 µm between thick-oxide gates of different transistors, and the transistors of a row were 0.21 µm apart (the active-area spacing). With 0.25 µm the block is clean: pass, no violations.

**Table 22.5 Array pitch: rule count and drawn layout**

|  | **Rule count (section 18.3)** | **Drawn and checked** |
|---|---|---|
| **Row pitch (along the bit line)** | 1.085 µm | 1.085 µm |
| **Device pitch (along the word line)** | 4.71 µm | 4.75 µm |
| **Area per device** | 5.11 µm<sup>2</sup> | 5.15 µm<sup>2</sup> |
| **72 × 24 tile** | 0.0177 mm<sup>2</sup> (transistors only) | 0.0206 mm<sup>2</sup> (229 × 90 µm, with word-line contacts and three tie rows) |

> **What the drawing does not contain.** The open PDK has no MEMRES layers, so the ReRAM element is not drawn: a stack of three Via2 on each drain marks where it goes, and the metal levels it actually sits between are a question for IHP (section 13). The foundry's cell replaces that part. The periphery and fill are not drawn. The 0.02 mm<sup>2</sup> used in the plan for the tile stands.

### 22.8 Programming with device-to-device spread

The programming scheme of the RTL (reset phase, then set phase, 21 amplitude steps of 0.1 V from 0.5 V each, 1 µs pulses, a verify read after each pulse) was simulated on many devices that differ from each other (model/program_mc.py). The device model is the re-fitted reference model; the transistor is IHP's 3.3 V NMOS, 4.5 µm, at three corners. Reset uses a 2.7 V gate and stops at 6 µA; set uses a 1.7 V gate and stops at 42 µA.

> **The spread is assumed.** No device-to-device statistics of the switching kinetics are published for this device; only the read currents after verify are (Table 4.1). Each simulated device draws its own rate prefactor v<sub>0</sub> (log-normal), activation energy E<sub>a</sub> (normal) and conduction prefactor I<sub>0</sub> (log-normal). "1×" means a standard deviation of 0.5 in ln v<sub>0</sub>, 0.03 eV in E<sub>a</sub> and 0.10 in ln I<sub>0</sub>; "2×" doubles them. 0.03 eV changes the switching rate by a factor of about 3. These are scenarios for finding the weak point, not predictions.

**Table 22.6 Program cycles with assumed spread, 100 devices per case**

| **Corner, spread** | **Both phases verified** | **Reset not reached in 21 pulses** | **Set not reached** | **Pulses per cycle, max** | **Verified LRS read current** |
|---|---|---|---|---|---|
| **tt, no spread** | 1 of 1 | 0 | 0 | 19 (mean 19.0) | 44.2–44.2 µA |
| **tt, 1x** | 100 of 100 | 0 | 0 | 28 (mean 19.0) | 42.1–51.5 µA |
| **tt, 2x** | 93 of 100 | 7 | 0 | 40 (mean 19.4) | 42.0–54.8 µA |
| **ss, no spread** | 1 of 1 | 0 | 0 | 21 (mean 21.0) | 42.7–42.7 µA |
| **ss, 1x** | 99 of 100 | 1 | 0 | 38 (mean 21.7) | 42.0–46.6 µA |
| **ss, 2x** | 88 of 100 | 12 | 0 | 42 (mean 21.7) | 42.0–52.2 µA |
| **ff, no spread** | 1 of 1 | 0 | 0 | 19 (mean 19.0) | 50.3–50.3 µA |
| **ff, 1x** | 100 of 100 | 0 | 0 | 26 (mean 18.3) | 42.0–57.4 µA |
| **ff, 2x** | 93 of 100 | 7 | 0 | 35 (mean 18.4) | 42.1–59.0 µA |

**Finding: reset is the weak phase.** Set always finished, at most at 2.0 V. Reset ran out of the 21-step ladder for 1 of 100 devices at the slow corner with 1× spread (none at the other corners) and for 7 to 12 of 100 with 2× spread. The sequencer handles that correctly (it stops, sets WERR and reports the pulse count, which the formal proofs and the test bench cover), but it is a lost row. Every device that verified ended above the 25 µA read reference with at least 17.0 µA to spare, so the read margins of section 18.6 hold for the devices that verify.

**Table 22.7 Reset phase alone on the same devices: devices not reset within 21 pulses**

| **Corner, spread** | **Gate 2.7 V** | **Gate 3.0 V** | **Gate 3.3 V** |
|---|---|---|---|
| **tt, 1x** | 0 (max 16 pulses) | 0 (max 11 pulses) | 0 (max 10 pulses) |
| **tt, 2x** | 7 (max 21 pulses) | 0 (max 15 pulses) | 0 (max 12 pulses) |
| **ss, 1x** | 1 (max 21 pulses) | 0 (max 12 pulses) | 0 (max 10 pulses) |
| **ss, 2x** | 12 (max 21 pulses) | 0 (max 19 pulses) | 0 (max 13 pulses) |

**Remedy.** A higher reset gate voltage lets the select transistor carry the reset current at a lower drop, so the device sees more of the pulse. The word-line driver of section 22.6 already has a 3.3 V rail. The plan changes from a 2.7 V reset gate (the published value for IHP's 0.25 µm arrays) to the highest gate voltage the thick-oxide device allows, to be confirmed with the foundry's model and measured devices.

The model's reset is abrupt: it ends at the 1.8 nm limit, 0.5 to 5.8 µA here, while measured arrays stop near the 6 µA target with a mean of 2.85 µA. The HRS read currents of this study are therefore model artifacts and are not quoted. A gradual reset cannot be fitted without per-pulse reset data, which are not published for this device.

### 22.9 The cell on SkyWater SKY130 models

Section 21.5 noted that the cell had not been simulated on SkyWater's models. It now is (model/sky130_port.py). Two questions were asked.

**Is SkyWater's ReRAM model the same as ours?** SkyWater's Verilog-A model (library sky130_fd_pr_reram, version 2.0.3) was transcribed line by line, with its own update order, and compared with our reference model at the same parameters. The read currents are exactly equal, and the gap after 1 µs constant-voltage pulses agrees within 1.0 pm when SkyWater's update is run with a small time step. With the 1 ns step its own code permits, it overshoots near a switching threshold (at −1.6 V it resets fully where the converged solution stops at 1.30 nm). That is a property of their discretization, not of the equations.

**Table 22.8 1T1R with SkyWater's 5 V NMOS (nfet_g5v0d10v5) at SkyWater's published programming conditions, 1 µs**

| **Corner, transistor width** | **Transistor current at 3.3 V gate, 0.2 V** | **After set (BL 2.4 V, WL 1.7 V): gap, read** | **Reset at WL 2.5 V, SL 2.6 V?** | **Word-line voltage the model needs to reset** |
|---|---|---|---|---|
| **tt, W = 0.42 µm** | 39 µA | 0.79 nm, 1.6 µA | no | 3.25 V |
| **tt, W = 1.0 µm** | 89 µA | 0.50 nm, 4.5 µA | no | 3.25 V |
| **tt, W = 2.0 µm** | 178 µA | 0.23 nm, 11.8 µA | no | 3.25 V |
| **tt, W = 4.0 µm** | 361 µA | 0.10 nm, 19.5 µA | no | 3.00 V |
| **ss, W = 0.42 µm** | 27 µA | 0.98 nm, 0.8 µA | no | 3.25 V |
| **ss, W = 1.0 µm** | 74 µA | 0.62 nm, 3.0 µA | no | 3.25 V |
| **ss, W = 2.0 µm** | 155 µA | 0.33 nm, 8.3 µA | no | 3.25 V |
| **ss, W = 4.0 µm** | 321 µA | 0.10 nm, 19.3 µA | no | 3.00 V |
| **ff, W = 0.42 µm** | 50 µA | 0.65 nm, 2.6 µA | no | 3.25 V |
| **ff, W = 1.0 µm** | 105 µA | 0.41 nm, 6.4 µA | no | 3.25 V |
| **ff, W = 2.0 µm** | 202 µA | 0.14 nm, 16.1 µA | no | 3.00 V |
| **ff, W = 4.0 µm** | 403 µA | 0.10 nm, 19.6 µA | no | 2.75 V |

**What the port shows.** Set works at SkyWater's published conditions, but the read current after set depends strongly on the transistor width, and the width of SkyWater's 1T1R test structure is not published. **Reset does not work at SkyWater's published conditions in the model at any width tried**: the transistor, used as a source follower, cannot pass the reset current at a 2.5 V gate. The model needs about 2.75 to 3.25 V on the word line. Either the published conditions refer to something not in the open files (a wider device, a longer pulse, a different bias), or SkyWater's model does not describe its reset well. This is a question for ChipFoundry (section 13, docs/QUESTIONS.md), and it is the same weakness section 22.8 found on IHP's transistor.

### 22.10 Questions drafted

Three messages are ready to send in docs/QUESTIONS.md: to IHP (how to obtain the MEMRES kit and its Verilog-A model, layer stack, programming voltages, measured statistics, who may order, 2027 dates), to ChipFoundry (next ReRAM shuttle, current sign-off files, forming voltage, measured statistics, and now the reset conditions of section 22.9), and to the REBEL-6 maintainers (slot 11 and interrupt 7, the BSD-PNX code on hardware, access to the current R2R executor with TMAC.T and memory-mapped devices, encoding space). None has been sent.

### 22.11 Numbers that changed

No device, cell, tile or read-path result of sections 18.2 to 18.6 changed; sections 22.5 to 22.9 add to them. The logic numbers that changed are in Table 22.3. The rule-count area of section 18.3 is superseded by the drawn pitch of Table 22.5 (4.75 µm instead of 4.71 µm along the word line). Sections 1 to 21 keep the numbers of revision 4.1, and the files they quote are kept in results/rev41 and results/rev4.

### 22.12 What is still open

- **Clock gating** of the logic, with its cell models, proofs and clock-tree check (section 22.4).

- **Reset gate voltage and the reset ladder**: decide with the foundry's model; consider a longer ladder or a second ladder at a higher gate voltage for devices that do not reset (section 22.8).

- **Answers from outside**: the MEMRES kit with its model and cell, measured statistics, the SkyWater reset conditions, REBEL-6 slot, interrupt, trit code and executor (section 22.10).

- **Circuits**: programming-voltage generation, current and voltage references, the analog-mode clamp and converter, the test multiplexer; the column switch sized for less drop (section 22.6).

- **Layout**: the ReRAM element once its layers are known, the periphery, and a full-chip assembly with fill, which also clears the density markers of Table 22.1.

- **REBEL-6**: attaching a TCIM0 model to the R2R executor needs a version with TMAC.T and memory-mapped devices, which the public repository does not have (section 22.10).

- **Timing**: a best-case parasitic extraction for the fast-corner hold check, and the SKY130 slow and fast libraries.

## Appendix A Calculations

Inputs are the read-current statistics of Table 4.1 and the IHP process values of Table 6.3 and section 3. The symbols μ and σ are the mean and standard deviation of the read current at 0.2 V.

| **Quantity** | **Formula** | **Result** |
|---|---|---|
| **Separation of two levels** | z = (μ<sub>high</sub> − μ<sub>low</sub>) / (σ<sub>high</sub> + σ<sub>low</sub>) | HRS–LRS1 4.00; LRS1–LRS2 3.63; LRS2–LRS3 3.99; LRS1–LRS3 7.27; HRS–LRS3 11.98 |
| **Misread probability at the equal-z threshold** | ½ erfc(z / √2) | 1.35 × 10<sup>−3</sup> at z = 3; 3.2 × 10<sup>−5</sup> at z = 4.0 |
| **Result step of a 2T2R weight** | Δ = μ<sub>LRS</sub> − μ<sub>HRS</sub> | 15.23 µA with LRS1; 40.74 µA with LRS3 |
| **Spread of one weight** | ±1: √(σ<sub>LRS</sub><sup>2</sup> + σ<sub>HRS</sub><sup>2</sup>). 0: √2 σ<sub>HRS</sub> | 2.70 µA (LRS1), 2.41 µA (LRS3); 2.62 µA for zero |
| **Spread of a sum of N weights, in steps** | √N × spread / Δ | Table 6.1 |
| **Chance the rounded result is wrong** | erfc(0.5 / (√2 × spread in steps)) | Table 6.1 |
| **Time-to-threshold code for result k** | floor(C V<sub>ref</sub> / (k Δ) / 1 ns) | 15 distinct codes for k = 1 to 64 in the best case |
| **Bitline voltage error** | Nodal solution of a resistive ladder: segment resistance = sheet resistance × pitch / width; each selected cell is a conductance to the 0.2 V rail | Table 6.2 |
| **Metal1 current density limit** | 1 mA/µm ÷ 0.42 µm | 2.4 × 10<sup>5</sup> A/cm<sup>2</sup> |
| **Pads on a square die** | 4 × floor((side − 360 µm) / 80 µm) | 24 at 0.8 mm<sup>2</sup>; 32 at 1.0 mm<sup>2</sup>; 40 at 1.5 mm<sup>2</sup>; 64 needs 2.69 mm<sup>2</sup> |
| **Price with MEMRES** | 7,300 A + 2,500 + 600 A, in euros, A in mm<sup>2</sup> | €8,820 at 0.8; €10,400 at 1.0; €14,350 at 1.5; €23,750 at 2.69 |
| **Bus width in the draft** | 1 + 1 + 12 + 64 + 64 + 5 × 2 | 152 wires |
| **Result range of N ternary products** | 2N + 1 values | 129 for N = 64; 145 for N = 72; both fit 5 trits (243) |
| **Oxide stability per oxygen atom** | ΔH per formula unit ÷ oxygen atoms | Al<sub>2</sub>O<sub>3</sub> −558.6; HfO<sub>2</sub> −572.4; TiO<sub>2</sub> −472.0 kJ/mol |
