"""First-order switching-energy estimate of a synthesized netlist (Yosys JSON + Liberty), by zero-delay simulation.

Energy per cycle = sum over nets of toggles x 1/2 C V^2   (C = fan-out pin capacitance + a wire allowance)
                 + sum over cell outputs of toggles x internal energy per transition (Liberty table, smallest load)
                 + clock: per flip-flop two clock-pin transitions (internal energy + pin capacitance) in every cycle in
                   which its clock runs: every cycle, or, behind an integrated clock-gating cell (ICG), only the cycles
                   in which the gate's enable is high; each ICG costs its clock-pin energy in every cycle, its output
                   energy in enabled cycles and its enable-pin energy on every enable toggle
                 + leakage x clock period
Also reported: e_clock_ideal_gating_pJ, the clock energy if every flip-flop were clocked only in the cycles in which
it takes a new value (a lower bound for clock gating: no gating cells, no clock tree).
Limits: no glitches (zero-delay), no clock tree, no placement or wire extraction. Expect the true figure to be
higher, typically by a factor of 1.5 to 3 for arithmetic logic. Good for order-of-magnitude comparisons only.
"""
from __future__ import annotations

import json
from collections import defaultdict

import liberty

VDD = 1.2


def _N(x):
    return 1 ^ x

C_WIRE = 2e-3          # pF per net, allowance


