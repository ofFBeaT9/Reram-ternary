"""Forming path for IHP SG13G2 from 3.3 V transistors only (9 October 2026). Proposal, first sizes.

Problem. IHP's arrays form with sweeps up to about 5 V (Grossi et al. 2018 needed 4.4-5 V for its most uniform film).
SG13G2's thickest-oxide transistors are rated 3.3 V. Everything that touches the bit line during forming must
therefore see no more than 3.3 V between any two of its terminals.

Part A - switch from a VFORM pad to one bit line, and the protection of the read path, VFORM 3.6 / 4.4 / 5.0 V:
  floating-rail level shifter: rails VMID = VFORM - 3.0 V and VFORM; NMOS input pair with NMOS cascodes (gate 3.0 V),
    PMOS cascodes (gate VMID) and a cross-coupled PMOS pair on VFORM; output swings between about VMID + |Vtp| and VFORM;
  switch: two stacked PMOS (gate of the upper one from the level shifter, the lower one at VMID), each in its own n-well
    tied to its source, so no junction sees more than that device's Vds;
  bit-line pull-down: two stacked NMOS (cascode gate 3.0 V); all control inputs swing 0 to 3.0 V;
  read path: column switch as two stacked NMOS, the upper gate 3.0 V and the lower 1.2 V while forming, so the
    sense-amplifier node (1.2 V devices) stays below 1.2 V.
  Load: the selected cell during forming as 20 kOhm (0.25 mA at 5 V, a formed cell under compliance) and 200 fF.
  Checked, at 5 corners and -40 / 27 / 125 C: the bit line reaches VFORM (drop at 0.25 mA), switching times, and the
  largest voltage between any two terminals (gate, drain, source, body) of every transistor over the whole transient.
  Drain-to-substrate junctions of the NMOS devices on the 5 V nodes do see VFORM; that is a junction rating, listed
  separately (IHP to confirm).
Part B - the array during forming (one column, 4 rows: selected row pristine, one row pristine, two rows already
  formed), with the source line along the column as drawn (layout/cell_2t2r.py): bias that keeps every select
  transistor within 3.3 V, and the voltage the selected cell then receives. Pristine cell: 100 MOhm (SkyWater: below
  0.1 uS fresh); formed: 20 kOhm. Compared with a source line along the row.
Writes results/gnucap_forming.json.
"""
import json, os, sys
from pathlib import Path
import numpy as np
import gnucap_run as g

OUT = Path(__file__).resolve().parents[2] / "results" / "gnucap_forming.json"
CORNERS = ("tt", "ss", "ff", "sf", "fs")
TEMPS = (-40, 27, 125)
SZ = dict(n_in=2.0, n_cas=2.0, p_cas=4.0, p_x=1.0, p_sw=20.0, n_pd=10.0, n_mux=10.0)
# SG13G2 process specification (libs.doc/doc/SG13G2_os_process_spec.pdf), sections 2.4 / 2.5: VGS <= 3.3 V maximum
# for HV-NMOS with L >= 0.6 um and HV-PMOS with L >= 0.5 um; BVDSS >= 5.3 V (NMOS, 10 x 0.45 um); junction breakdown
# n+/p-well and p+/n-well 12 V. The forming circuits therefore use L = 0.6 um (NMOS) and 0.5 um (PMOS).
L_N, L_P = 0.6, 0.5
# Design margin: no protection bias is placed at the 3.3 V rating itself. VMID = VFORM - VOX and the cascode gates are
# at VOX, so switching transients (about 0.15 V in the first runs, which used 3.3 V) stay below 3.3 V.
VOX = 3.0
KEEPERS = "1 GOhm: ya, yb, m to VMID; a1, b1, d1, ca to ground"
JUNCTION_BV = 12.0
VMAX = 3.3


def dev(kind, name, d, gt, s, b, w, l=None):
    l = (L_N if kind == "n" else L_P) if l is None else l
    m = int(np.ceil(w / 10.0 - 1e-9))
    gnd = lambda n: "\\0 " if n == "0" else n                      # ground in Gnucap's Verilog mode
    return (f"sg13_hv_{kind}mos #(.w({w / m:g}u), .l({l}u), .ng(1), .m({m}), .mm_ok(0), .rfmode(0)) {name}({gnd(d)}, {gnd(gt)}, {gnd(s)}, {gnd(b)});",
            (name, kind, d, gt, s, b))


