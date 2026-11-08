# Council 01: triage and 4T4R (8 November 2026)

## Triage

1. **Blocker: "Weights readable over the bus under LOCK" is not closed.** Under LOCK, products still run and Y is still readable (`rtl/tcim_core.sv:146`). LOCK gates only PITER, ACT, read-back and margin PDATA (`:152-153`, `:307-308`, `:389`). 72 one-hot products read the whole matrix. Fix: retitle the row "Read-back under LOCK: closed". Add a row "Weights extracted with 72 one-hot products: stands (trusted bus)".
2. **Should-fix: H5.** `r_lock` is still one flip-flop (`:90`). One upset clears it, and after that a SEC write is accepted again (`:269`). Fix: "closed for the option flip-flops; LOCK itself is one flip-flop (next chip)".
3. **Should-fix: rows missing from the triage.**
   - Early end of a product through an `r_cnt` fault (NEXT_CHIP_SPEC:62): next chip.
   - Council 01 §2(c,d): the ACT parity tree switches under LOCK, and the per-column clock gates show by location under EM. Stands.
   - Device behavior: no forming, retention or cycle-to-cycle variation in the model; spread uncertain by ×7 (STATUS §13). Stands.
   - sky130B and the sign-off PDK set (STATUS §14): outside.
   - Break-before-make on asynchronous reset (NEXT_CHIP_SPEC §5): next chip.
4. **Should-fix: the inputs row.** Write "closed in the model", as QA_GATE does.
5. **Note: `/tmp/claude-0/pg/TRIAGE.md` is stale.** It lacks build.py:87. Regenerate it.
6. **Note: the programming row.** "With any cell" rests on 2T2R alone (65.67). One-of-three gives 66.38, and 4T4R was not run.
7. **Note: other wording.** The FPGA evidence is the 4.6 logic; 4.7 was never built. "Glitches" in the fuzz row are logic-level chip-select glitches, not supply or clock glitching.

## H6 criterion

8. **Should-fix: the threshold needs an exposure budget.** build.py:58 already uses the gap change (n10 > 1e6), not |V| < 0.2 V.
   - A |V| test would be unsound: it ignores duration and polarity. Even 0.2 V moves HRS +10 % in 2,980 s (`results/read_disturb.json`).
   - 1e6 is too low. Each program command pulses all 72 rows' bit lines 42 times, so each device sees about 3,000 events per full-array write. 10^4 writes gives about 3×10^7.
   - read_disturb extrapolated to 0.64 V gives about 10^6 few-ns pulses per +10 %: the same order as the threshold.
   - Fix: closed only if n10 ≥ 10 × 3,024 × (planned writes, stated in the page). Count selected and unselected rows separately.
   - Start from the worst devices: HRS at 7.93 µS and LRS at about 28-30 µS. Integrate every case, not the top 4 by peak |V|.
9. **Should-fix: the asynchronous reset was simulated only on empty pulses.** A reset during a real pulse is a partial program, a fault handle. Fix: split the row; that half stands, with break-before-make on the next chip.

## 4T4R

10. **Note: the model is a fair reading of the text.** Gemini says "one LRS, three HRS; G = G_LRS + 3G_HRS" (unified.txt ~377-379), which matches `lrs_mask` (`tvla_tcim0.py:103-108`). "Complementary dual-rail" could also mean 2-of-4: one LRS per pair. It would balance current per pair, give a detectable invalid code and double the read power. Neither reading is modelled for EM by location. Fix: name the reading used.
11. **Should-fix: the cells claims.**
    - Area 1×/1.5×/2× is right as device count (NEXT_CHIP_SPEC:21; Gemini says 2×). Add the 24 or 48 bit-line slices.
    - "96 sense amps" means sensing a device that carries no information. 72 would do, which makes 4T4R even more clearly worse.
    - "We did not move to 4T4R" and "the plan stays one-of-three" are correct.
    - "Both fix the weight leak" overclaims. A residual remains (NEXT_CHIP_SPEC:26), and one-of-three reaches 4.08 at 1 µA noise (p about 0.003 under the null). Fix: "both pass at 150,000 traces and 5 µA noise; the model sees the total current only". Run 4T4R at 1 µA as well.
12. **Note: 1.78 vs 2.61 is noise.** With W fixed, both cells draw the same analog current whatever the inputs, and their digital terms are identical. With the digital term off they give 1.67 vs 2.51. The null 5/50/95 % points of the maximum over 72 samples are 2.05/2.59/3.38. Do not rank the cells on this.

**Verdict:** the triage needs one status change (weight extraction under LOCK stands), five more rows and an H6 criterion tied to an exposure budget. The 4T4R answer holds, without "fixes the weight leak".
