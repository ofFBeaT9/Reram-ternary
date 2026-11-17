# Technology landscape for the USN brief: m1frame run record (17 November 2026)

Mode C (native). Output: section 11 of `paper-v1-2026-11-14/BOS_BRIEF.md`, figures `fig/brief_nodes.png` and
`fig/brief_maturity.png` (`figures_landscape.py`).

Plan: production status of leading nodes; imec roadmap and the meaning of "sub-1 nm"; 2D, CNFET, ternary devices; photonic,
neuromorphic, memristor CIM; qubits and qudits; trends; whether to add a radix.

QA gate 1: production status comes from company statements, not journals; label projections; the maturity chart is the
author's placement and must say so.

Execution: 12 web searches (standard and extended). Journal facts read from publisher pages, abstracts or indexes (DOI, volume,
pages). The OpenPlanter agent did not run (its backend is not reachable from here); its method was followed by hand: name each
entity, check it in a second source, keep the evidence chain in the source list.

Fact checks, two sources each:
- 2D RISC-V: 5,900 transistors (China Daily; Nature DOI index).
- Willow: distance 7, 0.143 % per cycle, Lambda 2.14 (arXiv 2408.13687; Nature index).
- Qudit QEC gains 1.82 and 1.87 (arXiv 2409.15065; Nature PMC copy).
- Hala Point: 1.15 billion neurons, 1,152 chips, 2,600 W (Intel newsroom).
- imec: CFET at A7 (imec article; TrendForce). Gate pitch about 42 nm from A10 to A5 (TrendForce only).

Found on the way: imec's A2 date moved from 2036–2039 (older reports) to the 2040s (2026 reports), and press sources disagree
by a year on A10 and A7. The brief states the shift.

QA gate 2 (self-audit; no council, to keep the run short):
- Weakest items: the 2-billion-neuron system (secondary source, labelled), the gate-pitch figures (one trade-press source), and
  the photonic numbers (taken from a review's summary).

Gate: PASS with concerns.
