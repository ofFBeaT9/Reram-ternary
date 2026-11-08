"""Writes results/sky130_chip/precheck.json from a ChipFoundry precheck log (6 November 2026).
usage: python3 tools/precheck_summary.py <batch log> <precheck output dir> <run label>
The previous content of precheck.json is kept under "history"."""
import hashlib, json, re, sys
from pathlib import Path

log, outdir, label = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
t = log.read_text(errors="ignore")
checks = {m.group(2).strip(" ."): m.group(3) for m in re.finditer(r"\[\s*(\d+)/14\]\s+(.+?)\s+\.{3,}\s+(PASS|FAIL)", t)}
gds = Path("chip/sky130/caravan/gds/user_analog_project_wrapper.gds")
m = re.search(r"^([0-9a-f]{32})\s+/w/chip/sky130/caravan/gds/user_analog_project_wrapper.gds", t, re.M)
info = lambda f: (outdir / "logs" / f).read_text(errors="ignore").strip() if (outdir / "logs" / f).exists() else ""
old = json.loads(Path("results/sky130_chip/precheck.json").read_text()) if Path("results/sky130_chip/precheck.json").exists() else {}
hist = old.pop("history", [])
if old: hist.insert(0, {k: old[k] for k in ("tool", "run", "gds_md5", "passed", "total") if k in old})
res = dict(tool="cf-precheck " + (re.search(r"cf-precheck (\S+)", t).group(1) if re.search(r"cf-precheck (\S+)", t) else "?") + ", --magic-drc, all checks",
           run=label, gds_md5=m.group(1) if m else None,
           gds_md5_here=hashlib.md5(gds.read_bytes()).hexdigest() if gds.exists() else None,
           checks=checks, passed=sum(v == "PASS" for v in checks.values()), total=len(checks),
           tools_info=info("tools.info"), pdks_info=info("pdks.info"), history=hist)
Path("results/sky130_chip/precheck.json").write_text(json.dumps(res, indent=1))
print({k: v for k, v in res.items() if k not in ("history",)})
