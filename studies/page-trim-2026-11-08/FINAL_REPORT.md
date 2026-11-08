# Page trim, revision 4.8, open issues, 4T4R: final report (8 November 2026)

**Verdict.** The page is rewritten short (2,447 words, from 14,125), covers revisions 4.5 to 4.8, and reads every result
from `results/`. Of the open issues of 4.7, 7 are closed (two only in the model), 16 remain on this chip (9 stated
limits, 7 fixed only by the next chip) and 3 wait on others (`TRIAGE.md`). The project never moved to 4T4R: this chip is
2T2R and the next-chip plan is one-of-three. On the leak model 4T4R and one-of-three both pass the weight test that 2T2R
fails; 4T4R needs a third more devices for no measured gain.

**New evidence.**
- 4T4R in the leak model: weights |t| 3.14, inputs 1.78 (one-of-three 3.13 / 2.61; 2T2R 14.24 / 3.59; pass < 4.5).
- H6 empty pulses: 32 transient runs, peaks 1.32 V / 1.05 V; device-model drift toward the read reference reaches 10 %
  after 2.2e5 full-array writes at 85 °C (1.1e9 at 27 °C); closed in the model against 10 × 10,000 writes.
- TTPU-Gen2 logs stored: SEC test 11 checks, 0 failures; 4 of 4 existing benches pass.

**Council.** Two specialist reviewers and one red team (real subagents), papers in `council/`. Every finding was fixed or
recorded as a concern in `QA_GATE.md`.

**Next.** Full-system simulation (needs REBEL-6 RTL or an instruction-set model); H6 with a capacitive device and mixed
columns; send `docs/QUESTIONS.md`.
