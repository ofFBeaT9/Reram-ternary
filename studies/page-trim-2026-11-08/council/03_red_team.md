# Council 03: red team (8 November 2026)

## H6 empty-pulse study

1. **Blocker: "closed" is fragile, and build.py:121 prints it automatically.** The selected-row margin is 0.1/1.5e-9/42 = 1.6e6 writes, 16× the criterion. It holds only at 27 °C, tt, fitted F (k = 1); each alone erases it: with Ea = 1.5 eV the reset rate is ×33 at 50 °C and ×2,800 at 85 °C; the k = 4 F is ×34; the F spread is 2.2 decades. *Fix:* sweep to 85 °C, use the tail F, and print "stands (partial)" until then.
2. **Blocker: the other-row 0.0 is float underflow.** The ulp of g ≈ 0.96 nm is 2.1e-25 m, and any step under half an ulp is lost. Set-direction steps at 0.64 V are only 0.55 ulp. With `rel == 0`, n10 = inf, so `closed` = True. The true bound is N·ulp/2 = 1.2e-11 per pulse (2.7e6 writes). It still passes. *Fix:* accumulate Δg separately, report it signed, and never map 0 to inf.
3. **Should-fix: 120 µS is outside the model.** gap_for clamps it to GMIN, which reads 103 µS, so set-direction drift is zero by construction. At −0.64 V such a device loses 11 % per µs,. *Fix:* use 100 µS. empty_pulse_gap.py:57 maps 28 µS to 120 and 7.93 µS to 4.5: fix it or delete it.
4. **Should-fix: the exposure model.** Every PCMD re-verifies its row, so own-row drift does not accumulate across writes. The worst case is a row written once while other rows are rewritten, at 42 events per command. "10,000" is not on the page, although empty_pulse.py:84 says it is. A ±10 % threshold also fails HRS drifting *away* from the reference. *Fix:* budget the commands since the last verify, from the test plan, on the page; use the signed margin.
5. **Should-fix: the deck's omissions.** No ad/as/pd/ps and no extracted capacitance, so drain coupling is underestimated. Only uniform columns were run, with no half-selected step.

**Defensible now:** at 27 °C, tt and the fitted F, in an all-HRS column, an empty set pulse moves a selected-row device by about 1.5e-9 per pulse. Other rows move less than 1.2e-11. LRS, temperature and F-tail runs are pending.

## Page and triage

6. **Should-fix:** "11 stand for this chip" is wrong. With the six "next chip" items it is 17 of 26.
7. **Should-fix:** build.py:302 publishes `C:\Users\ACER\Downloads\…`. Remove it.
8. **Should-fix:** "Every number is read from the result files" is false (cell table, 152 cycles, 30–120 µS). Write "every test result".
9. **Should-fix:** the input "pass" hinges on assumed parameters. For the 4.6 inputs, |t| is 2.11 at k_uA = 0 and 19.55 at 0.15. The 4.7 value of 3.59 exceeds Council 01's 95 % null point (3.38). Write "no leak detected (150,000 traces, 5 µA noise, assumed digital coefficient)".
10. **Should-fix: stale or unsupported text.** STATUS 15.6 still says "remove the weight leak". STATUS 15.4 and the H6 row say "not run". The H6 template claims "for nanoseconds" (the pulse lasts 1 µs) and "part of the programming-profile leak", both unshown.
11. **Note:** "Reset clears LOCK" is marked "stands", yet Next steps promises a LOCK that survives reset. Mark it "next chip".
12. **Note:** cite "an alternative 4T4R cell", not "Google's Gemini AI". The formal row lists five proofs but says "7 of 7". Say what "152 cycles" counts (42 × T_PULSE 16 > 600).

**Councils 01 and 02:** their findings are fixed. The new errors are 2, 3 and 10.

**Verdict:** after fixes 1–10, the page can go to a professor, provided H6 reads "stands (partial)", not "closed".
