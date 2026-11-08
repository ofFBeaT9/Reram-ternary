# Council 02: verification of the revision 4.6 change to rtl/tcim_core.sv

Reviewer lens: formal verification and test. I reviewed by reading only (yosys/sby are not installed here). I used two
short Python string checks: fault strings against the current RTL, and identifiers used before they are declared.
Severity: **blocker** (a claim or result is unsupported as it stands), **should-fix** (a property or test is weaker
than its comment or than the repository's rules require), **note**.

Evidence I found in this copy (the brief says the PC logs are absent, but `flow/eda/formal24/` is here):
`flow/eda/pc_batch24_formal.log` and `formal24/*.log` record PASS for spi, safety, safety_pnx, progress, miter prove
and prove_pnx. The run of `check_faults.py` in batch 24 reports 21 of 22 faults; the fault it missed did not
elaborate (OTHER). `results/rtl_mutation.json` reports 109/109 and `results/rtl_mutation_pnx.json` 115/115.

## Checks run here

- Every fault string in `formal/check_faults.py` (22) and `tb/mutation_test.py` (109 + 6 PNX) occurs exactly once in
  the current `rtl/tcim_core.sv` / `rtl/tcim_pkg.sv`. Nothing would be NOT APPLIED.
- Elaboration: no fault introduces an identifier that is declared after the line it lands on. The rewritten
  miter fault uses `x_nz` (declared at line 148) at line 162. The fault that failed in batch 24 used `w_pos` (line 167).
  The mutation faults that use `w_pos`/`w_neg`/`next_row` land at lines 184 and 316-336, after those declarations.
  `margin check: PDATA not written` leaves `for (...) ;`, which is legal SystemVerilog.

## Findings

### Evidence and process

1. **Blocker: the page cites the wrong formal log.** `docs/page/security_section.py:116-120` reads
   `results/formal.log` and labels the row "Formal: safety properties (with the new ones)". That log dates from
   12 October (revision 4.5). It contains none of the revision 4.6 properties (`grep f_srow|f_cnt|r_lock` gives
   nothing), so the page would show PASS for proofs that log never ran. The revision 4.6 runs are in
   `flow/eda/formal24/`. Copy them, or batch 25's re-run, to `results/` (for example `results/security/formal_core_*.log`)
   and point the page at them.
2. **Should-fix: `make formal` never proves the miter, and does not stop when a base proof fails.**
   - `Makefile:142-144` runs spi/safety/safety_pnx/progress but not `tcim_miter.sby prove|prove_pnx`. It still runs
     `check_faults.py`, which counts the five miter faults as caught when their proof FAILs.
   - The recipe is `( ... ) 2>&1 | tee ../results/formal.log` with no `pipefail`, so a failing base proof does not
     stop make.
   - `check_faults.py` does not check that the unfaulted proof passes.

   Together, a broken base proof would make every fault look "caught". Fix: add both miter tasks to `make formal`,
   set `SHELL := /bin/bash` and `.SHELLFLAGS := -o pipefail -c` (or check each status), and have `check_faults.py`
   first run each task once on the unmodified RTL and require PASS.
3. **Should-fix: nothing ties a log to the source it ran on.**
   - `results/security/miter_prove*.log` (4 November, sandbox) and `flow/eda/formal24/` (5 November) carry no hash
     of the RTL.
   - Batch 25 (`pc_batch25.sh:22`) hashes `rtl/*.sv tb/tb_tcim.cc formal/check_faults.py` but not
     `formal/*.sby`, `formal/tcim_miter.sv` or `tb/mutation_test.py`.
   - Batch 25 re-runs only `check_faults.py`, not the base proofs.

   The current RTL's file time (5 Nov 00:47:47 -0800) is just before batch 24's start (00:48:44 if its log clock is
   UTC), which fits, but that is not proof. Fix: hash all formal inputs, and re-run the base proofs in batch 25 or
   compare against a hash recorded by batch 24.
4. **Note: `results/formal_faults.json` is out of date.** It still lists "miter: start row from the weights of
   row 0" (OTHER, 21 of 22 caught). The current script has "...from the input of row 0" instead, which has not been
   run yet. Until batch 25 lands, no result shows that the start-row path of the miter can fail. The page reads this
   file and would correctly show 21 of 22.
5. **Note: `check_faults.py` records only PASS/FAIL.** It does not record which assertion failed. A fault meant for
   the constant-activity property could be caught by an unrelated assertion and still count. Fix: save the
   `Assert failed in ... tcim_core.sv:<line>` line from the sby log in `formal_faults.json` and compare it with an
   expected line.

### Properties under `ifdef FORMAL` (rtl/tcim_core.sv)

6. **Fixed-latency read order (lines 468-471): sound; "each row exactly once" follows.**
   - `f_cnt` counts answers independently (line 424) and `f_srow < 72` is asserted.
   - The k-th answer must be row (f_srow + k) mod 72 while `f_cnt < 72`, `S_READ` exits only to `S_FINISH`, and
     `S_FINISH` requires `f_cnt == 72`. So there are exactly 72 answers on 72 consecutive rows mod 72, which is every
     row once.
   - It catches a skipped row, a repeated row, a missing wrap, early or late ends, and a first request that is not
     `first_row`.
   - Because `f_srow` is copied from the logic's own `first_row` (line 417), it does **not** catch a wrong start row
     inside 0..71: NOSHUF ignored, a start row that is always 0, or a start row computed from data. Today those are
     caught only by the test bench (mutations "NOSHUF ignored", "start row always 0") and by the miter (data
     dependence, via NOSHUF only).
   - **Should-fix (cheap):** add `if (f_cmd==1 && !r_zskip && r_noshuf) assert (f_srow == 0)` (NOSHUF cannot change
     while busy). Optionally also assert that at GO `f_srow` equals `lfsr[6:0]` mod 72, computed in the property.
7. **Should-fix: the request line and operation are not checked in `S_READ`.**
   - "Answers" are acks seen in `S_READ`. In the safety task the ack is free, so it can arrive with `req` low. A
     product that drops `req` passes safety and is caught only by the progress task.
   - An `arr_op` of `OP_SUM` in a digital product is caught by nothing in formal: line 429 exempts `OP_SUM` from the
     row check.
   - Fix: add `if (f_cmd==1 && state==S_READ) assert (req && arr_op == OP_READ)`.
8. **Should-fix: the constant-activity property (461-463) is written from the logic's own derived signals.**
   - It compares `acc_upd` and `d_acc_next` with `acc` and `d_acc`, which are the next-state wires. The registers
     themselves are not checked.
   - A fault on the assignments at line 291/292 is invisible to it: `acc <= acc_next`, or dropping
     `d_acc <= d_acc_next`. The mutation "dummy accumulators never updated" is caught only through ACT in the test
     bench.
   - This is the pattern `CLAUDE.md` warns about ("not from the logic's own derived signals").
   - Fix: keep shadow copies `f_acc_q <= acc; f_dacc_q <= d_acc; f_upd <= (f_cmd==1 && state==S_READ && arr_ack)`.
     In the next cycle, assert per column `(acc != f_acc_q) != (d_acc != f_dacc_q)`.
   - Note: the property is about the *number* of updates. It says nothing about toggle counts or power, and the
     header should not suggest more.
9. **Should-fix: the empty-pulse property is weaker than before, and its comment is stale.**
   - Line 435 still says "every pulse selects at least one device". Line 438 now checks that only with VARPROG.
   - In the default (constant-time) mode, no property ties the pulse mask to the devices that still have to change.
     A fault giving empty masks while devices are pending still satisfies lines 438/440/441. The miter does not
     compare masks, so only the test bench catches it (programming fails).
   - Fix: add an independent shadow of the pending sets. Decode them from `f_pdata` with `T_POS`/`T_NEG` in the
     property, update them from each verify answer, and assert `mask == pending & failed-verify` for every pulse.
     This also covers the new path where a failed reset phase leads to empty set pulses (316-317). Today that path
     is covered only by the mutation "constant time: set pulses after a failed reset phase".
10. **Should-fix: "21 + 21 pulse steps" is never proved as a number.**
    - The miter is relative: it shows the two copies agree, so a data-independent change (for example 20 + 21
      steps in both copies) passes it.
    - The core properties bound only from above (`arr_amp < 21`, `r_piter <= 42`). Only the test bench checks
      42 pulses and 44 verify reads.
    - Fix: count reset and set pulses in the property, independently, and assert at `S_FINISH` of a program command
      with `prow_ok` and `!r_varprog` that there were exactly 21 of each. Products already have the matching absolute
      check (line 471).
11. **Note: the LOCK properties (477-480) are sound.**
    - "Set-only" (f_lock -> r_lock) together with "options off under LOCK" covers the claims, and the faults show
      that each property can fail.
    - Lines 479/480 use the logic's decode signals `a_piter`/`a_act`. A fault in that decode would make them
      vacuous. Writing `bus_addr == 6'd49 && !bus_word` in the property is cleaner.
    - No property shows that LOCK can be set at all. The LOCK faults show it indirectly.
12. **Note: the margin-check properties (433, 450, 451) are sound but have no fault each.** The faults show that
    "no pulse" (431/450) can fail. Nothing exercises the row properties 433 for f_cmd 5 or 451. The pulse-count
    lemmas (447-448) and the zero-skip lemma (475) are lemmas and need no fault.

### Two-copy miter (formal/tcim_miter.sv, .sby)

13. **The assumptions are not too strong for the stated claim (timing).**
    - Public writes are equal (line 38), and only X0-X2 and PDATA, plus everything the array returns, are secret.
    - ZSKIP and VARPROG are off (39). These are documented, opt-in leaks; NOSHUF and LOCK stay free, so both locked
      and unlocked runs are explored.
    - The ack comes only on a request (40). That is mild, because no state reads an ack while `req` is low.
    - `bus_err` is combinational in address and strobes only (core line 114), so it cannot differ between copies.
    - `bus_rdata` is combinational, so a read cannot vary in timing.
    - BUSY is not compared, but in the correct RTL every busy state except `S_FINISH` holds `req` high, and DONE rises
      exactly when BUSY falls. `irq` (with IE free) therefore covers the BUSY/DONE timing.
14. **Should-fix: two assumptions should be written down.**
    - (a) The shared `arr_ack` assumes that the macro's answer time does not depend on data. That holds for the chip
      controller by reading: `rtl/chip/tcim_actl.sv` 103-160 times a request from `op` and the configuration pins
      only, never from the masks. It is not proved. A miter of `tcim_chip_core` (core + `tcim_actl`) with free sense
      inputs would make it a proof.
    - (b) Masks and `arr_row_mask` are not compared. During programming they depend on the data by design (empty or
      non-empty pulses), so constant-time programming hides time, not supply current. The miter header and the page
      should say "timing only". The power side belongs to `tvla_tcim0.py`.
15. **Note: the threat model should say what it does not cover.**
    - Read-back (PCMD -) returns the weights even under LOCK (`tb_tcim.cc:979`), so a bus master is not part of the
      threat model. The miter treats the weights as secret only from a timing observer.
    - ACT (+50) shows the parity of the dummy accumulators when unlocked. Which columns update their dummy
      accumulator depends on x and w, so that parity depends on the data. The header line 32 calls them "never
      read". Say "seen only through ACT's parity, which depends on the data; hidden under LOCK".
16. **Should-fix: the miter faults do not show that each compared output is live.**
    - All five faults change the request sequence (`req`/`row`). None is caught only by `irq` (DONE timing) or only by
      `amp`.
    - Fix: add one fault that delays DONE by a cycle after a data-dependent condition, one that makes the amplitude
      depend on the data, and one for "reset phase stops at verify". Also run the miter faults on `prove_pnx` (today
      `prove` only).

### Fault coverage (check_faults.py, mutation_test.py)

17. **Should-fix: new behaviour with properties but no formal fault.** The following are covered by mutations in the
    test bench but not by `check_faults.py`, although a property exists that should catch them:
    - "ACT not hidden by LOCK" (line 480)
    - "LOCK does not block option writes" (line 478)
    - "shuffle: start row may exceed 71" (`f_srow < 72`)
    - "fixed latency: no wrap from row 71 to row 0" (the modulo branch of line 470)
    - a "margin check reads another row" fault (lines 433/451)

    Add them, so that each new property can be shown able to fail.
18. **Note: new behaviour with no fault at all.**
    - The dummy update direction "+1 or -1 from the LFSR" (line 204). A fault that always counts up survives both the
      test bench (ACT still changes) and the formal properties.
    - SAT cleared by a margin check (line 281). A "SAT not cleared by a margin check" fault has no test (the
      read-back version exists).
    - The exact ACT parity (an inverted ACT would survive).

    None of these is a timing claim. Either add faults and tests, or state that they are not checked.

### Test bench (tb/tb_tcim.cc) against the header of tcim_core.sv

19. **Well covered:**
    - 150 fixed-latency products of equal length: every row exactly once, rotated order, no gaps (527-554).
    - Start rows vary and NOSHUF starts at 0 (556-583).
    - ZSKIP read counts (585-598).
    - Constant-time programming: 42 pulses and 44 verify reads per command (430-431), equal duration for every
      timed program command including the failure paths (510, 1037), PITER counting only the pulses that select a
      device (428).
    - The margin check, including the clear on a refused command (908-956).
    - LOCK (958-983), including ACT and PITER hidden and the reset clearing it.
    - The SEC illegal code and SEC writes while busy (889-906).
20. **Note: product duration is checked only against different inputs.** The 150 timed products use one set of
    weights and clean array answers, so "neither on the inputs nor on the weights" (header line 30) rests on the
    miter for the weights. A short loop with re-programmed weights and an invalid cell, timed with `timed()`, would
    give the test bench the same claim.
21. **Note: ZSKIP "in increasing order" (header line 9) is checked by the formal properties (456) only.** The
    test bench checks the number of reads, not the order. That is acceptable as long as `make formal` actually gates
    (finding 2).
22. **Note: the start row is not uniform.** It is `lfsr[6:0]` with 72..127 folded onto 0..55 (line 162), so rows
    0-55 are twice as likely as 56-71. The test bench checks only "at least 10 different in 40". QA_GATE finding 3
    already says not to call it random; the page should not call it uniform either.

## Summary

The new properties mostly state what they claim, and the read-order property does imply "each row exactly once".
What is missing:
- the page points at a revision 4.5 formal log (finding 1);
- `make formal` neither proves the miter nor fails when a base proof fails (finding 2);
- several properties are relative or use the logic's own next-state wires, so the faults they should catch are
  caught only by the test bench (findings 7-10, 17).

The miter's assumptions are acceptable for a timing claim. The assumption that the macro answers in a time that does
not depend on data, and the fact that masks (and so power) are excluded, should be written down (finding 14).
