# Council brief (6 November 2026)

Repository: /home/claude/reram-ternary (read CLAUDE.md first; a working copy restored from the owner's PC, which holds the
master). Study folder: studies/hw-security-2026-11/ (ROADMAP.md, QA_GATE.md, NEXT_CHIP_SPEC.md; the input document is
input_AI_Hardware_Hacking_m1.pdf). Tools such as yosys/sby/verilator are NOT installed in this working copy: review by reading.

What was done for the input document's checklist (revision 4.6 of TCIM0):
- RTL rtl/tcim_core.sv: fixed-latency products (all 72 rows, LFSR start row; ZSKIP opt-in), dummy accumulators
  (constant activity, ACT +50), constant-time programming (21 + 21 pulse steps, empty-mask pulses; VARPROG opt-in), SEC
  register (+3) with set-only LOCK, margin check (PCMD 0,+; MARG +52). Formal properties under `ifdef FORMAL` in the same file.
- Formal: formal/tcim_core.sby (safety, safety_pnx, progress), formal/tcim_miter.sv/.sby (two-copy timing miter),
  formal/check_faults.py (faults that must make proofs fail). PC logs: flow/eda/formal24/ are not in this copy; results are
  being rerun on the PC (batch 25).
- Test bench tb/tb_tcim.cc; mutation faults tb/mutation_test.py; results/rtl_mutation.json, results/rtl_mutation_pnx.json.
- Models: tools/tvla_tcim0.py -> results/security/tvla.json; chip/sky130/sim/sa_power.py -> results/security/sa_power.json;
  chip/sky130/sim/idle_impedance.py -> results/security/idle_impedance.json.
- Chip: results/sky130_chip/digital_block.json, area_estimate.json, top_layout.json, top_signoff.json; FPGA results/fpga/rev46.
- Page section draft: docs/page/security_section.py (prints the HTML section from results).

Rules: being correct is the only option; every number must come from a file in results/ or a script here; a simulation
is evidence about the model, not silicon; proposals are labelled as proposals.
