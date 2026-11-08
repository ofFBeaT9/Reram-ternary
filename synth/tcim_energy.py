"""Gate-level check and switching-energy estimate of the synthesized TCIM0 core during digital-mode products.
The mapped netlist (IHP standard cells) is simulated with a behavioural array that answers one cycle after
each request; every result is compared with the exact dot product."""
import json, os, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from power_estimate import Netlist

HERE = Path(__file__).resolve().parent
LIB = os.environ["IHP_STDCELL_LIB"]
rnd = random.Random(11)
ENC = {1: 1, 0: 0, -1: 3}
pack = lambda t: sum(ENC[v] << (2 * i) for i, v in enumerate(t))
trits = lambda n, pz=1 / 3: [0 if rnd.random() < pz else rnd.choice((-1, 1)) for _ in range(n)]


def tryte_to_int(x):
    v, w = 0, 1
    for i in range(6):
        c = (x >> (2 * i)) & 3
        v += w * (1 if c == 1 else -1 if c == 3 else 0); w *= 3
    return v


def main(n_products=6, name="tcim_core"):
    n = Netlist(HERE / "build" / f"{name}.json", LIB)
    W = [trits(24) for _ in range(72)]
    for p in ("bus_we", "bus_re", "bus_word", "bus_addr", "bus_wdata", "arr_ack", "arr_sa_p", "arr_sa_n", "arr_adc"):
        n.set(p, 0)
    n.set("rst_n", 0); n.clock(count=False); n.set("rst_n", 1); n.clock(count=False)

    def wr(addr, data, word, count=True):
        n.set("bus_we", 1); n.set("bus_word", word); n.set("bus_addr", addr); n.set("bus_wdata", data)
        n.clock(count=count); n.set("bus_we", 0)

    def rd(addr, word=0):
        n.set("bus_re", 1); n.set("bus_word", word); n.set("bus_addr", addr)
        n._settle(); v = n.get("bus_rdata"); n.clock(count=False); n.set("bus_re", 0)
        return v

    cycles_product, rows_read = [], []
    for _ in range(n_products):
        x = trits(72)
        for k in range(3):
            wr(4 + 4 * k, pack(x[24 * k:24 * k + 24]), 1)
        c0 = n.cycles
        wr(0, 1 | (1 << 6), 0)                               # EN + GO, digital mode
        reads = 0
        for _guard in range(400):
            n._settle()
            if n.get("arr_req"):
                row = n.get("arr_row")
                n.set("arr_sa_p", sum((W[row][c] == 1) << c for c in range(24)))
                n.set("arr_sa_n", sum((W[row][c] == -1) << c for c in range(24)))
                n.set("arr_ack", 1); n.clock(); n.set("arr_ack", 0); reads += 1
            else:
                n.clock()
            n._settle()
            if not n.get("arr_req") and (rd_stat := None) is None:
                pass
            # finished when BUSY drops: STAT is read without counting (the read itself is not part of the product)
            if reads and not n.get("arr_req"):
                n.set("bus_re", 1); n.set("bus_word", 0); n.set("bus_addr", 1); n._settle()
                busy = n.get("bus_rdata") & 3; n.set("bus_re", 0)
                if busy == 0:
                    break
        cycles_product.append(n.cycles - c0); rows_read.append(reads)
        for c in range(24):
            got = tryte_to_int(rd(16 + c))
            exp = sum(x[r] * W[r][c] for r in range(72))
            assert got == exp, (c, got, exp)
    e = n.energy()
    cyc = sum(cycles_product) / len(cycles_product)
    e.update(products=n_products, rows_read_mean=sum(rows_read) / len(rows_read), cycles_per_product=cyc,
             e_product_pJ=e["e_total_pJ_per_cycle"] * (cyc + 3))
    return e


if __name__ == "__main__":
    # tcim_core: the netlist without clock gating; tcim_core_cg: the same RTL with integrated clock-gating cells
    name = sys.argv[1] if len(sys.argv) > 1 else "tcim_core"
    r = main(name=name)
    print(json.dumps(r, indent=1))
    out = HERE.parent / "results" / "synth_baseline.json"
    d = json.loads(out.read_text()) if out.exists() else {}
    d["tcim_core_digital_product" + ("_cg" if name.endswith("_cg") else "")] = r
    out.write_text(json.dumps(d, indent=1))