class Netlist:
    def __init__(self, json_path, lib_path, top=None):
        self.lib = liberty.load(lib_path)
        d = json.load(open(json_path))
        mods = d["modules"]
        if top is None:
            top = next((n for n, m in mods.items() if m.get("attributes", {}).get("top")), None) or next(iter(mods))
        self.top = top
        m = mods[top]
        self.ports = {n: (p["direction"], p["bits"]) for n, p in m["ports"].items()}
        self.val = defaultdict(int)
        self.val["1"] = 1
        self.comb, self.ffs, self.icgs = [], [], []
        self.area = 0.0
        self.leak_pW = 0.0
        self.count = defaultdict(int)
        load = defaultdict(float)
        driver = {}
        for name, c in m["cells"].items():
            lc = self.lib.get(c["type"])
            if lc is None:
                raise KeyError(f"cell type {c['type']} not in the library (design not fully mapped?)")
            self.area += lc.area
            self.leak_pW += lc.leakage_pW
            self.count[c["type"]] += 1
            conn = {p: b[0] for p, b in c["connections"].items()}
            for p, b in conn.items():
                if lc.pins.get(p) == "input":
                    load[b] += lc.cap[p]
            outs = [p for p in conn if lc.pins.get(p) == "output"]
            if lc.icg:
                self.icgs.append((lc, conn, name))
                continue
            if lc.ff:
                self.ffs.append((lc, conn, name))
            else:
                self.comb.append((lc, conn, outs, [compile(lc.func[o], "<f>", "eval") for o in outs]))
            for o in outs:
                driver[conn[o]] = (lc, o)
        self.load, self.driver = load, driver
        # gated clock nets: net -> index of the ICG that drives it; flip-flops whose clock pin sits on such a net
        self.gated = {conn[lc.icg["out"]]: k for k, (lc, conn, _) in enumerate(self.icgs)}
        self.ff_gate = []
        for lc, conn, name in self.ffs:
            ck = lc.ff["clock"].replace("!", "").strip()
            self.ff_gate.append(self.gated.get(conn.get(ck)))
        self._order()
        self.state = {name: 0 for _, _, name in self.ffs}
        self.ff_code = [(compile(lc.ff["next"], "<n>", "eval"), compile(lc.ff["clear"], "<c>", "eval") if lc.ff["clear"] else None,
                         compile(lc.ff["preset"], "<p>", "eval") if lc.ff["preset"] else None) for lc, _, _ in self.ffs]
        self.toggles = defaultdict(int)
        self.ff_changes = defaultdict(int)   # counted cycles in which a flip-flop takes a new value
        self.ff_clocked = defaultdict(int)   # counted cycles in which a flip-flop's clock ran
        self.icg_on = defaultdict(int)       # counted cycles in which an ICG passed the clock
        self.cycles = 0
        self.prev = None

    def _order(self):
        produced = {}
        for k, (lc, conn, outs, _) in enumerate(self.comb):
            for o in outs:
                produced[conn[o]] = k
        deps = []
        indeg = [0] * len(self.comb)
        users = defaultdict(list)
        for k, (lc, conn, outs, _) in enumerate(self.comb):
            for p, b in conn.items():
                if lc.pins.get(p) == "input" and b in produced:
                    users[produced[b]].append(k); indeg[k] += 1
        ready = [k for k, n in enumerate(indeg) if n == 0]
        order = []
        while ready:
            k = ready.pop()
            order.append(k)
            for u in users[k]:
                indeg[u] -= 1
                if indeg[u] == 0:
                    ready.append(u)
        if len(order) != len(self.comb):
            raise RuntimeError("combinational loop in netlist")
        self.comb = [self.comb[k] for k in order]

    # ------------------------------------------------------------------ simulation
    def set(self, port, value):
        for i, b in enumerate(self.ports[port][1]):
            if isinstance(b, int):
                self.val[b] = (value >> i) & 1

    def get(self, port):
        return sum((self.val[b] if isinstance(b, int) else int(b == "1")) << i for i, b in enumerate(self.ports[port][1]))

    def _settle(self):
        val = self.val
        for (lc, conn, name) in self.ffs:
            q = self.state[name]
            for p, b in conn.items():
                if lc.pins.get(p) == "output":
                    val[b] = q if lc.func.get(p, "").find(lc.ff["state_n"] or "\0") < 0 else 1 - q
        for lc, conn, outs, codes in self.comb:
            v = {p: val[b] for p, b in conn.items()}
            for o, code in zip(outs, codes):
                val[conn[o]] = eval(code, {"v": v, "N": _N}) & 1

    def clock(self, count=True):
        """Settle with the present inputs, record toggles against the previous cycle, then clock the flip-flops."""
        self._settle()
        snap = dict(self.val)
        if count and self.prev is not None:
            for b, x in snap.items():
                if self.prev.get(b, 0) != x:
                    self.toggles[b] += 1
            self.cycles += 1
        self.prev = snap
        # an ICG passes the next clock edge if its enable (or test enable) is high before the edge
        en = [int(any(self.val[conn[p]] for p in lc.icg["enable"] + lc.icg["test"] if p in conn)) for lc, conn, _ in self.icgs]
        if count and self.prev is not None:
            for k, e in enumerate(en):
                self.icg_on[k] += e
        nxt = {}
        for (lc, conn, name), (cn, cc, cp), g in zip(self.ffs, self.ff_code, self.ff_gate):
            v = {p: self.val[b] for p, b in conn.items()}
            clocked = g is None or en[g]
            if count and self.prev is not None and clocked:
                self.ff_clocked[name] += 1
            q = (eval(cn, {"v": v, "N": _N}) & 1) if clocked else self.state[name]
            if cc is not None and eval(cc, {"v": v, "N": _N}) & 1:
                q = 0
            if cp is not None and eval(cp, {"v": v, "N": _N}) & 1:
                q = 1
            nxt[name] = q
        if count and self.prev is not None:
            for name, q in nxt.items():
                if q != self.state.get(name, q):
                    self.ff_changes[name] += 1
        self.state = nxt
        self._settle()

    # ------------------------------------------------------------------ report
    def energy(self, f_clk=50e6):
        e_net = e_int = 0.0
        for b, n in self.toggles.items():
            if not isinstance(b, int):
                continue
            e_net += n * 0.5 * (self.load.get(b, 0.0) + C_WIRE) * VDD * VDD
            if b in self.driver:
                lc, o = self.driver[b]
                e_int += n * lc.e_int.get(o, 0.0)
        e_clk = e_clk_ideal = 0.0
        for lc, conn, name in self.ffs:
            ck = lc.ff["clock"].replace("!", "").strip()
            e_one = 2 * (lc.e_int.get(ck, 0.0) + 0.5 * lc.cap.get(ck, 0.0) * VDD * VDD)
            e_clk += self.ff_clocked[name] * e_one
            e_clk_ideal += self.ff_changes[name] * e_one     # bound: each flip-flop clocked only when it changes
        e_icg = 0.0
        for k, (lc, conn, name) in enumerate(self.icgs):
            c, o = lc.icg["clock"], lc.icg["out"]
            e_icg += self.cycles * 2 * (lc.e_int.get(c, 0.0) + 0.5 * lc.cap.get(c, 0.0) * VDD * VDD)
            e_icg += self.icg_on[k] * 2 * lc.e_int.get(o, 0.0)
            for p in lc.icg["enable"]:
                e_icg += self.toggles.get(conn[p], 0) * lc.e_int.get(p, 0.0)
        e_clk += e_icg
        n = max(self.cycles, 1)
        leak = self.leak_pW * 1e-12 / f_clk * 1e12          # pJ per cycle
        return dict(cycles=self.cycles, area_um2=round(self.area, 1), cells=sum(self.count.values()), flops=len(self.ffs),
                    e_net_pJ=e_net / n, e_internal_pJ=e_int / n, e_clock_pJ=e_clk / n, e_leak_pJ=leak,
                    e_clock_ideal_gating_pJ=e_clk_ideal / n, icgs=len(self.icgs), e_icg_pJ=e_icg / n,
                    gated_flops=sum(g is not None for g in self.ff_gate),
                    e_total_pJ_per_cycle=(e_net + e_int + e_clk) / n + leak, leakage_uW=self.leak_pW * 1e-6)
