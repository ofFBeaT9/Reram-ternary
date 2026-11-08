"""Host test for the TCIM0 FPGA demonstration (rtl/fpga), over the board's USB serial port or against the Verilator
model of the same design (tb/fpga). 9 October 2026.

  python3 tools/fpga_host.py --sim  <path to Vtcim_fpga_top binary>   [options]
  python3 tools/fpga_host.py --port COM5                               [options]     (needs pyserial)
Options: --bank 0|1|2 (spread x1/x2/x3 of the emulated array), --noise N (read noise, LSB of 0.25 uA),
         --products N (random products per mode), --seed S, --json out.json

What it does, with the register map of rtl/tcim_core.sv and the default (two's-complement) trit code:
 1. redraw the emulated array; 2. program all 72 rows with random ternary weights (one third zeros) through
 PROW / PDATA / PCMD (program with verify), recording PITER and WERR per row; 3. read every row back (PCMD = -)
 and count wrong weights; 4. run random digital products (only rows with non-zero input are read) and compare every
 column with the exact dot product of the intended weights; 5. the same in analog mode (converter counts).
The emulated array is not silicon: its statistics come from the device model and published data
(rtl/fpga/arr_emu.sv). The test shows that the logic, the serial protocol and the programming loop work end to end
with variable devices.
"""
import argparse, json, random, subprocess, sys, time

ROWS, COLS = 72, 24
ENC = {1: 0b01, 0: 0b00, -1: 0b11}
DEC = {0b01: 1, 0b00: 0, 0b11: -1, 0b10: 0}


def pack(trits):
    v = 0
    for i, t in enumerate(trits):
        v |= ENC[t] << (2 * i)
    return v


def unpack(v, n):
    return [DEC[(v >> (2 * i)) & 3] for i in range(n)]


def int_to_trits(x, n):
    out = []
    for _ in range(n):
        r = ((x + 1) % 3) - 1
        out.append(r); x = (x - r) // 3
    assert x == 0
    return out


def trits_to_int(ts):
    return sum(t * 3 ** i for i, t in enumerate(ts))


