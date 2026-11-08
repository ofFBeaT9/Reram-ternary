# Council 01: hardware security (side channels and faults), revision 4.6

Reviewer lens: side-channel and fault-attack soundness of the revision 4.6 changes and of the leak models. Review by reading,
plus short Python checks that import `tools/tvla_tcim0.py` unchanged and run it on variants of its assumptions. Those
checks are council evidence about a variant of the model. Their numbers are not in `results/` (scratch scripts, described in
each finding so that they can be rebuilt in `tools/`). No repository file except this one was changed.

Severity: **blocker** = a stated conclusion flips or is unsupported; **should-fix** = a claim needs narrowing, or there is a
design gap worth fixing; **note** = something to record.

---

## 1. BLOCKER: the model rotates the start row uniformly, the RTL does not. With the RTL's rotation, "one-of-three passes" flips

- Model: `tools/tvla_tcim0.py:103` `start = rng.integers(0, ROWS, (n, 1))`, uniform over the 72 rows and independent per trace.
- RTL: `rtl/tcim_core.sv:162` `start_row = lfsr[6:0] >= 72 ? lfsr[6:0] - 72 : lfsr[6:0]`. Over the full 65,535-state period
  of the LFSR, rows 1-55 come up 1,024 times each, row 0 1,023 times and rows 56-71 512 times each (counted by running the
  LFSR of line 231 from the seed `16'hace1` of line 229). That is a 2:1 non-uniformity, and it is the best case: it assumes
  that GO lands at a random point of the period.
- Why it matters: when the start is not uniform, the mean of sample k under fixed weights is a weighted sum of the frozen
  row currents that depends on the position. So per-position first-order leakage appears that uniform rotation averages away.
- Council check: exact per-sample means from the script's own `row_current`, `chip` and `hrs_g` with seed 1. The fixed group
  uses frozen row currents; the random-group mean and variance come from 1.2 M random rows. Same assumptions otherwise
  (5 µA noise). The uniform rows agree with the script's own results to within noise: a direct 200k-trace simulation gave
  10.6 and 0.83.

  | case, 150,000 traces/group | uniform start (as modelled) | RTL start distribution |
  |---|---|---|
  | 2T2R, all fixes, weights, expected max \|t\| | 10.5 | 18.4 |
  | one-of-three, all fixes, weights, expected max \|t\| | 0.8 | **6.9** |
  | one-of-three, same, noise 1 µA | 2.0 | 17.3 |

- So the one-of-three result in `results/security/tvla.json` (3.49, "passes") depends on a rotation that the RTL does not
  produce. `NEXT_CHIP_SPEC.md:20-22` ("below 4.5") and `docs/page/security_section.py:227-229` ("brings it to 3.49") rest on
  it. The spec also says the revision 4.6 sequence "applies unchanged".
- Even with uniform rotation, one-of-three has a real first-order leak: expected |t| 0.8 at 150k. The 3.49 is mostly the
  maximum of the noise over 72 samples. At 5 µA that leak reaches 4.5 at about 4.7 M traces, and at about 0.7 M traces with
  1 µA noise. The cause is frozen sense-amplifier mismatch plus frozen HRS conductances. "Passes" is true only at the stated
  trace count and noise, and the spec should say so.
- Fix: model the start-row distribution the RTL produces (better, model the deterministic sequence: see 3). Or make the RTL
  rotation uniform, for example by reducing the 16-bit LFSR value mod 72 (bias about 1/910) or by rejection, and re-run.

## 2. BLOCKER for "the logic changes remove [the input leak]": constant activity is modelled as a constant count, so it passes by construction

- Model: `tools/tvla_tcim0.py:112-113`. In `+ca` the digital term is the constant `k_dig * 24`. Apart from that term and the
  duration, the samples contain nothing that depends on the inputs: the array current depends only on W, because every row is
  read with all masks on. So the "inputs pass" rows test only the count of accumulator updates, and the RTL makes that count
  constant by design (formal property `rtl/tcim_core.sv:461-463`). Even `fixed` with `k_dig = 0` passes (2.86), so rotation
  plays no part in the input result.
