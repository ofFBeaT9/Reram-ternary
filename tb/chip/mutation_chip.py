"""Mutation test of the chip test bench (11 October 2026): inject one bug at a time into the array controller
rtl/chip/tcim_actl.sv and check that the chip build of tb/tb_tcim.cc (line-level macro model, TB_CFG=1,1,0) fails.
Usage: python3 tb/chip/mutation_chip.py [first] [last] | count      Writes results/sky130_chip/mutation_chip.json
(or mutation_chip_<first>_<last>.json for a part). Needs yosys with slang and a C++ compiler."""
import json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RTL = ["rtl/tcim_pkg.sv", "rtl/tcim_core.sv", "rtl/tcim_spi.sv", "rtl/tcim_top.sv", "rtl/chip/tcim_actl.sv", "rtl/chip/tcim_chip_core.sv"]
CXXRTL = subprocess.run(["yosys-config", "--datdir"], capture_output=True, text=True).stdout.strip() + "/include/backends/cxxrtl/runtime"
F = "rtl/chip/tcim_actl.sv"
# CHIP_CELL=1of3: the next-chip 3T3R build (8 November 2026), faults of list MZC in the Z bit-line logic only
CELL3 = os.environ.get("CHIP_CELL", "") == "1of3"
DEFS = ["-DTCIM_CELL_1OF3"] if CELL3 else []

# (name, text to replace in tcim_actl.sv (exactly once), replacement)
M = [
    ("reset pulse: bit-line polarity of P devices inverted", "blp_prg <= is_set ? mp : (is_rst ? ~mp : '0);", "blp_prg <= is_set ? mp : (is_rst ? mp : '0);"),
    ("reset pulse: source lines not at the program rail", "sl_prg  <= is_rst;", "sl_prg  <= 1'b0;"),
    ("set pulse: N bit lines follow the P mask", "bln_prg <= is_set ? mn :", "bln_prg <= is_set ? mp :"),
    ("word line off and lines released in the same cycle (no WLOFF)", "wl_on <= '0; pstb <= 1'b0;\n                        st <= A_WLOFF;",
     "wl_on <= '0; pstb <= 1'b0;\n                        st <= A_REL;"),
    ("no settling time before the word line", "cnt <= pow2m1({1'b0, cfg_ts} + 4'd1);", "cnt <= '0;"),
    ("pulse one power of two too short", "pow2m1({1'b0, cfg_tp} + 4'd2)", "pow2m1({1'b0, cfg_tp} + 4'd1)"),
    ("sense time one power of two too short", "pow2m1({2'b0, cfg_tr} + 4'd2)", "pow2m1({2'b0, cfg_tr} + 4'd1)"),
    ("set verify uses the mid reference", "(op == OP_VFY_SET) ? 3'b100", "(op == OP_VFY_SET) ? 3'b010"),
    ("reset verify uses the mid reference", "(op == OP_VFY_RESET) ? 3'b001", "(op == OP_VFY_RESET) ? 3'b010"),
    ("read uses the set-target reference", "(is_rd ? 3'b010 : 3'b000)", "(is_rd ? 3'b100 : 3'b000)"),
    ("second sampling flip-flop bypassed (samples after the word line)", "arr_sa_p <= is_rd ? q1_p : '0;", "arr_sa_p <= is_rd ? sa_p : '0;"),
    ("sense outputs of P and N exchanged", "q1_p <= sa_p; q1_n <= sa_n;", "q1_p <= sa_n; q1_n <= sa_p;"),
    ("word line of the neighbouring row", "wl_on[row] <= 1'b1;", "wl_on[row ^ 7'd1] <= 1'b1;"),
    ("pulses on the read rail", "wl_prog <= ~is_rd;                            // word-line rail", "wl_prog <= 1'b0;                            // word-line rail"),
    ("pulse strobe never raised", "wl_on[row] <= 1'b1; pstb <= ~is_rd;", "wl_on[row] <= 1'b1; pstb <= 1'b0;"),
    ("pulse kind output always set", "pk <= (arr_op == OP_PULSE_RST);", "pk <= 1'b0;"),
    ("amplitude output one step high", "pamp <= arr_amp;", "pamp <= arr_amp + 5'd1;"),
    ("bit lines on the sense amplifiers during pulses", "bl_sen  <= is_rd;", "bl_sen  <= 1'b1;"),
    ("lines left floating after an operation", "flt <= 1'b0;\n                    arr_ack <= 1'b1;", "arr_ack <= 1'b1;"),
    ("no break before make when lines leave ground", "flt <= 1'b1;\n                        st <= A_BRK;", "st <= A_BRK;"),
    ("no break before make when lines return to ground", "flt <= 1'b1;\n                    st <= A_REL;", "st <= A_REL;"),
    ("flt dropped in the cycle the rails switch on", "st <= A_MAKE;", "flt <= 1'b0; st <= A_MAKE;"),
    ("lines float after reset", "sl_prg <= 1'b0; flt <= 1'b0;", "sl_prg <= 1'b0; flt <= 1'b1;"),
    ("acknowledge one cycle early (before the lines are grounded)", "A_REL: begin", "A_REL: begin arr_ack <= 1'b1;"),
    ("an analog-sum request drives the array", "if (arr_op == OP_SUM || arr_op > OP_SUM || arr_row >= 7'(ROWS)) begin", "if (arr_op > OP_SUM || arr_row >= 7'(ROWS)) begin"),
    ("request parameters not latched (mask read live)", "op <= arr_op; row <= arr_row; mp <= arr_mask_p; mn <= arr_mask_n;", "op <= arr_op; row <= arr_row; mn <= arr_mask_n;"),
]

