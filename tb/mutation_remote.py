"""The mutation test of tb/mutation_test.py split in two, so that the slow part runs on a machine with many cores
(revision 4.3: the owner's PC, 32 cores in the OpenROAD-flow-scripts image, which has a C++ compiler but no
SystemVerilog front end).

  python3 tb/mutation_remote.py gen <pack dir>        here (needs yosys with slang): every fault of both trit codes
        is applied to the RTL exactly as tb/mutation_test.py does, and converted to C++ with write_cxxrtl; the pack
        also holds the unchanged RTL of both codes (which must PASS), the test bench, its vectors and the CXXRTL
        runtime headers of the same Yosys.
  python3 mutation_remote.py run <pack dir> <jobs>     on the other machine (python3 and c++ only): compiles and runs
        every entry in parallel, with the criteria of tb/mutation_test.py, and writes <pack>/rtl_mutation_0_<n-1>.json
        and rtl_mutation_pnx_0_<n-1>.json plus baseline.json.
Then copy the two part files to results/ and run tb/mutation_merge.py and tb/mutation_merge.py _pnx as usual."""
import json, os, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent


def gen(pack):
    ROOT = HERE.parent
    sys.path.insert(0, str(HERE))
    pack.mkdir(parents=True, exist_ok=True)
    datdir = subprocess.run(["yosys-config", "--datdir"], capture_output=True, text=True).stdout.strip()
    shutil.copytree(f"{datdir}/include/backends/cxxrtl/runtime", pack / "cxxrtl_runtime", dirs_exist_ok=True)
    shutil.copytree(ROOT / "tb" / "vectors", pack / "vectors", dirs_exist_ok=True)
    shutil.copy(ROOT / "tb" / "tb_tcim.cc", pack / "tb_tcim.cc")
    shutil.copy(Path(__file__), pack / "mutation_remote.py")
    entries = []
    for enc in ("", "pnx"):
        os.environ["TB_ENC"] = enc
        import importlib
        import mutation_test as mt
        mt = importlib.reload(mt)
        defs = mt.DEFS
        tag = mt.TAG
        jobs = [(-1, "unchanged RTL (must pass)", None, None, None)] + [(k, *m) for k, m in enumerate(mt.M)]
        for k, name, fname, old, new in jobs:
            d = pack / f"m{tag}_{'base' if k < 0 else f'{k:02d}'}"
            d.mkdir(exist_ok=True)
            e = dict(id=k, name=name, tag=tag, defs=defs, dir=d.name)
            srcs = []
            for f in mt.RTL:
                s = (ROOT / "rtl" / f).read_text()
                if f == fname:
                    if s.count(old) != 1:
                        e["status"] = "NOT APPLIED"; e["detail"] = f"{s.count(old)} matches"
                    s = s.replace(old, new)
                (d / f).write_text(s)
                srcs.append(str(d / f))
            if "status" not in e:
                y = subprocess.run(["yosys", "-q", "-p", f"read_slang {' '.join('-D ' + x[2:] for x in defs)} --top tcim_top {' '.join(srcs)}; "
                                    f"hierarchy -top tcim_top; proc; flatten; opt; write_cxxrtl -header -namespace cxxrtl_design {d}/tcim_top.cc"],
                                   capture_output=True, text=True)
                if y.returncode:
                    e["status"] = "DOES NOT ELABORATE"; e["detail"] = (y.stdout + y.stderr)[-300:]
            for f in mt.RTL:
                (d / f).unlink()
            entries.append(e)
            print(e["tag"] or "default", k, e.get("status", "ready"), name[:70], flush=True)
    (pack / "manifest.json").write_text(json.dumps(entries, indent=1))


def run_one(pack, e):
    if "status" in e:
        return dict(name=e["name"], status=e["status"], detail=e.get("detail", ""))
    d = pack / e["dir"]
    c = subprocess.run(["c++", "-std=c++14", "-O1", *e["defs"], "-I", str(d), "-I", str(pack / "cxxrtl_runtime"),
                        str(pack / "tb_tcim.cc"), str(d / "tcim_top.cc"), "-o", str(d / "tb")], capture_output=True, text=True)
    if c.returncode:
        return dict(name=e["name"], status="DOES NOT COMPILE", detail=c.stderr[-300:])
    t0 = time.time()
    env = dict(os.environ) if e["id"] < 0 else dict(os.environ, TB_FAIL_FAST="1")
    try:
        r = subprocess.run([str(d / "tb"), str(pack / "vectors")], capture_output=True, text=True, timeout=1500, env=env)
        out = r.stdout
        caught = "TEST FAILED" in out or r.returncode != 0
        first = next((l.strip() for l in out.splitlines() if "FAIL:" in l), "")
        stage = [l for l in out.splitlines() if l[:1].isdigit()]
        res = dict(name=e["name"], status="caught" if caught else "SURVIVED", first_failure=first,
                   in_test=stage[-1][:40] if stage else "", seconds=round(time.time() - t0))
        if e["id"] < 0:
            res["summary"] = [l for l in out.splitlines() if "checks" in l or "TEST" in l]
    except subprocess.TimeoutExpired:
        res = dict(name=e["name"], status="caught", first_failure="test bench did not finish (hang)", in_test="", seconds=1500)
    return res


def run(pack, jobs):
    entries = json.loads((pack / "manifest.json").read_text())
    with ThreadPoolExecutor(jobs) as ex:
        results = list(ex.map(lambda e: run_one(pack, e), entries))
    base = {}
    for tag in ("", "_pnx"):
        rows = []
        for e, r in zip(entries, results):
            if e["tag"] != tag:
                continue
            if e["id"] < 0:
                base[tag or "default"] = dict(r, passed=r["status"] == "SURVIVED")   # the unchanged RTL must pass
                continue
            r["id"] = e["id"]
            rows.append(r)
        (pack / f"rtl_mutation{tag}_0_{len(rows) - 1}.json").write_text(json.dumps(rows, indent=1))
        print(tag or "default", sum(r["status"] == "caught" for r in rows), "of", len(rows), "caught")
    (pack / "baseline.json").write_text(json.dumps(base, indent=1))
    print("unchanged RTL:", {k: v["passed"] for k, v in base.items()})


if __name__ == "__main__":
    if sys.argv[1] == "gen":
        gen(Path(sys.argv[2]).resolve())
    else:
        run(Path(sys.argv[2]).resolve(), int(sys.argv[3]))