- RTL behaviour the model leaves out:
  - (a) The result accumulators are cleared at GO (`tcim_core.sv:259`), and 10-bit two's-complement updates around 0 flip up
    to all 10 bits (0 → −1). The dummies (`:202-204`) take a random walk that is never cleared. So the Hamming distance of an
    update depends on the partial sum, which means on X·W.
  - (b) `cur_pos` / `cur_nz` (`:184-185`) are selected by the input of the current row and fan out to 24 ten-bit adders and
    muxes.
  - (c) The 240-input parity tree that feeds ACT (`:141`) switches with the d_acc toggles even under LOCK. LOCK masks only its
    output.
  - (d) The block has 84 clock gates (`results/sky130_chip/digital_block.json`). If acc and d_acc are gated per column, which
    gate fires is data-dependent, which is visible to EM by location.
- Council check of (a): same script, 2T2R, all fixes, fixed W, secret = inputs, rotation per trace. The digital term is
  `k_bit × (bits toggled in acc and d_acc per row read)`, following the RTL's update rule. With 0.15 µA per bit (about
  2 bits per ±1 update, so the same scale as the model's 0.3 µA per update):

  | traces/group | 0 µA/bit (null) | 0.05 µA/bit | 0.15 µA/bit |
  |---|---|---|---|
  | 20,000 | 2.72 | 3.05 | **7.54** |
  | 150,000 | | | **22.45** |

- Page text `security_section.py:196-198` ("the logic changes remove it") and the brief's "fixed latency + rotation removes
  the input leak": the evidence supports "they remove the timing leak and make the update count constant". Fix: replace the
  count term with a Hamming-distance term in `tvla_tcim0.py`. Better, take per-cycle toggle counts from a gate-level VCD of the
  routed block (the `gls_chip.sh` run) as the digital term. One possible RTL mitigation (proposal): clear or randomize the
  result accumulators differently, for example preload a random offset and subtract it at the end. Then re-test.

## 3. SHOULD-FIX: "2T2R still leaks total sparsity" understates the leak. Rotation by one of 72 positions is undone by realignment

- With uniform rotation every sample position sees the same mixture, so the per-position t-test sees only the average row
  current, which is the total number of LRS devices. But each trace is the fixed cyclic sequence of 72 row currents, shifted.
- Council check: 5,000 fixed-weight traces at 5 µA, 2T2R with all fixes, blind iterative circular cross-correlation alignment
  (the first trace as the initial template, no knowledge of the start rows). The correlation of the recovered 72-row profile
  with the true number of non-zero weights per row is **0.91**. So the per-row sparsity leaks, not only the total.
- In addition, the LFSR is reset to a constant (`:229`) and advances once per clock (`:231`). So:
  - Deterministic firmware gives the same start row on every boot, and no attacker control is needed.
  - Each GO's start row is a known function of the cycle count.
  - On the SKY130 chip, GO arrives over SPI from the test board, so the board owner sets it.

  The page (`:230-231`) and `NEXT_CHIP_SPEC.md:46-49` state only the "controls GO" case.
- Fix the wording on the page (`:197-198`, `:227`) and in the spec: per-row non-zero counts are recoverable. Rotation hides
  the position only against a first-order, unaligned test.

## 4. SHOULD-FIX (design): LOCK gives no confidentiality against the bus, and the page's "forces the secure behaviour" does not say so

- Under LOCK, PCMD − (read-back, `:274-279`, `:346-353`) still copies any row's weights into PDATA, and the margin check
  (`:280-285`, `:356-359`) does the same. LOCK is cleared by reset, and the weights are non-volatile. So anyone who can reset
  and reach the bus can read every weight directly, without a side channel. On the SKY130 chip that is the board, over SPI.
