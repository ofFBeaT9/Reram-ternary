# Paper plan (8 November 2026)

**Working title.** One of Three: A Constant-Conductance Ternary ReRAM Cell Against Weight-Sparsity Leakage in
Compute-in-Memory (alternative: What Logic Cannot Hide: Side Channels of a Ternary ReRAM CIM Tile).

**Claim (one sentence).** In a digital-mode ternary ReRAM compute-in-memory tile, logic countermeasures close the timing
and accumulator leaks, but the 2T2R ternary encoding leaks each row's weight sparsity through the array read current; a
one-of-three (3T3R) cell, which holds exactly one low-resistance device per weight, removes that leak by construction at
1.56× cell area, shown on transistor-level read currents of a drawn, signed-off SKY130 design.

**Why it is new (LITERATURE.md, section 7).** Closest: Goudzwaard (TU Delft MSc, 2025: ternary ReRAM weight
extraction via power, no cell countermeasure); Sapui and Tahoori (ASP-DAC 2025: dual-rail ReRAM CAM, binary);
Laborieux et al. (2020: the 2T2R ternary encoding, no security); Micron US 11,811,424 (fixed-weight ternary codewords,
reliability). No one-of-three ReRAM CIM cell for side-channel resistance was found (web search; IEEE Xplore and patent
search still to do). The logic countermeasures are known or partly known (Leaky Nets, Hua DAC 2018, "Make it Darker"
DATE 2026) and are presented as the baseline that cannot close the cell-level leak.

**Venue.** IACR TCHES 2027 issue 3 (deadline 15 January 2027) if the evidence below holds; otherwise IEEE TCAD or
JETCAS (journal), with HOST 2028 as the conference fallback. HOST 2027 (paper 15 November 2026) is too close.

**Structure (TCHES-style, ~20 pages).**
1. Introduction: CIM accelerators hold model IP in the array; zero weights are common in ternary nets; contributions.
2. Background and threat model: ternary 2T2R ReRAM CIM, digital mode; attacker with physical access, a supply-current
   probe, chosen or known inputs, profiling on a second device; no fault injection.
3. The TCIM0 tile and its open SKY130 test chip (artifact): array, periphery, controller, sign-off (precheck 14/14).
4. Leakage study, layer by layer (behavioural model, then transistor level):
   - timing: zero-skipping (|t| 580.75) -> fixed latency + LFSR start row;
   - accumulators: bit flips around zero (19.55) -> random offset (3.59);
   - cell: 2T2R sparsity in the read current (behavioural 14.24; transistor level, this study) -> no logic fix.
5. The one-of-three cell: encoding argument, layout (5.6 × 3.0 µm), periphery (macro 1566.3 × 1950.5 µm vs 1436.7 ×
   1391.7 µm), programming through the drawn drivers (same pulse counts as 2T2R, no disturb), logic support
   (TCIM_CELL_1OF3; tests, proofs, mutation), invalid-code detection.
6. Evaluation: transistor-level TVLA 2T2R vs 3T3R vs 4T4R; LRS-spread sweep; a sparsity-recovery attack (correlation
   0.9 on 2T2R, about 0 on 3T3R); noise sensitivity; programming leak (unchanged); residual: sense-register switching.
7. Discussion: cost (1.5× devices per weight, 24 more bit-line slices), alternatives (row current compensation, dual-rail,
   current flattening, masking), what remains (programming profile, deterministic LFSR, LOCK after reset), silicon plan.
8. Related work. 9. Conclusion. Artifact appendix: repository, commands, result files.

**Evidence status.** Done in this study: transistor-level read waveforms with mismatch (sa_transient), circuit-level
TVLA, attack, 3T3R programming, 3T3R macro DRC/LVS, logic, tests, proofs. Still missing for a strong submission:
silicon (the decisive one), an IEEE Xplore / patent search for 3T3R ternary cells, reading the closest papers in full,
higher-order analysis of the offset, a network-level accuracy and energy table with the 3T3R cost.
