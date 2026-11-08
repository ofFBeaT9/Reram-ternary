"""Add the PC's DRC and LVS results (layout/periph_checks.log, copied to results/periph_layout/) to
results/periphery_layout.json."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results" / "periphery_layout.json"
log = (ROOT / "results" / "periph_layout" / "periph_checks.log").read_text(encoding="utf-8", errors="ignore")
res = json.loads(R.read_text())
kl = re.search(r"KLayout (\S+)", log)
res["checks"] = dict(tool=f"KLayout {kl.group(1) if kl else '?'} in openroad/orfs:26Q4-71-g9b26ff8ff, IHP-Open-PDK 5e6d592e decks "
                          "(DRC without density; LVS run_lvs.py defaults)")
for c in res["cells"]:
    drc = re.search(rf"^{c} DRC: .*$", log, re.M).group(0)
    lvs = re.search(rf"^{c} LVS: .*$", log, re.M).group(0)
    flt = re.search(rf"^{c} LVS with fault: .*$", log, re.M).group(0)
    res["cells"][c]["drc_clean"] = "Check Passed" in drc
    res["cells"][c]["lvs_match"] = "PASS (netlists match)" in lvs
    res["cells"][c]["lvs_detects_injected_fault"] = "FAIL (netlists do not match)" in flt
R.write_text(json.dumps(res, indent=1))
print(json.dumps({c: {k: v for k, v in d.items() if k in ("drc_clean", "lvs_match", "lvs_detects_injected_fault")} for c, d in res["cells"].items()}))
