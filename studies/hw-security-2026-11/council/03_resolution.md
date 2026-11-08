# Council resolution (6 November 2026)

Two reviewers worked independently from the repository (01_hw_security.md, 02_verification.md). The owner chose to fix the
gaps as revision 4.7 rather than ship 4.6 with caveats. What was done with each finding:

| # | Finding | Severity | Resolution |
|---|---|---|---|
| H1 | Start row not uniform (rows 0-55 twice as likely); "one-of-three passes" rested on a uniform model | blocker | RTL 4.7: start row = 16-bit LFSR value mod 72 (register `lfsr_m72`, proved equal to `lfsr % 72`). Model 2 draws start rows from the RTL's own distribution. |
| H2 | Input result passed by construction (update count); bit flips around zero carry the inputs | blocker | Model 2 counts flipped bits. RTL 4.7: random accumulator offset (-128 ... 127) taken off with the last row. Revision 4.6 leaks inputs in model 2; 4.7 does not. |
| H3 | 2T2R leaks per-row sparsity after realignment, not only the total | should-fix | Stated on the page and in the final report; the one-of-three cell (next chip) is the fix. |
| H4 | LOCK leaves the weights readable over the bus; SEC write while BUSY silently dropped | should-fix | RTL 4.7: read-back refused under LOCK (WERR, no array access); margin check does not write PDATA under LOCK. Read SEC back after LOCK (documented). Reset still clears LOCK: stated as a limit. |
| H5 | One upset after LOCK brings an option back | should-fix | RTL 4.7: every use of ZSKIP / VARPROG / NOSHUF gated by ~LOCK. Not testable functionally (an equivalent mutant without upsets); stated. Early-end-of-product fault primitive: noted for the next revision. |
| H6 | Empty pulse: steady-state statement; cell-node transients, asynchronous reset during a pulse | should-fix | Page and spec say "no steady-state voltage"; transients and asynchronous reset not simulated: stated as limits. |
| H7 | Idle impedance holds only for the powered-idle schematic | should-fix | Page sentence narrowed (powered, schematic, device as a resistor; package and board not modelled); spec corrected. |
| H8 | sa_power is DC only | should-fix | Page says DC; read transients not simulated: stated. |
| H9 | Wrong cause given for the programming leak | should-fix | Page: the number of devices each pulse selects depends on which devices must change (and on switching speed). |
| V1 | Page quoted the revision 4.5 formal.log as 4.6 | blocker | All proofs re-run for 4.7 (PC batch 27); the page reads only results produced by these runs. |
| V2 | make formal did not stop on a failed base proof and did not run the miter; check_faults did not check base proofs | should-fix | Makefile: pipefail, miter runs inside make formal; check_faults refuses to count without passing base proofs. |
| V3 | Logs not tied to the RTL they ran on | should-fix | PC batches 25-27 write md5 lists of their inputs (flow/eda/batch2x/md5_*.txt). |
| V4 | f_srow from the logic's own start row cannot catch a wrong start inside 0..71 | should-fix | Property: with NOSHUF the start row is 0 (fault "NOSHUF ignored"); 4.7 property lfsr_m72 == lfsr mod 72 (fault "without the 65536 term"). |
| V5 | Nothing asserted req and READ throughout a product | should-fix | Property added, with fault "a product drops its request between rows". |
| V6 | Constant-activity property on next-state wires | should-fix | Kept; the mutation test covers the register assignment ("dummy accumulators never updated"). Stated. |
| V7 | Empty-pulse property weaker, comment stale | should-fix | Comment corrected. |
| V8 | "21 + 21 steps" not proved absolutely | should-fix | Tested (every program command 152 cycles, 42 pulses) and the miter proves data independence; not an absolute proof: stated. |
| V9 | Miter assumptions unwritten (macro answer timing, masks not compared) | should-fix | Written into tcim_miter.sv's header. |
| V10 | A planted proof fault did not elaborate | note | Rewritten (x_nz); batch 24's "21 of 22" superseded. |
| V11 | ACT parity is data dependent when unlocked | note | Header and page say so; LOCK hides it. |
| V12 | Gate-level xnor fault landed on a dummy accumulator | (found in batch 25) | gls_chip.sh picks the first xnor2_1 that reaches a non-dummy flip-flop. |

Contradictions between the two reviewers: none. Where a finding asked for a new simulation (transients, unpowered idle, read
transient), it was not run in this revision and is listed as a limit, not as a result.
