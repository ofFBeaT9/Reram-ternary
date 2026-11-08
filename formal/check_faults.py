"""Are the formal proofs able to fail? Inject one fault at a time into rtl/tcim_core.sv and run the proof that
should catch it; every run must report FAIL. Writes ../results/formal_faults.json.
Usage: python3 formal/check_faults.py   (SBY = path to sby.py, default 'sby')"""
import json, os, shutil, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SBY = os.environ.get("SBY", "sby").split()
F = [
    ("pulse amplitude may reach 21", "safety", "end else if (amp == 5'(AMP_STEPS)) begin\n                        s_werr <= 1'b1; req <= 1'b0; state <= S_FINISH;\n                    end else begin\n                        arr_op <= OP_PULSE_RST;",
     "end else if (amp == 5'(AMP_STEPS + 1)) begin\n                        s_werr <= 1'b1; req <= 1'b0; state <= S_FINISH;\n                    end else begin\n                        arr_op <= OP_PULSE_RST;"),
    ("set pulse reaches devices that must stay in HRS", "safety", "arr_op <= OP_PULSE_SET; arr_amp <= amp; arr_mask_p <= pend_p & ~arr_sa_p;",
     "arr_op <= OP_PULSE_SET; arr_amp <= amp; arr_mask_p <= ~arr_sa_p;"),
    ("a reset pulse after the set phase has begun", "safety", "amp <= amp + 5'd1; r_piter <= r_piter + 6'(|{arr_mask_p, arr_mask_n});\n                    arr_op <= OP_VFY_SET; state <= S_SET_VFY;",
     "amp <= amp + 5'd1; r_piter <= r_piter + 6'(|{arr_mask_p, arr_mask_n});\n                    arr_op <= OP_PULSE_RST; state <= S_SET_VFY;"),
    ("PDATA writable while a program command runs", "safety", "if (wr && !s_busy) begin", "if (wr) begin"),
    ("product reads the same row again and again", "progress", "{1'b0, arr_row} + 8'd1", "{1'b0, arr_row}"),
    ("product reads rows with input 0", "safety", "assign x_nz = x_pos | x_neg;", "assign x_nz = '1;"),
    ("product skips rows with input -1", "safety", "assign x_nz = x_pos | x_neg;", "assign x_nz = x_pos;"),
    ("an all-zero product ends without DONE", "safety", "end else state <= S_FINISH;                  // all inputs 0", "end else state <= S_IDLE;                  // all inputs 0"),
    ("product ends before the last row", "safety", "for (int r = ROWS - 1; r >= 0; r--) if (nz[r]", "for (int r = ROWS - 2; r >= 0; r--) if (nz[r]"),
    # ---- revision 4.6 (security study): properties of the fixed-latency product, LOCK, margin check, empty pulses
    ("fixed latency: the same row read twice", "safety", "((arr_row == 7'(ROWS - 1)) ? 7'd0 : arr_row + 7'd1)", "arr_row"),
    ("fixed latency: product ends one row early", "safety", "(r_cnt == 7'(ROWS - 1)) ? 7'(ROWS)", "(r_cnt == 7'(ROWS - 2)) ? 7'(ROWS)"),
    ("LOCK cleared by a write", "safety", "                    if (is_pos(bus_wdata[7:6])) begin\n                        r_lock <= 1'b1;",
     "                    r_lock <= is_pos(bus_wdata[7:6]);\n                    if (is_pos(bus_wdata[7:6])) begin\n                        r_lock <= 1'b1;"),
    ("LOCK does not clear the options", "safety", "r_lock <= 1'b1; r_zskip <= 1'b0; r_varprog <= 1'b0; r_noshuf <= 1'b0;", "r_lock <= 1'b1;"),
    ("LOCK does not hide PITER", "safety", "r_lock ? ZERO_TRYTE : int_to_tryte({4'b0, r_piter})", "int_to_tryte({4'b0, r_piter})"),
    ("margin check pulses the array", "safety", "arr_op <= OP_VFY_SET; state <= S_MC_SET;", "arr_op <= OP_PULSE_SET; state <= S_MC_SET;"),
    ("empty pulses in stop-at-verify programming", "safety",
     "== '0 && (varprog_e || amp == 5'(AMP_STEPS))) begin\n                        amp <= '0;", "== '0 && (1'b0 || amp == 5'(AMP_STEPS))) begin\n                        amp <= '0;"),
    ("dummy accumulators updated only when the result is", "safety", "if (!(cur_nz && (arr_sa_p[c] ^ arr_sa_n[c])))", "if ((cur_nz && (arr_sa_p[c] ^ arr_sa_n[c])))"),
    # two-copy timing miter (tcim_miter.sby): each of these makes the timing depend on a secret
    ("miter: programming stops at verify (revision 4.5 behaviour)", "miter:prove",
     "== '0 && (varprog_e || amp == 5'(AMP_STEPS))) begin\n                        req <= 1'b0;", "== '0 && (1'b1 || amp == 5'(AMP_STEPS))) begin\n                        req <= 1'b0;"),
    ("miter: a failed reset phase ends the command", "miter:prove", "end else if (amp == 5'(AMP_STEPS) && !varprog_e) begin", "end else if (1'b0) begin"),
    ("miter: products skip rows with input 0 (revision 4.5 behaviour)", "miter:prove", "assign first_row = zskip_e ? next_nz", "assign first_row = 1'b1 ? next_nz"),
    ("miter: product ends at the last non-zero input", "miter:prove", "assign next_row  = zskip_e ? next_nz", "assign next_row  = 1'b1 ? next_nz"),
    # (with NOSHUF, which the miter leaves free, the first row then depends on a secret input; the first version of this
    #  fault used w_pos, declared after this line, so it did not elaborate: batch 24, 5 November 2026)
    # (council, 6 November 2026: faults for the two properties added then)
    ("NOSHUF ignored", "safety", "assign start_row  = noshuf_e ? 7'd0 :", "assign start_row  = 1'b0 ? 7'd0 :"),
    ("a product drops its request between rows", "safety", "end else arr_row <= next_row;", "end else begin arr_row <= next_row; req <= 1'b0; end"),
    # revision 4.7 (6 November 2026)
    ("start row: LFSR mod 72 without the 65536 term", "lfsr", "(lfsr[15] ? 9'sd16 : 9'sd0)", "9'sd0"),
    ("result accumulators keep the offset", "safety", "state <= S_FINISH; acc <= acc_fin;", "state <= S_FINISH; acc <= acc_upd;"),
    ("read-back runs under LOCK", "safety", "if (prow_ok && !r_lock) begin", "if (prow_ok) begin"),
    ("margin check writes PDATA under LOCK", "safety", "if (!r_lock) begin                           // (revision 4.7: not under LOCK)",
     "if (1'b1) begin                           // (revision 4.7: not under LOCK)"),
    ("miter: start row from the input of row 0", "miter:prove", "assign start_row  = noshuf_e ? 7'd0 :", "assign start_row  = r_noshuf ? {6'd0, x_nz[0]} :"),
]
# the unfaulted proofs must have passed first (results/formal.log from make formal, the miter logs from the miter runs)
base = (ROOT / "results" / "formal.log").read_text() if (ROOT / "results" / "formal.log").exists() else ""
for t in ("tcim_core_safety", "tcim_core_safety_pnx", "tcim_core_progress", "tcim_core_lfsr"):
    assert f"[{t}] DONE (PASS" in base, f"{t} has not passed in results/formal.log: run make formal first"
