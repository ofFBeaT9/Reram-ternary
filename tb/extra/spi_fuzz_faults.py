"""Can the serial-port fuzzer fail? Plant one fault at a time in rtl/tcim_spi.sv, rebuild the CXXRTL model, run
tb/extra/spi_fuzz.cc; every fault must make it fail. Also runs the unchanged design. Writes results/spi_fuzz.json.
Usage: python3 tb/extra/spi_fuzz_faults.py <frames>   (yosys with slang and g++ on the path)"""
import json, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
N = sys.argv[1] if len(sys.argv) > 1 else "200000"
F = [("none (the design as it is)", None, None),
     ("a frame cut at 55 clocks writes", "if (bitcnt == 7'd55 && cmd[7]) begin", "if (bitcnt == 7'd54 && cmd[7]) begin"),
     ("bit counter not cleared when CS rises", "bitcnt <= '0; miso <= 1'b0;", "miso <= 1'b0;"),
     ("error flag not latched on a write", "if (bus_we) err_latch <= bus_err;", ""),
     ("read launched one bit late (address shifted)", "if (bitcnt == 7'd7) begin", "if (bitcnt == 7'd8) begin")]
inc = subprocess.run(["yosys-config", "--datdir"], capture_output=True, text=True).stdout.strip() + "/include/backends/cxxrtl/runtime"
res = []
for name, old, new in F:
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        for f in ("tcim_pkg.sv", "tcim_core.sv", "tcim_spi.sv", "tcim_top.sv"):
            t = (ROOT / "rtl" / f).read_text()
            if f == "tcim_spi.sv" and old:
                assert t.count(old) == 1, name; t = t.replace(old, new)
            (d / f).write_text(t)
        rtl = " ".join(str(d / f) for f in ("tcim_pkg.sv", "tcim_core.sv", "tcim_spi.sv", "tcim_top.sv"))
        subprocess.run(["yosys", "-q", "-p", f"read_slang --top tcim_top {rtl}; hierarchy -top tcim_top; proc; flatten; opt; "
                        f"write_cxxrtl -header -namespace cxxrtl_design {d}/tcim_top.cc"], check=True)
        subprocess.run(["g++", "-std=c++14", "-O2", "-I", str(d), "-I", inc, str(ROOT / "tb/extra/spi_fuzz.cc"), str(d / "tcim_top.cc"),
                        "-o", str(d / "fz")], check=True)
        r = subprocess.run([str(d / "fz"), N, "1"] if old is None else [str(d / "fz"), "20000", "1"], capture_output=True, text=True)
        passed = "FUZZ PASSED" in r.stdout
        res.append(dict(fault=name, frames=int(N) if old is None else 20000, fuzz_passed=passed,
                        ok=passed if old is None else not passed, summary=r.stdout.strip().splitlines()[0] if r.stdout else r.stderr[-200:]))
        print(name, "|", "passed" if passed else "FAILED", "|", res[-1]["summary"], flush=True)
(ROOT / "results" / "spi_fuzz.json").write_text(json.dumps(res, indent=1))
sys.exit(0 if all(x["ok"] for x in res) else 1)
