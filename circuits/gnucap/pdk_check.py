"""Run the IHP PDK's own Gnucap reference tests for the PSP103 MOS models (low- and high-voltage devices)
and compare the output with the reference files shipped in the PDK.
The RF-variant plugins are not built here, so their `load` line is dropped and the *_rf tests are skipped;
the Monte Carlo tests (*_mc_*) are skipped as well.
Second stage: the Id-Vd sweeps are compared number by number with the NGSPICE reference outputs that the PDK
ships (tests/ngspice/*/ref), which come from the official OSDI models. Writes results/pdk_check.json."""
import json, os, re, subprocess, sys
from pathlib import Path

import numpy as np

import gnucap_run as g

IHP = Path(os.environ["IHP_GNUCAP"])
OUT = Path(__file__).resolve().parents[2] / "results"
GNUCAP = os.environ.get("GNUCAP", "gnucap")


def run_dir(name):
    src, dst = IHP / "tests" / "gnucap" / name, IHP / "tests" / "gnucap" / (name + "_norf")
    dst.mkdir(exist_ok=True)
    for f in list(src.glob("*.va")) + list(src.glob("*.gc")):
        (dst / f.name).write_text("".join(l for l in f.read_text().splitlines(True) if "_rf_paramset.so" not in l))
    res = {}
    for gc in sorted(dst.glob("*.gc")):
        if "_rf" in gc.name or "_mc_" in gc.name:
            continue
        r = subprocess.run([GNUCAP, gc.name], cwd=dst, capture_output=True, text=True, timeout=900)
        lines = (r.stdout + r.stderr).splitlines()[11:]
        got = [l for l in lines if not (l.startswith("stashing as") or "already installed" in l or l.startswith("@@"))]
        ref = (src / "ref" / (gc.name + ".out")).read_text().splitlines()
        res[gc.name] = dict(passed=got == ref, lines=len(ref))
    return res


def against_ngspice(name):
    """Gnucap (this build) against the PDK's ngspice reference, all points with |I| > 100 nA."""
    gdir, ndir = IHP / "tests" / "gnucap" / (name + "_norf"), IHP / "tests" / "ngspice" / name / "ref"
    res = {}
    for gc in sorted(gdir.glob("*id_vd_ng*.gc")):
        ref = ndir / gc.name.replace(".gc", ".sp.out")
        if "_rf" in gc.name or gc.name.startswith("aud_") or not ref.exists():
            continue
        nd = np.loadtxt(ref, skiprows=1)
        tmp = gdir / ("aud_" + gc.name)
        tmp.write_text(gc.read_text().replace("print dc", "options numdgt 9\nprint dc"))
        r = subprocess.run([GNUCAP, tmp.name], cwd=gdir, capture_output=True, text=True, timeout=900)
        tmp.unlink()
        rows = []
        for line in r.stdout.splitlines():
            t = line.split()
            if len(t) == 4:
                try:
                    rows.append([g.num(x) for x in t])
                except ValueError:
                    pass
        gd = np.array(rows)
        if gd.shape[0] != nd.shape[0]:
            res[gc.name] = dict(error=f"{gd.shape[0]} rows against {nd.shape[0]}")
            continue
        big = np.abs(nd[:, 2]) > 100e-9
        rel = np.abs(gd[big, 2] - nd[big, 2]) / np.abs(nd[big, 2])
        res[gc.name] = dict(points=int(big.sum()), max_rel_diff=float(rel.max()), median_rel_diff=float(np.median(rel)))
    return res


if __name__ == "__main__":
    out = {d: run_dir(d) for d in ("moslv", "moshv")}
    ng = {d: against_ngspice(d) for d in ("moslv", "moshv")}
    worst = max(t.get("max_rel_diff", 1.0) for v in ng.values() for t in v.values())
    npts = sum(t.get("points", 0) for v in ng.values() for t in v.values())
    print(f"against the PDK's ngspice reference: {sum(len(v) for v in ng.values())} Id-Vd sweeps, {npts} points above 100 nA, "
          f"largest relative difference {worst:.2e}")
    tot = sum(len(v) for v in out.values()); ok = sum(t["passed"] for v in out.values() for t in v.values())
    for d, v in out.items():
        print(d, f"{sum(t['passed'] for t in v.values())} of {len(v)} reference tests identical;", sum(t["lines"] for t in v.values()), "output lines compared")
        for n, t in v.items():
            if not t["passed"]:
                print("   FAIL", n)
    out["against_ngspice"] = ng
    out["summary"] = dict(tests=tot, identical=ok, ngspice_sweeps=sum(len(v) for v in ng.values()), ngspice_points=npts, ngspice_max_rel_diff=worst)
    (OUT / "pdk_check.json").write_text(json.dumps(out, indent=1))
    sys.exit(0 if ok == tot and worst < 5e-3 else 1)
