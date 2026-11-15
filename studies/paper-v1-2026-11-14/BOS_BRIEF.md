# Brief for the meeting with Steven Bos (USN), week of 16 November 2026

Prepared 14 November 2026. Numbers are from `results/` in the repository `Reram-ternary`; leakage numbers are from
`results/security/v1/` and are statements about a model, not about silicon.

## 1. What to say in the first two minutes

- TCIM0 is a 72 × 24 ternary ReRAM compute-in-memory tile for REBEL-6: one product replaces 72 TMAC.T instructions, and the
  digital read is exact whenever every device is read correctly.
- The 2T2R test chip is drawn on SKY130 with SkyWater's ReRAM layer and passes ChipFoundry's precheck (14 of 14). Revision 4.9
  of the logic is locked at reset and unlocks only by erasing the array.
- Nothing is measured. No shuttle has confirmed the ReRAM layer.
- A paper is drafted: the 2T2R ternary code leaks each row's zero count in a single read, and a one-of-three cell fixes that
  only if its bit lines are balanced.

## 2. What is new this week

| Finding | Number |
|---|---|
| 2T2R: profiled zero-count attack | correlation 0.80 from 1 read; 99.2 % of rows exact from 4,096 reads per row |
| One-of-three as drawn | silent to a few hundred reads; 0.56 at 65,536 reads; 0.90 at 1,048,576 reads (about 1 minute of array time) |
| Cause | the Z bit line's capacitance differs from P and N (10.7 fF against 15.5 and 14.7 fF over 72 rows); this is the same on every chip |
| Sense-amplifier rotation | does not help against that (0.93 at 1,048,576 reads); it only removes the chip-specific amplifier term |
| Balanced bit lines (for instance transposed) | attack at the guessing rate up to 16,777,216 reads per row; information bound 0 bits per row with rotation |
| Amplifier mismatch | 27 nA sd per amplifier on an LRS read; 120 nA if the shared reference generator's mismatch is counted per amplifier, as the earlier draft did |
| Fault found in the earlier study | the mismatch seed had no effect in ngspice 42, so every (sample, conductance) pair was a different amplifier; the 8 November position numbers (26.32, 2.70) are withdrawn |
| Cost of one-of-three | 1.56× cell area, 1.53× macro area, 1.50× read charge at one third zeros |
| Side benefit | 9 of 9 single-device flips are detected (2T2R: 2 of 6); silent weight errors fall from 1.3e-4 to 2e-8 at a flip probability of 1e-4 |

The model changed too: waveforms now follow the controller's read sequence (precharge, read, recharge), 400 independent
amplifier samples replace 40, and the extracted bit-line capacitances are in. The numbers of the 8 November draft are superseded.

## 3. What is new in the literature sense, stated plainly

Not new, and cited:

- one low-resistance element among three as a ternary state: Rambus, US 9,704,576 (2017), for TCAM, no security purpose;
- random swapping of two sense amplifiers to hide their mismatch: TSMC, US 10,269,420 and family;
- capacitance imbalance of dual-rail bit lines as a power-analysis leak, and crossover against it: Infineon, US 7,161,869 (2007);
- dual-rail ReRAM storage against collision attacks (Sapui and Tahoori, ASP-DAC 2025); a balanced MRAM cell (S-ALSA, arXiv 2609.33619).

New, as far as two searches show (IEEE Xplore not searched directly):

- the analysis for ternary CIM weights, where the leaking value is the zero and the leak is sparsity;
- the separation into four layers (count, amplifier, bit line, device) with sizes from a drawn, open design;
- the result that count balance alone gives the count back through the layout, and that rotation without balance does not help;
- the artifact: an open tile, layouts, decks and scripts from which every number is generated.

Honest ceiling: without silicon this is a simulation paper (DATE, HOST, ASP-DAC, IEEE JETCAS or TCAS-I level). A measured
2T2R-against-one-of-three comparison would be a stronger paper (TCHES level).