- So LOCK protects against nothing that has bus access, and the side-channel measures matter only where the bus and reset are
  trusted. LOCK's logic does what F4 asks (`ROADMAP.md:34`, formal `:477-480`), but the threat model does not hold together.
- Also: a SEC write while BUSY is silently dropped (`:237`, `:242`), LOCK included, with no bus error. Firmware must read SEC
  back after writing LOCK.
- Proposal: under LOCK, refuse read-back and the PDATA write-back of the margin check (WERR), or add a separate read-protect
  bit. Until then, `security_section.py:214-215` should state the limit.

## 5. SHOULD-FIX (faults): LOCK is enforced once, at the write, not where the options are used

- `r_zskip`, `r_varprog` and `r_noshuf` are single flip-flops cleared at the LOCK write (`:246-248`). One upset afterwards
  (laser, EM or voltage glitch) turns zero-skipping or stop-at-verify back on until reset. The proved property
  `r_lock -> !r_zskip` (`:478`) holds only for fault-free logic.
- Fix (tiny): qualify each option where it is used (`r_zskip & ~r_lock`, and so on), so that one fault has to hit two
  flip-flops.
- Related: the fixed-latency product ends on `r_cnt == 71` (`:163`). A fault in `r_cnt` or `arr_row` ends the product early,
  with DONE and no WERR. That is a row-skip primitive for differential weight extraction. A redundant check that 72 answers
  arrived (WERR otherwise) would close it. Noted for the next revision. Read-back (4) is the easier attack today.

## 6. SHOULD-FIX: the empty-mask pulse. The sequence is sound, but "no voltage across any device" is a steady-state statement

Answer to the brief's question, from `rtl/chip/tcim_actl.sv` and `periph.spice`:

- **Empty set pulse** (`mp = mn = 0`):
  - `blp/bln_prg = 0` and `sl_prg = 0` (`:116-118`).
  - Every bit line and source line is grounded through NOR(prg, sen, flt), except in the flt cycles, when it floats at 0 V
    with the word line off.
  - The word line rises on VWLP over grounded lines.
  - Harmless.
- **Empty reset pulse**:
  - `blp_prg = bln_prg = ~0` and `sl_prg = 1`, so all 48 bit lines and the source lines are driven to VPRG from the BRK edge.
  - The word line rises only at the end of SETL, that is MAKE plus T_SETTLE (at least 2) cycles later (`:124-134`).
  - The word line falls when WLON ends (`:139`). The lines are released at BRK2 (`:149`) and grounded at GND (`:153`), 3
    cycles after the word line control falls.
  - bl and sl come from the same VPRG rail.
  - So there is **no window in the controller's sequence with the word line on and unequal line voltages**. This holds
    provided the lines settle within T_SETTLE and the word line falls within about 2 cycles. An empty reset step loads the
    board's VPRG with 48 bit lines and 24 source lines at once (`QA_GATE.md:26-27`), and no transient checks it.
- **What the statement misses**:
  - In every row whose word line is off, the node between the device and its select transistor follows the bit line only
    through the device.
  - When the bit lines rise to VPRG, every such device sees a transient of set polarity. When they are grounded, it sees one
    of reset polarity. Its size depends on the line edge rate against C(node)/G, and is largest for HRS devices.
  - Real reset steps already do this on the unmasked lines. Constant-time programming makes it happen 21 times per program
    command on all 72 × 48 devices, against 1-2 times with stop-at-verify.
  - `macro_sim.py` is quasi-static on a 2 × 2 array, so this transient has not been simulated.
- **Asynchronous reset**: `rst_n` (`tcim_actl.sv:94-99`) drops the word line and grounds every line on the same edge, with no
  break-before-make. A reset or brown-out during a pulse leaves the selected row with the word line still falling while bl and
  sl discharge at different rates (bl pull-down W 2 µm, sl W 4 µm). That is an uncontrolled partial pulse, and a fault-injection
  handle. It was not new in 4.6, but constant-time programming makes it 21× more likely that a reset during programming lands
  inside a reset pulse.
