"""Switching-energy estimates of the digital yardsticks (see power_estimate.py for the method and its limits)."""
import json, os, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from power_estimate import Netlist

HERE = Path(__file__).resolve().parent
LIB = os.environ["IHP_STDCELL_LIB"]
OUT = HERE.parent / "results"
rnd = random.Random(7)
ENC = {1: 1, 0: 0, -1: 3}


def trits(n, p_zero=1 / 3):
    return [0 if rnd.random() < p_zero else rnd.choice((-1, 1)) for _ in range(n)]


def pack(t):
    return sum(ENC[v] << (2 * i) for i, v in enumerate(t))


def tmac():
    n = Netlist(HERE / "build" / "tmac24.json", LIB)
    hist = []
    for k in range(1200):
        a, b, acc = trits(24), trits(24), rnd.randint(-200, 200)
        n.set("a", pack(a)); n.set("b", pack(b)); n.set("acc_in", acc & 0x3ff)
        n.clock(count=k > 4)
        hist.append((a, b, acc))
        if k >= 1:                                    # input register, then output register
            a0, b0, acc0 = hist[k - 1]
            got = n.get("acc_out")
            got = got - 1024 if got & 0x200 else got
            exp = acc0 + sum(x * y for x, y in zip(a0, b0))
            assert got == exp, (k, got, exp)
    return n.energy()


def dtile(n_products=12, name="dtile72x24"):
    n = Netlist(HERE / "build" / f"{name}.json", LIB)
    W = [trits(24) for _ in range(72)]
    n.set("rst_n", 0); n.set("we", 0); n.set("go", 0); n.clock(count=False)
    n.set("rst_n", 1)
    for r in range(72):
        n.set("we", 1); n.set("waddr", r); n.set("wdata", pack(W[r])); n.clock(count=False)
    n.set("we", 0); n.clock(count=False)
    for _ in range(n_products):
        x = trits(72)
        n.set("x", pack(x)); n.set("go", 1); n.clock()
        n.set("go", 0)
        for _ in range(72):
            n.clock()
        assert n.get("busy") == 0
        y = n.get("y")
        for c in range(24):
            v = (y >> (10 * c)) & 0x3ff
            v = v - 1024 if v & 0x200 else v
            assert v == sum(x[r] * W[r][c] for r in range(72)), (c, v)
    e = n.energy()
    e["cycles_per_product"] = 73
    e["e_product_pJ"] = e["e_total_pJ_per_cycle"] * 73
    return e


if __name__ == "__main__":
    res = {}
    res["tmac24"] = tmac()
    print("tmac24 (function checked against the reference on 1,199 random vectors):", json.dumps(res["tmac24"], indent=1))
    if (HERE / "build" / "dtile72x24.json").exists():
        res["dtile72x24"] = dtile()
        print("dtile72x24 (12 products checked against the exact result):", json.dumps(res["dtile72x24"], indent=1))
    if (HERE / "build" / "dtile72x24_cg.json").exists():          # the same yardstick with clock gating (revision 4.3)
        res["dtile72x24_cg"] = dtile(name="dtile72x24_cg")
        print("dtile72x24_cg:", json.dumps(res["dtile72x24_cg"], indent=1))
    for top in ("tcim_top", "tcim_top_cg"):
        p = HERE / "build" / f"{top}.json"
        if p.exists():
            n = Netlist(p, LIB)
            res[top] = dict(area_um2=round(n.area, 1), cells=sum(n.count.values()), flops=len(n.ffs), leakage_uW=n.leak_pW * 1e-6)
            print(top, res[top])
    (OUT / "synth_baseline.json").write_text(json.dumps(res, indent=1))