def part_a_netlist():
    z = SZ
    D = [
        # floating-rail level shifter, branch A (input en) and B (input enb)
        dev("n", "na1", "a1", "en", "0", "0", z["n_in"]), dev("n", "na2", "xa", "vddh", "a1", "0", z["n_cas"]),
        dev("p", "pa2", "xa", "vmid", "ya", "ya", z["p_cas"]), dev("p", "pa1", "ya", "yb", "vform", "vform", z["p_x"]),
        dev("n", "nb1", "b1", "enb", "0", "0", z["n_in"]), dev("n", "nb2", "xb", "vddh", "b1", "0", z["n_cas"]),
        dev("p", "pb2", "xb", "vmid", "yb", "yb", z["p_cas"]), dev("p", "pb1", "yb", "ya", "vform", "vform", z["p_x"]),
        # stacked PMOS switch VFORM -> bit line
        dev("p", "ps1", "m", "ya", "vform", "vform", z["p_sw"]), dev("p", "ps2", "bl", "vmid", "m", "m", z["p_sw"]),
        # mid-node clamp: while the switch is off (yb low) a PMOS from the node between the two switch PMOS to VMID
        # keeps that node within |Vtp| of yb; without it the node floats and the upper PMOS sees up to 4 V gate to
        # drain (found on 10 October). In its own n-well tied to the node.
        dev("p", "pc", "vmid", "yb", "m", "m", 1.0),
        # stacked bit-line pull-down
        dev("n", "nd2", "d1", "vddh", "bl", "0", z["n_pd"]), dev("n", "nd1", "0", "dis", "d1", "0", z["n_pd"]),
        # stacked column switch to the sense amplifier
        dev("n", "nma", "bl", "vmuxa", "ca", "0", z["n_mux"]), dev("n", "nmb", "ca", "vmuxb", "blsa", "0", z["n_mux"]),
    ]
    return [d[0] for d in D], [d[1] for d in D]


EDGES_NS = (10, 15, 20, 200, 250, 300)          # input edges of the part A transient
LIMIT = 3.3


def stress(table, devices, nodes_fixed):
    """Per device: oxide (gate to source, drain, body) and channel (drain to source) voltages, from the printed node
    voltages: the largest value once settled (more than 5 ns after every input edge), the largest value at any time,
    and the time spent above 3.3 V. Junctions (drain or source to body) are listed separately (rated 12 V)."""
    cols = table["cols"]
    data = table["data"]
    t = data[:, 0]
    # the first 10 ns are start-up from Gnucap's DC solution, in which nodes held only by off transistors can take
    # unphysical values (seen: -2 V at t = 0 for VFORM 3.6 V); they are excluded from every figure below
    run = t >= 10e-9
    settled = run.copy()
    for e in EDGES_NS:
        settled &= ~((t >= e * 1e-9) & (t < (e + 5) * 1e-9))
    dt = np.gradient(t)

    def v(n):
        if n == "0":
            return np.zeros(len(data))
        if n in nodes_fixed:
            return np.full(len(data), nodes_fixed[n])
        return data[:, cols.index(f"v({n})")]
    out = {}
    for name, kind, d, gt, s, b in devices:
        V = dict(d=v(d), g=v(gt), s=v(s), b=v(b))
        oc = dict(gs=V["g"] - V["s"], gd=V["g"] - V["d"], gb=V["g"] - V["b"], ds=V["d"] - V["s"])
        jn = dict(db=V["d"] - V["b"], sb=V["s"] - V["b"])
        worst_t = np.where(run, np.max(np.abs(np.vstack(list(oc.values()))), axis=0), 0.0)
        out[name] = dict(settled_max=round(float(worst_t[settled].max()), 3), any_time_max=round(float(worst_t.max()), 3),
                         ns_above_limit=round(float(dt[worst_t > LIMIT].sum() * 1e9), 3),
                         junction_max=round(float(np.max(np.abs(np.vstack(list(jn.values())))[:, run])), 3),
                         pairs={k: round(float(np.abs(x).max()), 3) for k, x in oc.items()})
    return out


