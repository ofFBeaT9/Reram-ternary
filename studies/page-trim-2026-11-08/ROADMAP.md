# Page trim, revision 4.8, open issues, 4T4R (8 November 2026), m1frame mode C

**Analyst.** The explainer is the 12 October (4.5) page with sections added on top. It is long and repeats itself, it
contradicts itself (4.5 numbers in sections 1-12 next to 4.7 numbers in 13), it does not mention revision 4.8, and it lists
the open issues of 4.7 without saying which still stand. The owner thought the design had moved to 4T4R cells; it has not.
The next-chip plan is the one-of-three cell (3T3R), and nothing has compared 4T4R with it.

**PM.** Goal: one short, consistent page that someone can read in about 10 minutes.
- Requirements: every number comes from `results/`; it covers 4.5 to 4.8 and the TTPU-Gen2 fixes; it has one table of
  open issues (open / closed / next chip); it answers 4T4R; it keeps the USN asks.
- Out of scope: new RTL, new layout, the full-system simulation.
- Success: `make test` passes; no number differs from its results file; the page is under 1/3 of the present length;
  no horizontal scrolling at 400 px.

**Architect.**
- A new generator, `docs/page/build.py`, reads `results/` and writes `docs/TCIM0_explainer.html`. It reuses the styling of
  the old page; the old 4.5 content stays in `docs/STATUS.md`.
- 4T4R gets a case in the leak model (`tools/tvla_tcim0.py`, `--only`), with the same traces and seed as the one-of-three case.
- The open issues are triaged against the files (proofs, tests, simulations) into: closed (with evidence), stands for
  this chip (stated limit), next chip.

**Scrum.**
1. 4T4R leak-model run; comparison table (area, devices, sense amplifiers, \|t\|).
2. Triage of the open issues.
3. Build the new page and check it.
4. Council: page accuracy against the results; triage and 4T4R. Red-team.
5. Publish; `make test`; sync.