class SimLink:
    def __init__(self, exe):
        self.p = subprocess.Popen([exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)

    def write(self, b):
        self.p.stdin.write(bytes(b)); self.p.stdin.flush()

    def read(self, n):
        out = b""
        while len(out) < n:
            c = self.p.stdout.read(n - len(out))
            if not c:
                raise IOError("simulation ended")
            out += c
        return out

    def close(self):
        self.p.stdin.close(); self.p.wait(timeout=30)


class SerialLink:
    def __init__(self, port):
        import serial
        self.s = serial.Serial(port, 115200, timeout=5)
        time.sleep(0.1); self.s.reset_input_buffer()

    def write(self, b):
        self.s.write(bytes(b))

    def read(self, n):
        d = self.s.read(n)
        if len(d) != n:
            raise IOError(f"timeout: got {len(d)} of {n} bytes")
        return d

    def close(self):
        self.s.close()


class Transcript:
    """Wraps a link and records every byte sent and received, with wall-clock and monotonic times, as JSON lines
    (12 October 2026). tools/fpga_verify.py re-derives every result from this file alone, without trusting the summary."""
    def __init__(self, link, path):
        self.l = link; self.f = open(path, "w"); self.t0 = time.monotonic()

    def _log(self, d, b):
        self.f.write(json.dumps({"t": round(time.monotonic() - self.t0, 6), "d": d, "hex": bytes(b).hex()}) + "\n")

    def note(self, **kv):
        self.f.write(json.dumps({"t": round(time.monotonic() - self.t0, 6), "note": kv}) + "\n")

    def write(self, b):
        self._log("tx", b); self.l.write(b)

    def read(self, n):
        d = self.l.read(n); self._log("rx", d); return d

    def close(self):
        self.f.close(); self.l.close()


class TCIM:
    def __init__(self, link):
        self.l = link

    def _st(self, r, cmd):
        assert r[0] == cmd | 0x20, (r, cmd)
        if r[1] & 1:
            raise RuntimeError("bus error")
        return r

    def write(self, addr, value, word):
        self.l.write([0x57, addr, int(word)] + [(value >> (8 * i)) & 0xff for i in range(6)])
        return self._st(self.l.read(2), 0x57)

    def read(self, addr, word):
        self.l.write([0x52, addr, int(word)])
        r = self._st(self.l.read(8), 0x52)
        return sum(r[2 + i] << (8 * i) for i in range(6)), r[1]

    def emu(self, bank, noise, redraw=True):
        self.l.write([0x45, (bank & 3) | ((noise & 7) << 2) | (0x80 if redraw else 0)])
        return self._st(self.l.read(2), 0x45)

    def pulses(self):
        self.l.write([0x50])
        r = self._st(self.l.read(6), 0x50)
        return sum(r[2 + i] << (8 * i) for i in range(4))

    # registers
    def tryte(self, addr, x):
        self.write(addr, pack(int_to_trits(x, 6)), False)

    def wait(self):
        for _ in range(100000):
            v, _ = self.read(1, False)
            busy, done, werr, sat = unpack(v, 4)
            if busy != 1:
                return dict(done=done == 1, werr=werr == 1, sat=sat == 1)
        raise TimeoutError

    def ctrl(self, en=True, ie=False, analog=False, go=False):
        self.write(0, pack([1 if en else 0, 1 if ie else 0, 1 if analog else 0, 1 if go else 0, 0, 0]), False)

    def program_row(self, r, w):
        self.tryte(40, r)
        self.write(44, pack(w), True)
        self.write(48, pack([1, 0, 0, 0, 0, 0]), False)
        st = self.wait()
        piter = trits_to_int(unpack(self.read(49, False)[0], 6))
        return st, piter

    def read_row(self, r):
        self.tryte(40, r)
        self.write(48, pack([-1, 0, 0, 0, 0, 0]), False)
        st = self.wait()
        return unpack(self.read(44, True)[0], COLS), st

    def product(self, x, analog=False):
        for k in range(3):
            self.write(4 + 4 * k, pack(x[24 * k:24 * k + 24]), True)
        self.ctrl(en=True, analog=analog, go=True)
        st = self.wait()
        y = [trits_to_int(unpack(self.read(16 + c, False)[0], 6)) for c in range(COLS)]
        return y, st


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--sim"); g.add_argument("--port")
    ap.add_argument("--bank", type=int, default=0); ap.add_argument("--noise", type=int, default=1)
    ap.add_argument("--products", type=int, default=50); ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--json")
    ap.add_argument("--transcript", help="record every byte on the link (JSON lines) for tools/fpga_verify.py")
    ap.add_argument("--bitstream", help="bitstream file loaded on the board; its SHA-256 goes into the transcript")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    link = SimLink(a.sim) if a.sim else SerialLink(a.port)
    if a.transcript:
        import hashlib, platform, datetime
        link = Transcript(link, a.transcript)
        link.note(start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), argv=sys.argv, host=platform.node(),
                  python=platform.python_version(), link=("sim " + a.sim) if a.sim else ("serial " + a.port),
                  bitstream=a.bitstream, bitstream_sha256=hashlib.sha256(open(a.bitstream, "rb").read()).hexdigest() if a.bitstream else None,
                  rtl_sha256={f: hashlib.sha256(open(f, "rb").read()).hexdigest() for f in
                              ("rtl/tcim_pkg.sv", "rtl/tcim_core.sv", "rtl/fpga/arr_emu.sv", "rtl/fpga/uart.sv", "rtl/fpga/tcim_fpga_top.sv")
                              if __import__("os").path.exists(f)})
    t = TCIM(link)
    t0 = time.time()
    t.emu(a.bank, a.noise, True)
    t.ctrl(en=True)
    W = [[rng.choice((-1, 0, 1)) for _ in range(COLS)] for _ in range(ROWS)]
    prog = []
    for r in range(ROWS):
        st, piter = t.program_row(r, W[r])
        prog.append(dict(row=r, werr=st["werr"], piter=piter))
    back = [t.read_row(r)[0] for r in range(ROWS)]
    wrong_w = sum(back[r][c] != W[r][c] for r in range(ROWS) for c in range(COLS))
    res = dict(bank=a.bank, noise_lsb=a.noise, seed=a.seed, rows_with_werr=sum(p["werr"] for p in prog),
               piter_max=max(p["piter"] for p in prog), piter_mean=round(sum(p["piter"] for p in prog) / ROWS, 2),
               device_pulses=t.pulses(), readback_wrong_weights=wrong_w, weights=ROWS * COLS)
    for mode in ("digital", "analog"):
        inexact = 0; col_err = 0; max_abs = 0
        for _ in range(a.products):
            x = [rng.choice((-1, 0, 1)) for _ in range(ROWS)]
            y, st = t.product(x, analog=(mode == "analog"))
            exact = [sum(x[r] * W[r][c] for r in range(ROWS)) for c in range(COLS)]
            e = [abs(y[c] - exact[c]) for c in range(COLS)]
            inexact += any(e); col_err += sum(v != 0 for v in e); max_abs = max(max_abs, max(e))
        res[mode] = dict(products=a.products, inexact_products=inexact, wrong_columns=col_err, columns=a.products * COLS, max_abs_error=max_abs)
    res["host_seconds"] = round(time.time() - t0, 1)
    if a.transcript:
        link.note(summary=res)
    link.close()
    print(json.dumps(res, indent=1))
    if a.json:
        open(a.json, "w").write(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
