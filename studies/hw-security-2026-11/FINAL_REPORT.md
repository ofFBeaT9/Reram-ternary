# Hardware security of TCIM0: final report (7 November 2026)

**Verdict.** TCIM0 revision 4.7 applies every item of the document that fits TCIM0. An independent review found four gaps
in revision 4.6, and revision 4.7 closes them. Revision 4.7 is verified as fully as revision 4.5 was: two simulators,
both trit codes, mutation tests, formal proofs with planted faults, a timing miter, equivalence proofs, place and route
with timing at every corner, gate-level runs, sign-off, and ChipFoundry's precheck at 14 of 14 on the final GDS. In the
leak model, the inputs no longer leak and both timings are constant. The weights still leak through the 2T2R cell; the
one-of-three cell of the next chip closes that in the model.

**Evidence.** `docs/STATUS.md`, section 15. The explainer (`docs/TCIM0_explainer.html`), sections 13 and "Is it ready".
`results/` (the checks in `tests/test_claims.py`, section 26). The council's papers are in `council/`; the two gates are in
`QA_GATE.md`.

**Caveats.** Everything is evidence about the model, not silicon. The LFSR is deterministic. Reset clears LOCK. Pulse
transients and the unpowered package were not simulated. Sensors and decoupling are specified, not drawn. The chip cannot be
ordered until ChipFoundry confirms that a shuttle accepts ReRAM.

**Next steps.** Send `docs/QUESTIONS.md` to ChipFoundry. Design the test board. Draw the one-of-three array, the sensors
and the decoupling for the next chip (`NEXT_CHIP_SPEC.md`).
