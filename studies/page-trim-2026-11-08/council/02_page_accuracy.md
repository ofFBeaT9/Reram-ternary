# Council paper 02: accuracy and consistency of the revision 4.8 page

Reviewer 02, 8 November 2026. Inputs: docs/page/build.py, security_section.py, base_rev45.html, built /tmp/claude-0/pg/t.html, results/, docs/STATUS.md, rtl/tcim_core.sv, tritone-tpu-soc commit 0999075. The H6 row was not reviewed.

Checked and correct: 72 × 24, 3,456 devices, 48 sense amplifiers, −72…+72, "72 TMAC.T" (STATUS.md:89), −128…127 offset (tcim_core.sv:293), read-back refused under LOCK (tcim_core.sv:307, proof :533), 11 SEC checks (tb_ttpu_gen2_sec.sv), every |t| value, the triage counts (6/13/6/3), the fuzz numbers and the GDS md5.

## Findings

1. **Blocker. The TPU evidence is not stored anywhere.** The lede says "Every number is read from the repository's result files", but "11 checks" and "2 of 5 did before" are typed into build.py:235. The only logs are in /tmp/claude-0/g2…g5, which will be lost. *Fix:* commit the run logs to the TPU repo (or results/), or label the section "hand-written, from commit 0999075".

2. **Should-fix. The TPU "2 of 5 did before" is misleading.** The count comes from /tmp/claude-0/g2: the new SEC test on the new RTL plus tb_tpu_benchmarks. On the old RTL the SEC test fails 7 of 11 checks (commit message), so only 1 of the 4 old benches passed. Also, three benches passed only after their stale version checks were edited. *Fix:* "New SEC test, 11 checks (7 fail on the old RTL). Of the four existing benches, two timed out on the missed DONE pulse, and three had stale version checks, now updated. All five pass."

3. **Should-fix. One triage row contradicts itself** (build.py:83). The row says "tested, not proved" and then "the miter proves timing does not depend on data". STATUS.md 15.4 adds the missing clause. *Fix:* "The miter proves the timing does not depend on data. The exact count (21 + 21 steps, 152 cycles) is tested only."

4. **Should-fix. The programming |t| has the wrong trace count.** The security section says "150,000 traces per group", but the programming 65.67 is from 20,000 traces (tvla.json programming). "Any cell" is also an overclaim: tvla_4t4r.json has no programming entry. The same applies to "Neither cell fixes the programming leak" (build.py:209). *Fix:* "(20,000 traces; modelled for 2T2R and one-of-three)".

5. **Should-fix. The reused cell figure points to cuts that are not on the page.** Its caption says "A and B mark the two cuts below", but the cut figures were not reused. *Fix:* in build.py:225, replace that sentence or drop it.

6. **Should-fix. The system figure shows the revision 4.5 register map.** It lists "CTRL, STAT, X0–X2, Y0–Y23, PROW, PDATA, PCMD, PITER" and misses SEC, ACT and MARG. *Fix:* add those three to the caption replacement, or note "registers as of 4.5".

7. **Should-fix. Two overclaims for a professor.**
   - "Proven or checked exactly: the logic" (build.py:181). The logic has stated properties proved plus tests; it is not proven correct as a whole. *Fix:* "the logic's stated properties (formal) and its tests".
   - "layout signed off" (build.py:247) reads as a foundry sign-off. *Fix:* "layout passes DRC, LVS, antenna and ChipFoundry's precheck".

8. **Should-fix. The precheck row names the wrong script.** security_section.py:158 says flow/eda/pc_batch24.sh, but precheck.json says the run was PC batch 28c. *Fix:* "flow/eda/pc_batch28c.sh".

9. **Should-fix. The Corrections list misstates the "508" fix.** It says "508 checked numbers … now read from the result files", but no such count appears on the page; it was dropped. Bullet 4 (ESD) is not a correction. *Fix:* "removed", and delete bullet 4.

10. **Note. The cell options give numbers with no source.**
    - "Largest |t| of 72 samples is typically 2–3.4" is not in any result file. *Fix:* cite a null run or cut it.
    - "1.5× / 2×" area is a device-count estimate. *Fix:* label it "(by device count)".
    - "96 (72 needed)" differs from STATUS.md 15.6 ("96"). *Fix:* use the same value in both.
    - "Would double read power" was not modelled. *Fix:* say so.

11. **Note. "Async reset during a real pulse leaves a partial write" is stated as fact** but was not simulated (STATUS.md 15.4). *Fix:* "can leave".

12. **Note. The revision label in STATUS.md is stale.** Its header still says "revision 4.7, 7 November", but it contains 4.8 and an 8 November section 15.6. *Fix:* update the header.

13. **Note. The verification table hides when the tests ran.** The simulations ran on tcim_core.sv md5 d41aed6c. The present file differs only in its FORMAL block (STATUS 15.3). *Fix:* one line under the table.

14. **Note. "Next chip" in Next steps is shorter than the triage.** It omits redundant LOCK, the row-answer count and break-before-make. *Fix:* add "and the three logic fixes of NEXT_CHIP_SPEC section 5".

## Readability cuts (about 10-minute read)

- **Verification table, 27 rows down to about 10:** one row for the four test benches, one for the five formal tasks plus the miter, one for the four chip builds.
- **Triage, 28 rows:** merge the "stands" rows that only record limits of the model (idle impedance, SA DC only, ACT and EM, SEC write ignored, CVC warning) into one row, "Model limits, stated".
- **Cell options:** delete the two-pair parenthesis and the "48 more bit-line slices" clause, which conflicts with "72 needed".
- **"Tell your professor / Do not claim":** this reads as coaching if the professor reads the page. *Fix:* retitle it "What can be claimed".
- **"Gemini's proposal":** say "a 4T4R cell proposed in a Gemini summary".

**Verdict:** the numbers read from results/ are correct, but the hand-written TPU section and five static sentences need fixing before the page goes to a professor.