- Fix: a transient deck (one column, 72 rows, with the internal-node capacitance, with and without the device model) for an
  empty reset step and for an asynchronous reset in WLON, reporting the peak |V| and the gap change. Until then, word
  `security_section.py:211-212` and `tcim_core.sv:36-37` as "no voltage across the devices of the selected row while its
  word line is on".

## 7. SHOULD-FIX: idle impedance. The deck does model the powered idle state, but "does not reveal stored data" has holes

- The deck matches its docstring for the lines:
  - prg_lv = 0 and sen = flt = 0, so dn = 1 and the ground switches are on (`idle_impedance.py:44-45`).
  - The source-line ground is on (`:47`).
  - sel = 0, so the word lines are pulled down (`:28`).
  - Its finding (stored state below 1e-6 relative at every pin) follows from the topology: each device sits between a grounded
    bit line and a node behind an off transistor.
- Holes:
  - (a) Schematic only. There are no extracted layout parasitics (line-to-supply coupling), and the ReRAM is a pure resistor
    with no capacitance. The PDF's own test (item 6) is an "AC impedance sweep of the extracted power network".
  - (b) The reference bias sits at the read setting (`:42`, r1 = vccd). In tcim_actl IDLE, `ref_sel = 0`. The docstring
    says so, but the deck is then not exactly "the idle state the controller holds".
  - (c) Powered idle only. With vdda off, the ground NORs, the word-line pull-downs (gates from level shifters on vdda) and
    the transmission-gate PFETs (gates at 0) behave differently: the lines and word lines float, and a PFET conducts if its
    pin is biased. The isolation argument does not cover an unpowered or powering-up part. DExiM-style package
    measurements may be made unpowered.
  - (d) The positive control (`:74-82`) shows that the method sees a *conductive* path. It does not show sensitivity to a
    weak capacitive or leakage path at the 1e-6 level. Example of a sensitivity control: idle plus 1 fF from the internal
    node to the pin.
  - (e) The largest differences sit at the top of the sweep (vdda 5.2e-7, vprg 9.5e-7 at 1 GHz), so the trend beyond the
    sweep is not shown.
- The page's sentence (`security_section.py:162-163`) already says "in this model" and "package and board are not
  modelled". It should add "powered idle, schematic without layout parasitics, device as a resistor".
  `NEXT_CHIP_SPEC.md:34-35` ("The idle isolation is already met") is an overclaim. It should read "met in the powered-idle
  schematic model".

## 8. SHOULD-FIX: `sa_power.py` is DC only. Two page sentences go beyond it

- The deck uses `dc` / `op` (`sa_power.py:33-55`). "Clamped for every low-resistance device, so the spread of the set state
  does not reach the supply" (`security_section.py:188-189`) is a DC result.
- The same sweep shows the bit-line voltage moving from 0.084 V (30 µS) to 0.025 V (120 µS). So the bit-line charge, the
  settling time and the moment the sense output switches all depend on the conductance. A time-resolved attacker sees that
  transient, and it has not been simulated. Near the trip point the inverter draws crowbar current (2.406 µA at 12 µS). That
  current falls on the drifted devices the margin check looks for.
- The figure caption (`:192-193`) says "not which sign each weight has". At first order that is right. But the frozen
  mismatch differs between the P and N amplifiers of a column (sd 0.111 µA each, `sa_power.json`), so the sign is carried
  weakly. That is the same mechanism as the residual in 1.
- Fix: a transient read of one bit line at 30 and 120 µS (supply current against time). Narrow both sentences.

## 9. SHOULD-FIX: the page gives the wrong cause for the programming leak in the 2T2R case

- `security_section.py:199-201` says the constant-pulse-count leak (|t| 65.67) exists "because each device's own switching
  speed sets when its pulses become empty".
