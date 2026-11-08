"""Independent check of an FPGA run from its byte transcript (12 October 2026).

  python3 tools/fpga_verify.py run.transcript.jsonl [--json out.json]

Reads only the bytes that crossed the serial line (written by tools/fpga_host.py --transcript), decodes them with the
byte protocol of rtl/fpga/tcim_fpga_top.sv and the register map of rtl/tcim_core.sv, and re-derives every result:
the weights each row was programmed with (PROW / PDATA / PCMD = +), the weights read back (PCMD = -), the error flag of
every program command (STAT after it), the input vector and the 24 results of every product, and the exact dot
products. It does not import the host program and does not trust its summary; at the end it compares its own numbers
with the summary the host wrote into the transcript and exits with 1 if any differs.
Trit code: two's complement, 01 = +1, 00 = 0, 11 = -1 (10 is not a valid trit and is counted)."""
import json, sys, argparse

ROWS, COLS = 72, 24
DEC = {0b01: 1, 0b00: 0, 0b11: -1}


def trits(v, n):
    out = []
    for i in range(n):
        c = (v >> (2 * i)) & 3
        if c not in DEC:
            raise ValueError(f"invalid trit code {c:02b}")
        out.append(DEC[c])
    return out


def val(ts):
    return sum(t * 3 ** i for i, t in enumerate(ts))


def frames(path):
    """Pair each transmitted command with the bytes received for it."""
    import gzip
    fh = gzip.open(path, "rt") if path.endswith(".gz") else open(path)
    ev = [json.loads(l) for l in fh if l.strip()]
    notes = [e["note"] for e in ev if "note" in e]
    io = [e for e in ev if "d" in e]
    out = []; i = 0
    while i < len(io):
        tx = io[i]
        assert tx["d"] == "tx", f"unexpected {tx}"
        rx = io[i + 1] if i + 1 < len(io) and io[i + 1]["d"] == "rx" else None
        out.append((bytes.fromhex(tx["hex"]), bytes.fromhex(rx["hex"]) if rx else b"", tx["t"]))
        i += 2 if rx else 1
    return out, notes


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("transcript"); ap.add_argument("--json"); a = ap.parse_args()
    fr, notes = frames(a.transcript)
    regs = {}                     # last value written per address (48-bit bus value)
    intended = {}                 # row -> weights it was programmed with
    readback = {}                 # row -> weights read back
    prog_werr = {}; prog_piter = {}
    products = {"digital": [], "analog": []}
    pending = None                # (kind, info) awaiting completion
    bad_status = 0; n_frames = len(fr); last_stat = None
    ctrl_mode = None; ys = {}
    for tx, rx, t in fr:
        cmd = tx[0]
        if cmd == 0x57:           # 'W' addr flags d0..d5
            assert rx[:1] == b"w", (tx, rx)
            bad_status += rx[1] & 1
            addr, v = tx[1], int.from_bytes(tx[3:9], "little")
            regs[addr] = v
            if addr == 48:        # PCMD
                op = trits(v & 0xfff, 6)[0]; row = val(trits(regs.get(40, 0) & 0xfff, 6))
                if op == 1:
                    intended[row] = trits(regs[44], COLS); pending = ("prog", row)
                elif op == -1:
                    pending = ("read", row)
            if addr == 0:         # CTRL
                c = trits(v & 0xfff, 6)
                if c[3] == 1:     # GO
                    x = trits(regs[4], 24) + trits(regs[8], 24) + trits(regs[12], 24)
                    pending = ("product", ("analog" if c[2] == 1 else "digital", x)); ys = {}
        elif cmd == 0x52:         # 'R' addr flags -> 'r' st d0..d5
            assert rx[:1] == b"r", (tx, rx)
            bad_status += rx[1] & 1
            addr, v = tx[1], int.from_bytes(rx[2:8], "little")
            if addr == 1:
                last_stat = trits(v & 0xfff, 6)
                if last_stat[0] != 1 and pending and pending[0] == "prog":
                    prog_werr[pending[1]] = last_stat[2] == 1
            elif addr == 49 and pending and pending[0] == "prog":
                prog_piter[pending[1]] = val(trits(v & 0xfff, 6))
            elif addr == 44 and pending and pending[0] == "read":
                readback[pending[1]] = trits(v, COLS)
            elif 16 <= addr < 40 and pending and pending[0] == "product":
                ys[addr - 16] = val(trits(v & 0xfff, 6))
                if len(ys) == COLS:
                    mode, x = pending[1]
                    products[mode].append((x, [ys[c] for c in range(COLS)])); pending = None
        elif cmd in (0x45, 0x50):  # 'E' emulator config, 'P' pulse count
            pass
        else:
            raise ValueError(f"unknown command byte {cmd:#x}")
    W = [intended[r] for r in range(ROWS)]
    wrong_w = sum(readback[r][c] != W[r][c] for r in range(ROWS) for c in range(COLS))
    res = dict(frames=n_frames, bus_errors=bad_status, rows_programmed=len(intended), rows_read_back=len(readback),
               rows_with_werr=sum(prog_werr.values()), piter_max=max(prog_piter.values()),
               piter_mean=round(sum(prog_piter.values()) / ROWS, 2), readback_wrong_weights=wrong_w, weights=ROWS * COLS)
    for mode, lst in products.items():
        inexact = col_err = mx = 0
        for x, y in lst:
            exact = [sum(x[r] * W[r][c] for r in range(ROWS)) for c in range(COLS)]
            e = [abs(y[c] - exact[c]) for c in range(COLS)]
            inexact += any(e); col_err += sum(v != 0 for v in e); mx = max(mx, max(e))
        res[mode] = dict(products=len(lst), inexact_products=inexact, wrong_columns=col_err, columns=len(lst) * COLS, max_abs_error=mx)
    host = next((n["summary"] for n in notes if "summary" in n), None)
    start = next((n for n in notes if "start_utc" in n), {})
    diffs = []
    if host:
        for k in ("rows_with_werr", "piter_max", "piter_mean", "readback_wrong_weights"):
            if host.get(k) != res[k]:
                diffs.append((k, host.get(k), res[k]))
        for m in ("digital", "analog"):
            for k in ("products", "inexact_products", "wrong_columns", "max_abs_error"):
                if host[m][k] != res[m][k]:
                    diffs.append((m + "." + k, host[m][k], res[m][k]))
    out = dict(recomputed=res, start=start, host_summary=host, differences_from_host=diffs,
               verdict="consistent" if host and not diffs else ("no host summary" if not host else "DIFFERS"))
    print(json.dumps(out, indent=1))
    if a.json:
        open(a.json, "w").write(json.dumps(out, indent=1))
    sys.exit(0 if out["verdict"] == "consistent" else 1)


if __name__ == "__main__":
    main()