for t in ("prove", "prove_pnx"):
    m = ROOT / "results" / "security" / f"miter_{t}.log"
    assert m.exists() and "DONE (PASS" in m.read_text(), f"miter {t} has not passed ({m})"
# each fault runs in its own folder, so they can run side by side (JOBS, default 1)
def one(item):
    name, task, old, new = item
    if True:
        d = HERE / "faults" / name.replace(" ", "_")[:40]
        shutil.rmtree(d, ignore_errors=True); (d / "rtl").mkdir(parents=True)
        src = (ROOT / "rtl" / "tcim_core.sv").read_text()
        assert src.count(old) == 1, name
        (d / "rtl" / "tcim_core.sv").write_text(src.replace(old, new))
        shutil.copy(ROOT / "rtl" / "tcim_pkg.sv", d / "rtl")
        sbyf = "tcim_core.sby"
        if task.startswith("miter:"):
            sbyf, task = "tcim_miter.sby", task.split(":")[1]
            shutil.copy(HERE / "tcim_miter.sv", d)
        sby = (HERE / sbyf).read_text().replace("../rtl/", "rtl/")
        (d / sbyf).write_text(sby)
        r = subprocess.run([*SBY, "-f", sbyf, task], cwd=d, capture_output=True, text=True, timeout=7200)
        out = r.stdout
        # a real counterexample ends the task with DONE (FAIL); an induction step that fails alone ends it UNKNOWN (not caught)
        status = "FAIL" if "DONE (FAIL" in out else ("PASS" if "DONE (PASS" in out else "OTHER")   # OTHER: e.g. ERROR, UNKNOWN
        print(name, task, status, flush=True)
        return dict(fault=name, proof=task, result=status, caught=status == "FAIL")
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=int(os.environ.get("JOBS", "1"))) as ex:
    res = list(ex.map(one, F))
(ROOT / "results" / "formal_faults.json").write_text(json.dumps(res, indent=1))
print(sum(r["caught"] for r in res), "of", len(res), "faults make a proof fail")