- Council check: the script's `prog_traces` with no device-to-device and no cycle-to-cycle spread still gives 2T2R |t| 31.7
  at 20,000 traces (at the first set step), against 2.67 for one-of-three. In 2T2R, how many devices must be pulsed depends
  on the target weights (a 0 needs no set). The switching speed is the mechanism only for one-of-three.
- "Amplitude profile" also collides with `arr_amp`, the pulse-voltage step, which is data-independent. The leak is the
  number of devices pulsed per step.
- Before LOCK, PITER reports that count directly (`tcim_core.sv:140`, `:326`, `:341`).

## 10. NOTE: what a trace sample is

There is one sample per row read: the DC sense-amplifier current, plus the digital term averaged over the read, plus 5 µA of
noise (`tvla_tcim0.py:116`). A row read takes at least about 12 controller cycles (`tcim_actl.sv` sequence). The accumulator
update happens in one cycle (the ack). An attacker who samples that cycle gains roughly √12 ≈ 3.5 in t on the digital term.
State in the docstring that SIGMA is per integrated row read.

## 11. NOTE: the margin check is a reliability check, not an integrity check

`ROADMAP.md:35-36` maps F5 to the PDF's "CRC/MAC on stored weights". The margin check flags only devices between a verify
target and the mid reference at the time of the check (`:364-372`). A weight changed on purpose or by a fault, fully across
the reference, reads with full margin and is not flagged. Do not present it as covering the PDF's MAC item. "Every device
that has drifted" (`security_section.py:216-217`) holds only within that band.

## 12. NOTE: ACT and PITER before LOCK

- ACT is the parity of d_acc. d_acc's updates are exactly the complement of the result updates, and d_acc is never cleared.
  So ACT is a data-dependent architectural output before LOCK.
- PITER is the real pulse count (9).
- Both are hidden under LOCK (formal `:479-480`), which is consistent. Before LOCK both are channels. This is moot while
  read-back is open (4).

## 13. NOTE: scope of the timing claims

- The miter (`formal/tcim_miter.sv:41-45`) compares req, op, row, amp and irq, but not `arr_row_mask`, `arr_mask_p/n`. That
  is correct for a timing claim.
- In analog mode (MODE +, `tcim_core.sv:261`, `:302`), the word-line pattern is the input vector itself. That mode is
  unsupported on the SKY130 chip (`tcim_actl.sv:37`), but it is in the IHP target. The page's "duration does not depend on the
  inputs" is right. Any power claim covers digital products only.

## 14. NOTE: small model differences that do not change any conclusion

- Under ZSKIP the RTL still runs the dummy accumulators for zero-weight columns. The model's `zskip` has none
  (`tvla_tcim0.py:115`). Timing dominates that case anyway.
- `hrs_g` clips (`np.minimum`, `:64`), which puts a point mass at 7.93 µS. The docstring says "cut" (truncation).

---

### Summary of verdicts on the brief's questions

- **TVLA**:
  - The assumptions are stated and the magnitudes are reasonable as placeholders.
  - Rotation is modelled per trace, but uniformly (finding 1, which flips the one-of-three result).
  - The dummy accumulators are modelled as a constant count, so the input result holds by construction (finding 2, which
    flips under a Hamming-distance term that follows the RTL).
  - The 2T2R leak is per row, not only total (finding 3).
- **RTL**:
  - The logic does what F1-F4 specify.
  - LOCK is defeated through the bus by read-back and reset (4) and by a single-flop fault (5).
  - The GO timing against the deterministic LFSR is a known limit, larger than the page states (3).
- **Empty pulses**: no window with the word line on and unequal line voltages in the sequence. There are unsimulated
  transients on the internal cell nodes, and an asynchronous reset has no break-before-make (6).
- **Decks**: they model what their docstrings say, with the exceptions in 7(b) and 8 (DC only). "Idle impedance does not
  reveal stored data" holds for the powered-idle schematic only (7).
