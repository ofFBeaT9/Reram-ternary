# QA gates

## Gate 1 (plan)
- Risk: rewriting the page by hand reintroduces stale numbers. Fix: every number is read from `results/` by the
  generator, and the council checks the page against the files.
- Risk: the 4T4R result is only as good as its reading of Gemini's text ("exactly one LRS of four" for three values
  leaves one device always high-resistance). Fix: state that reading on the page.
- Gate 1: PASS.

## Gate 2 (8 November 2026): after execution and council

| Check | Result |
|---|---|
| Page length | 2,447 words (old page 14,125); no horizontal page scroll at 400 px |
| Numbers | `make test`: 596 numbers, 0 stale (new: 4T4R leak model, H6 empty pulses) |
| Council 01 (triage, 4T4R) | 1 blocker fixed (weights recoverable through products under LOCK: new row, stands); 5 rows added; 4T4R wording narrowed to "passes the test" |
| Council 02 (page accuracy) | TPU logs now stored (`results/ttpu_gen2/`), unsupported "2 of 5 before" removed; figure captions corrected; overclaims ("logic proven", "signed off") reworded; verification table cut from 27 to 11 rows |
| Council 03 (red team) | Both H6 blockers fixed: gap drift accumulated separately (no float loss), 120 µS (outside the model) replaced by 100 µS, drift counted toward the reference only, three conditions (27 °C, 85 °C, fastest-reset cell); personal path removed; opening claim narrowed |
| H6 | 32 of 32 runs finished (one needed Gear integration); closed in the model, margin 2.2× at 85 °C |

**Gate: PASS with concerns.** Concerns: the H6 margin at 85 °C is thin and the deck has no device or junction capacitance;
the 4T4R/one-of-three comparison is total-current only; 21 of the 32 H6 records were rebuilt from the run log after a
time-out (`results/security/empty_pulse_run3.log`; |V| per device and VPRG current not kept for those).
