# QA gates

## Gate 1 (roadmap)
- The circuit-level TVLA must not reuse the behavioural model's own assumptions silently: noise level, traces per group and
  device spreads must be stated, and the 2T2R result must reproduce a leak (a test that cannot fail proves nothing).
- Formal on the option: a property set that never mentions Z proves nothing about Z; planted Z faults must make it fail.
- The macro drawn for 3T3R is not a chip: say so.
- Gate: PASS with concerns (formal and full mutation may exceed the sandbox's time; then run on the PC or report as not run).

## Gate 2 (8 November 2026, after execution, council and red team)

Checks run by the coordinator, not taken from the agents' word:
- Red-team R1 reproduced at 150,000 traces: aligned one-of-three 26.32; the agent's prediction was about 28.
- Zero count of the fixed matrix recomputed: 565.
- LOCK gaps confirmed in the RTL.
- Single-flip counts (9/9, 2/6) and C(n,k) checked by hand.
- Read-current ratios recomputed by the generators.
- Rotation fix modelled and run at 150,000 traces.
- `tests/test_claims.py`: 645 numbers, 0 stale.
- Page rendered with no script errors and no horizontal overflow at 400 px.

Findings:
- **FAIL → fixed:** the draft 0.1 claims ("by construction", "second-order residual", "foundry's precheck", "unchanged and
  verified", "constant-conductance") overstated the evidence. Draft 0.2 is regenerated with narrowed claims.
- **CONCERN (open):**
  - The full mutation campaign on the option is still running.
  - The rotation and the LOCK fix are proposals only.
  - The open experiments listed in `council/00_synthesis.md`.
- **CONCERN (open):** the device states of the tile model (SkyWater's published 60 / 4.5 µS) differ from what the drawn drivers
  program (about 30 / 0.3 µS). The cost table shows both. The leakage runs use the published states only.

Gate: **CONCERNS**. The work is correct as stated, and the claims match the evidence. The paper is not ready for TCHES.