## 4. What to ask him

1. **REBEL-6 interface.** Slot 11 and interrupt source 7 for TCIM0; the wire code of a trit (BSD-PNX or two's complement, both
   builds are verified); access to the current executor with TMAC.T and memory-mapped devices, for a recorded co-simulation.
2. **Wording.** How REBEL-6 may be described in the paper, and whether he wants to see the text before a preprint.
3. **Authorship and affiliation.** Whether he or his group would join as co-authors, and under which condition (a review of
   the REBEL-6 parts, measurements at USN).
4. **Measurement.** Whether USN's bench can take supply-current traces (a current probe or shunt amplifier with a bandwidth of
   20 MHz or more, an oscilloscope, a clean supply), and whether the test board for the chip could be built or tested there.
5. **Silicon route.** ChipFoundry has not confirmed ReRAM on a shuttle. Does USN have access to IHP's MEMRES kit or to
   another ReRAM run through Europractice?
6. **Venue.** His view on ISMVL for a system paper (REBEL-6 + TCIM0) beside the security paper.
7. **REBEL-6 itself.** Whether a hardware-security review of REBEL-6 is of interest to the group.

## 5. Questions he may ask, and short answers

- *Why ternary?* The paper does not claim that ternary is better. It claims that ternary CIM has a specific leak (sparsity) and
  shows what it costs to close it. TCIM0's energy per multiply-accumulate is within a few-fold of INT8 hardware.
- *Why ReRAM at this size?* Not for energy: for 1,728 weights kept without power in about a seventh to a tenth of the area of
  flip-flops.
- *How good is the device model?* A stand-in. SkyWater's public yield data fix the device spread only to a factor of about
  seven. The test chip exists to measure exactly that, with programming levels set from the board.
- *Is the 1.5× cost worth it?* For a model that must stay secret, yes, if the layout is balanced. The error detection comes
  free with it. A current flattener on 2T2R is the alternative and is not simulated yet.
- *Can the attack be done in practice?* The read counts scale with the square of the assumed noise (5 µA rms per clock cycle).
  2T2R needs one to a few hundred reads. One-of-three as drawn needs about 10⁵ to 10⁶, which is seconds to minutes.
- *What stops the attacker from reading the weights directly?* Revision 4.9: locked at reset, read-back and programming refused,
  unlock only by erasing. The tile's results must stay with the host; with readable results and chosen inputs no side channel
  is needed.
- *What is verified, and how?* Logic: about 107,000 checks in two simulators, 126 of 126 injected faults caught, formal proofs
  with four tasks still open. Layout: DRC, LVS and the foundry's precheck, each shown able to fail.

## 6. Open points to admit

- No silicon; the leakage model has no supply network, no bit-line resistance and one corner.
- Rotation and balanced bit lines are simulated at circuit level; neither is drawn or in the RTL. The 3T3R chip is not assembled.
- Routing capacitance of the 3T3R macro is not extracted.
- Four formal tasks of revision 4.9 are open.
- The questions to ChipFoundry, IHP and the REBEL-6 group, drafted on 9 October, were not sent as of the last record.

## 7. Proposed next six weeks

1. Send the three sets of questions (this week).
2. Draw the balanced cell or the transposed column, extract it, and re-run the attack on the extracted values.
3. Put the rotation in the RTL (controller option), with tests, injected faults and proofs; draw the switch.
4. Simulate the current-flattener baseline; add corners and a supply-network model.
5. Recorded FPGA re-run with the byte-level transcript; co-simulation with the REBEL-6 executor once the interface is agreed.
6. Preprint of the security paper; decide the silicon route with what ChipFoundry and IHP answer.

## 8. One thing to settle before the meeting

The project documents treat REBEL-6 as USN's specification and claim no silicon. If a fabricated REBEL-6 chip is available to
you or to USN, say so at the start: measurements on it would come before everything in section 7.
