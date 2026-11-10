"""Collect the verification of revision 4.9 (9 November 2026: locked at reset, erase of the whole array to unlock,
programming refused under LOCK, LOCK in three flip-flops) from the result files into results/rev49/summary.json.
A file that does not exist yet shows as null. Usage: python3 tools/collect_rev49.py"""
import json, re
from pathlib import Path

R = Path(__file__).resolve().parents[1] / "results"
NEW_MUT = ("LOCK not set by reset (revision 4.9)", "programming runs under LOCK", "programming under LOCK without WERR",
           "erase never clears LOCK", "erase clears LOCK despite WERR", "erase ends before the last row", "erase skips every other row",
           "erase programs PDATA instead of weight 0", "erase stops at verify with VARPROG (not constant time)", "LOCK held in one copy only",
           "erase starts row 0 without resetting P", "erase rows after the first without resetting N")
NEW_FORMAL = ("LOCK not set by reset", "programming runs under LOCK", "erase clears LOCK despite WERR", "erase ends before the last row",
              "erase skips every other row", "erase programs PDATA instead of weight 0", "erase never ends (repeats row 0)")


def tb(n):
    f = R / n
    if not f.exists():
        return None
    t = f.read_text(); m = re.findall(r"(\d+) checks, (\d+) failures", t)
    return dict(checks=int(m[-1][0]), failures=int(m[-1][1]), passed="TEST PASSED" in t) if m else None


def js(n):
    f = R / n
    return json.loads(f.read_text()) if f.exists() else None


def mut(n):
    d = js(n)
    if d is None:
        return None
    res = d.get("results", [])
    new = [r for r in res if r["name"] in NEW_MUT]
    return dict(faults=d["faults"], run=d.get("run", len(res)), detected=d["detected"], not_detected=d.get("not_detected", []),
                new_faults=len(new), new_caught=sum(r["status"] == "caught" for r in new))


def formal():
    """Revision 4.9 proofs as far as they have closed (results/rev49/formal/, copied from the PC batches 29h, 29i, 29j).
    The PDR tasks over the whole property set had not closed when revision 4.9 was committed; they are listed as open."""
    F = R / "rev49" / "formal"
    done = lambda n: (F / n).exists() and "DONE (PASS" in (F / n).read_text()
    passed = {"serial port (tcim_spi)": done("spi.log"), "start row = LFSR mod 72 (lfsr)": done("lfsr.log"),
              "LOCK set by reset (lock)": done("lock.log"), "timing miter (prove)": done("miter_prove.log"),
              "timing miter, BSD-PNX (prove_pnx)": done("miter_prove_pnx.log"),
              "safety, revision 4.7 properties (variant A)": done("safety_variant_A.log"),
              "safety, + under LOCK no pulse or read-back, erase writes weight 0 (variant B)": done("safety_variant_B.log"),
              "safety, + erase visits rows 0 to 71 in order and ends after 71 (variant C)": done("safety_variant_C.log")}
    secs = {}
    for n, f in (("A", "safety_variant_A.log"), ("B", "safety_variant_B.log"), ("C", "safety_variant_C.log")):
        m = re.search(r"Elapsed clock time \[H:MM:SS \(secs\)\]: \S+ \((\d+)\)", (F / f).read_text()) if (F / f).exists() else None
        secs[n] = int(m.group(1)) if m else None
    open_ = ["safety with the unlock property (LOCK clears only after an erase of all 72 rows without WERR)",
             "safety, BSD-PNX code", "progress (every command ends in bounded time)", "safety on the 3T3R build",
             "planted proof faults (check_faults.py) for the revision 4.9 properties"]
    cex = F / "miter_prove_batch29_counterexample.log"
    return dict(passed=passed, n_passed=sum(passed.values()), variant_seconds=secs, open=open_,
                miter_counterexample_before_fix=(cex.exists() and "step 6270" in cex.read_text()))


def equiv(b):
    f = R / "rev49" / f"equiv_vs_rev48_{b}.log"
    if not f.exists():
        return None
    m = re.search(r"Of those cells (\d+) are proven and (\d+) are unproven", f.read_text())
    sig = (R / "rev49" / f"equiv_vs_rev48_unproven_{b}.txt").read_text().split()
    return dict(proven=int(m.group(1)), unproven=int(m.group(2)), signals=sig)


def fuzz():
    f = R / "spi_fuzz_1M.log"
    return f.read_text().strip().splitlines()[-1] if f.exists() else None


lint = R / "rev49" / "lint.log"
S = dict(
    revision="4.9", date="2026-11-09",
    erase_cycles=(lambda f: int(re.search(r"erase: 72 rows x \(21 \+ 21\) pulse steps, (\d+) cycles", f.read_text()).group(1)) if f.exists() and "erase: 72" in f.read_text() else None)(R / "rtl_test.log"),
    tb={n: tb(n) for n in ("rtl_test.log", "rtl_test_pnx.log", "rtl_test_verilator.log", "rtl_test_verilator_pnx.log",
                           "next_chip/rtl_test_1of3.log", "next_chip/rtl_test_1of3_pnx.log", "sky130_chip/rtl_chip_000.log",
                           "sky130_chip/rtl_chip_110.log", "sky130_chip/rtl_chip_321.log", "next_chip/rtl_chip_1of3_110.log")},
    mutation={n: mut(n) for n in ("rtl_mutation.json", "rtl_mutation_pnx.json", "rtl_mutation_1of3full.json")},
    mutation_chip={n: js(n) and dict(faults=js(n)["faults"], detected=js(n)["detected"])
                   for n in ("sky130_chip/mutation_chip.json", "next_chip/mutation_chip_1of3.json")},
    formal=formal(), equiv_vs_rev48={b: equiv(b) for b in ("default", "1of3")},
    lint_warnings=(len(re.findall(r"%Warning", lint.read_text())) if lint.exists() else None), fuzz=fuzz())
(R / "rev49").mkdir(exist_ok=True)
(R / "rev49" / "summary.json").write_text(json.dumps(S, indent=1))
print(json.dumps(S, indent=1)[:3000])