def part_a(corner, temp, vform):
    vmid = vform - VOX
    lines, devices = part_a_netlist()
    nodes = ["en", "enb", "a1", "xa", "ya", "b1", "xb", "yb", "m", "bl", "d1", "ca", "blsa", "dis", "vmuxb"]
    deck = g.header(corner) + f"""
spice
.options temp={temp}
Vform vform 0 dc {vform}
Vmid vmid 0 dc {vmid}
Vddh vddh 0 dc {VOX}
Vmuxa vmuxa 0 dc {VOX}
* control inputs from a VOX (3.0 V) rail
Ven en 0 pwl(0 0 20n 0 20.5n {VOX} 200n {VOX} 200.5n 0 400n 0)
Venb enb 0 pwl(0 {VOX} 20n {VOX} 20.5n 0 200n 0 200.5n {VOX} 400n {VOX})
Vdis dis 0 pwl(0 {VOX} 15n {VOX} 15.5n 0 250n 0 250.5n {VOX} 400n {VOX})
Vmuxb vmuxb 0 pwl(0 {VOX} 10n {VOX} 10.5n 1.2 300n 1.2 300.5n {VOX} 400n {VOX})
Rload bl 0 20k
Cbl bl 0 200f
Rsa blsa vsa 100k
* 1 GOhm from the level-shifter outputs and from the switch mid node to VMID: defines the DC solution of nodes that
* are otherwise held only by off transistors (in silicon their subthreshold currents settle them between VMID and
* VMID + |Vtp|)
Rka ya vmid 1G
Rkb yb vmid 1G
Rkm m vmid 1G
* the same for the nodes inside the NMOS stacks (between input and cascode, pull-down halves, column-switch halves):
* without them a node held only by two off transistors takes values of hundreds of volts in Gnucap's solution
* (found on 10 October: 'open circuit: internal node' and up to 411 V on na1 while en was low)
Rk1 a1 0 1G
Rk2 b1 0 1G
Rk3 d1 0 1G
Rk4 ca 0 1G
Vsa vsa 0 dc 0.2
.verilog
{chr(10).join(lines)}
print tran {' '.join(f'v({n})' for n in nodes)}
tran 0 400n 0.1n
"""
    t = g.run(deck, timeout=1200)[0]
    data, cols = t["data"], t["cols"]
    tt = data[:, 0]
    vb = data[:, cols.index("v(bl)")]
    on = vb[(tt > 150e-9) & (tt < 199e-9)]
    t90 = tt[np.nonzero((tt > 20e-9) & (vb > 0.9 * vform))[0][0]] - 20.25e-9 if (vb > 0.9 * vform).any() else None
    st = stress(t, devices, dict(vform=vform, vmid=vmid, vddh=VOX, vmuxa=VOX))
    ws = max(st.items(), key=lambda kv: kv[1]["settled_max"])
    wt = max(st.items(), key=lambda kv: kv[1]["any_time_max"])
    return dict(vform=vform, bl_on_V=round(float(on.mean()), 4), drop_mV=round((vform - float(on.mean())) * 1e3, 1),
                bl_rise_90_ns=None if t90 is None else round(t90 * 1e9, 2),
                bl_after_pulldown_V=round(float(vb[np.argmin(abs(tt - 299e-9))]), 4),
                blsa_max_V=round(float(data[tt >= 10e-9, cols.index("v(blsa)")].max()), 4),
                settled_worst_device=ws[0], settled_worst_V=ws[1]["settled_max"],
                transient_worst_device=wt[0], transient_worst_V=wt[1]["any_time_max"],
                ns_above_limit_max=max(x["ns_above_limit"] for x in st.values()),
                junction_max_V=max(x["junction_max"] for x in st.values()), devices=st, problems=t.get("problems", [])[:5])