MZC = [
    ("1of3: set pulse, Z bit lines follow the P mask", "`ZA(blz_prg <= is_set ? mz :", "`ZA(blz_prg <= is_set ? mp :"),
    ("1of3: reset pulse, Z bit-line polarity inverted", "(is_rst ? ~mz : '0);)", "(is_rst ? mz : '0);)"),
    ("1of3: Z sense output never sampled", "`ZA(q1_z <= sa_z;)", "`ZA(q1_z <= '0;)"),
    ("1of3: Z sampled after the word line (second flip-flop bypassed)", "`ZA(arr_sa_z <= is_rd ? q1_z : '0;)", "`ZA(arr_sa_z <= is_rd ? sa_z : '0;)"),
    ("1of3: Z bit line not released", "`ZA(blz_prg <= '0;) sl_prg <= 1'b0;", "sl_prg <= 1'b0;"),
    ("1of3: Z mask of the request not taken", "`ZA(mz <= arr_mask_z;)", "`ZA(mz <= '0;)"),
]
if CELL3:
    M = MZC


def run(k, name, old, new):
    d = ROOT / "tb" / "build" / f"mutchip{k:02d}"
    shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True)
    srcs = []
    for f in RTL:
        s = (ROOT / f).read_text()
        if f == F:
            if s.count(old) != 1:
                return dict(name=name, status="NOT APPLIED", detail=f"{s.count(old)} matches")
            s = s.replace(old, new)
        (d / Path(f).name).write_text(s); srcs.append(str(d / Path(f).name))
    y = subprocess.run(["yosys", "-q", "-p", f"read_slang {' '.join('-D ' + x[2:] for x in DEFS)} --top tcim_chip_core {' '.join(srcs)}; hierarchy -top tcim_chip_core; proc; flatten; opt; "
                        f"write_cxxrtl -header -namespace cxxrtl_design {d}/tcim_chip_core.cc"], capture_output=True, text=True)
    if y.returncode:
        return dict(name=name, status="DOES NOT ELABORATE", detail=(y.stdout + y.stderr)[-300:])
    c = subprocess.run(["c++", "-std=c++14", "-O1", "-DTCIM_CHIP", *DEFS, "-I", str(d), "-I", CXXRTL, str(ROOT / "tb" / "tb_tcim.cc"),
                        str(d / "tcim_chip_core.cc"), "-o", str(d / "tb")], capture_output=True, text=True)
    if c.returncode:
        return dict(name=name, status="DOES NOT COMPILE", detail=c.stderr[-300:])
    t0 = time.time()
    try:
        r = subprocess.run([str(d / "tb"), str(ROOT / "tb" / "vectors")], capture_output=True, text=True, timeout=3000,
                           env=dict(os.environ, TB_FAIL_FAST="1", TB_CFG="1,1,0"))
        out = r.stdout
        caught = "TEST FAILED" in out or r.returncode != 0
        first = next((l.strip() for l in out.splitlines() if "FAIL:" in l), "")
        stage = [l for l in out.splitlines() if l[:1].isdigit()]
        res = dict(name=name, status="caught" if caught else "SURVIVED", first_failure=first, in_test=stage[-1][:40] if stage else "",
                   seconds=round(time.time() - t0))
    except subprocess.TimeoutExpired:
        res = dict(name=name, status="caught", first_failure="test bench did not finish (hang)", in_test="", seconds=3000)
    shutil.rmtree(d, ignore_errors=True)
    return res


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "count":
        print(len(M)); sys.exit(0)
    a = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    b = int(sys.argv[2]) if len(sys.argv) > 2 else len(M) - 1
    whole = (a, b) == (0, len(M) - 1)
    out = (ROOT / "results" / "next_chip" / "mutation_chip_1of3.json") if CELL3 else (ROOT / "results" / "sky130_chip" / ("mutation_chip.json" if whole else f"mutation_chip_{a}_{b}.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    res = []
    for k in range(a, b + 1):
        r = run(k, *M[k]); r["id"] = k; res.append(r)
        print(k, r["status"], "|", r["name"], "|", r.get("first_failure", r.get("detail", ""))[:110], "|", r.get("seconds", ""), flush=True)
        out.write_text(json.dumps(dict(faults=len(M), run=len(res), detected=sum(x["status"] == "caught" for x in res), results=res), indent=1))
    sys.exit(0 if all(x["status"] == "caught" for x in res) else 1)