# ---------------------------------------------------------------- B. array column during forming
def part_b(corner, temp, vform, sl_along="column"):
    """4 rows of one column: r0 selected (pristine), r1 pristine, r2/r3 formed. Returns biases, cell voltages and stress."""
    vmid = vform - VOX
    rp, rf = 100e6, 20e3
    cells = dict(r0=rp, r1=rp, r2=rf, r3=rf)
    if sl_along == "column":
        # one source line for the column: it must carry VMID so that the unselected rows (gate VMID) are off
        sl = {r: vmid for r in cells}
        wl = dict(r0=vmid + 1.5, r1=vmid, r2=vmid, r3=vmid)
    else:
        # source line per row: the selected row's at 0 V, the others at VMID; unselected gates at VMID
        sl = dict(r0=0.0, r1=vmid, r2=vmid, r3=vmid)
        wl = dict(r0=1.5, r1=vmid, r2=vmid, r3=vmid)
    lines, devices, src = [], [], []
    for r, R in cells.items():
        src += [f"Vwl{r} wl{r} 0 dc {wl[r]}", f"Vsl{r} sl{r} 0 dc {sl[r]}", f"R{r} bl d{r} {R:g}"]
        l_, d_ = dev("n", f"m{r}", f"d{r}", f"wl{r}", f"sl{r}", "0", 4.5, l=0.45)   # the drawn select transistor
        lines.append(l_); devices.append(d_)
    deck = g.header(corner) + f"""
spice
.options temp={temp}
Vbl bl 0 dc {vform}
{chr(10).join(src)}
.verilog
{chr(10).join(lines)}
print op {' '.join(f'v(d{r})' for r in cells)}
op
"""
    t = g.run(deck, timeout=600)[0]
    row = t["data"][0]; cols = t["cols"]
    vd = {r: float(row[cols.index(f"v(d{r})")]) for r in cells}
    fixed = dict(bl=vform, **{f"wl{r}": wl[r] for r in cells}, **{f"sl{r}": sl[r] for r in cells})
    st = {}
    for name, kind, d, gt, s, b in devices:
        r = name[1:]
        V = dict(d=vd[r], g=wl[r], s=sl[r], b=0.0)
        pairs = dict(gs=V["g"] - V["s"], gd=V["g"] - V["d"], ds=V["d"] - V["s"], db=V["d"], sb=V["s"], gb=V["g"])
        st[name] = {k: round(abs(x), 3) for k, x in pairs.items()}
    gate_channel = max(max(st[n][k] for k in ("gs", "gd", "ds")) for n in st)
    return dict(sl_along=sl_along, vform=vform, vmid=vmid, wl=wl, sl=sl, cell_V={r: round(vform - vd[r], 3) for r in cells},
                selected_cell_V=round(vform - vd["r0"], 3), max_gate_channel_V=gate_channel,
                max_junction_V=max(max(st[n]["db"], st[n]["sb"]) for n in st), devices=st)


def _part_a_job(a):
    return part_a(*a)


if __name__ == "__main__":
    res = dict(sizes_um=SZ, vmax=VMAX, keepers=KEEPERS, part_a={}, part_b={})
    if "--resume" in sys.argv and OUT.exists():           # continue an interrupted sweep with the same sizes
        old = json.loads(OUT.read_text())
        if old.get("sizes_um") == SZ and old.get("keepers") == KEEPERS:
            res["part_a"] = old.get("part_a", {})
    todo = [(c, T, vf) for vf in (3.6, 4.4, 5.0) for c in CORNERS for T in TEMPS if f"{vf} V {c} {T} C" not in res["part_a"]]
    from multiprocessing import Pool
    with Pool(int(os.environ.get("JOBS", os.cpu_count() or 1))) as pool:
        for (c, T, vf), r in zip(todo, pool.imap(_part_a_job, todo)):
            res["part_a"][f"{vf} V {c} {T} C"] = r
            OUT.write_text(json.dumps(res, indent=1))
            print("A", vf, c, T, {k: r[k] for k in ("bl_on_V", "drop_mV", "bl_rise_90_ns", "bl_after_pulldown_V", "blsa_max_V", "settled_worst_device", "settled_worst_V", "transient_worst_device", "transient_worst_V", "ns_above_limit_max", "junction_max_V")}, flush=True)
    res["part_a"] = {f"{vf} V {c} {T} C": res["part_a"][f"{vf} V {c} {T} C"] for vf in (3.6, 4.4, 5.0) for c in CORNERS for T in TEMPS}
    OUT.write_text(json.dumps(res, indent=1))
    A = list(res["part_a"].values())
    res["part_a_summary"] = dict(cases=len(A), settled_max_V=max(x["settled_worst_V"] for x in A),
                                 transient_max_V=max(x["transient_worst_V"] for x in A),
                                 ns_above_3p3_max=max(x["ns_above_limit_max"] for x in A),
                                 junction_max_V=max(x["junction_max_V"] for x in A), drop_max_mV=max(x["drop_mV"] for x in A),
                                 rise_max_ns=max(x["bl_rise_90_ns"] or 999 for x in A), blsa_max_V=max(x["blsa_max_V"] for x in A),
                                 pulldown_max_V=max(x["bl_after_pulldown_V"] for x in A))
    print(res["part_a_summary"], flush=True)
    for along in ("column", "row"):
        for vf in (3.3, 4.4, 5.0):
            for c, T in (("tt", 27), ("ff", 125), ("ss", -40)):
                r = part_b(c, T, vf, along)
                res["part_b"][f"{along} {vf} V {c} {T} C"] = r
                print("B", along, vf, c, T, r["cell_V"], r["max_gate_channel_V"], flush=True)
    OUT.write_text(json.dumps(res, indent=1))
