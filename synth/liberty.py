"""Minimal Liberty (.lib) reader: enough for area, pin capacitance, logic functions, flip-flop definitions
and the internal-power tables of a standard-cell library."""
from __future__ import annotations

import re

_TOK = re.compile(r'\s*(?:(/\*.*?\*/)|("(?:[^"\\]|\\.)*")|([{}();:,])|([^\s{}();:,"]+))', re.S)


def _tokens(text):
    pos = 0
    n = len(text)
    while pos < n:
        m = _TOK.match(text, pos)
        if not m:
            break
        pos = m.end()
        if m.group(1):
            continue
        if m.group(2) is not None:
            yield ("s", m.group(2)[1:-1].replace("\\\n", ""))
        elif m.group(3):
            yield ("p", m.group(3))
        elif m.group(4):
            yield ("w", m.group(4).replace("\\", ""))


class Group:
    def __init__(self, kind, args):
        self.kind, self.args, self.attrs, self.groups = kind, args, {}, []

    def sub(self, kind):
        return [g for g in self.groups if g.kind == kind]


def parse(path) -> Group:
    toks = list(_tokens(open(path).read()))
    i = 0

    def group(kind, args):
        nonlocal i
        g = Group(kind, args)
        while i < len(toks):
            t = toks[i]
            if t == ("p", "}"):
                i += 1
                return g
            name = t[1]
            i += 1
            if toks[i] == ("p", ":"):                       # simple attribute
                i += 1
                vals = []
                while toks[i] != ("p", ";"):
                    vals.append(toks[i][1]); i += 1
                i += 1
                g.attrs[name] = " ".join(vals)
            elif toks[i] == ("p", "("):                     # group or complex attribute
                i += 1
                args_ = []
                while toks[i] != ("p", ")"):
                    if toks[i][0] != "p":
                        args_.append(toks[i][1])
                    i += 1
                i += 1
                if i < len(toks) and toks[i] == ("p", "{"):
                    i += 1
                    g.groups.append(group(name, args_))
                else:
                    if i < len(toks) and toks[i] == ("p", ";"):
                        i += 1
                    g.attrs.setdefault(name, args_)
            else:
                raise ValueError(f"liberty syntax near token {i}: {name}")
        return g

    assert toks[0][1] == "library"
    i = 1
    args = []
    assert toks[i] == ("p", "("); i += 1
    while toks[i] != ("p", ")"):
        args.append(toks[i][1]); i += 1
    i += 1
    assert toks[i] == ("p", "{"); i += 1
    return group("library", args)


def _table_typ(g: Group) -> float:
    """Table entry at a typical operating point: third input-slew row, smallest load."""
    rows = [[float(x) for x in v.replace(",", " ").split()] for v in g.attrs.get("values", [])]
    rows = [r for r in rows if r]
    if not rows:
        return 0.0
    r = rows[min(2, len(rows) - 1)]
    return r[0]          # smallest load: the tables include the energy of the load, which is added separately


def _expr(fn: str) -> str:
    """Liberty boolean expression -> Python expression on 0/1 integers. N(x) is NOT."""
    if "'" in fn:
        raise ValueError("postfix NOT is not supported: " + fn)
    out, prev_operand, neg = [], False, False
    for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*|[!()*+&|^]|[01]", fn):
        if tok == "!":
            if prev_operand:
                out.append("&"); prev_operand = False
            neg = not neg
        elif tok in "*&":
            out.append("&"); prev_operand = False
        elif tok in "+|":
            out.append("|"); prev_operand = False
        elif tok == "^":
            out.append("^"); prev_operand = False
        elif tok == "(":
            if prev_operand:
                out.append("&")                              # juxtaposition means AND
            out.append("N(" if neg else "("); neg = False; prev_operand = False
        elif tok == ")":
            out.append(")"); prev_operand = True
        else:
            if prev_operand:
                out.append("&")
            atom = tok if tok.isdigit() else f"v['{tok}']"
            out.append(f"N({atom})" if neg else atom); neg = False; prev_operand = True
    return " ".join(out)


class Cell:
    def __init__(self, g: Group):
        self.name = g.args[0]
        self.area = float(g.attrs.get("area", 0))
        self.leakage_pW = float(g.attrs.get("cell_leakage_power", 0))
        self.pins, self.cap, self.func, self.e_int = {}, {}, {}, {}
        self.ff = None
        # integrated clock-gating cell: enable, clock and gated-clock pins (None for ordinary cells)
        self.icg = None
        if "clock_gating_integrated_cell" in g.attrs:
            roles = {}
            for p in g.sub("pin"):
                for role in ("clock_gate_enable_pin", "clock_gate_clock_pin", "clock_gate_out_pin", "clock_gate_test_pin"):
                    if p.attrs.get(role, "false").strip('"') == "true":
                        roles.setdefault(role, []).append(p.args[0])
            self.icg = dict(enable=roles.get("clock_gate_enable_pin", []), clock=roles["clock_gate_clock_pin"][0],
                            out=roles["clock_gate_out_pin"][0], test=roles.get("clock_gate_test_pin", []))
        for f in ([] if "clock_gating_integrated_cell" in g.attrs else g.sub("ff") + g.sub("latch")):
            self.ff = dict(state=f.args[0], state_n=f.args[1] if len(f.args) > 1 else None,
                           next=_expr(f.attrs.get("next_state", f.attrs.get("data_in", "0"))),
                           clock=f.attrs.get("clocked_on", f.attrs.get("enable", "")).strip('"'),
                           clear=_expr(f.attrs["clear"]) if "clear" in f.attrs else None,
                           preset=_expr(f.attrs["preset"]) if "preset" in f.attrs else None)
        for p in g.sub("pin"):
            n = p.args[0]
            self.pins[n] = p.attrs.get("direction", "input").strip('"')
            self.cap[n] = float(p.attrs.get("capacitance", 0))          # pF
            if "function" in p.attrs:
                self.func[n] = _expr(p.attrs["function"])
            e = []
            for ip in p.sub("internal_power"):
                for t in ip.groups:
                    e.append(_table_typ(t))
            if e:
                self.e_int[n] = sum(e) / len(e)                          # pJ per transition, typical point


def load(path) -> dict[str, Cell]:
    lib = parse(path)
    return {c.args[0]: Cell(c) for c in lib.sub("cell")}


if __name__ == "__main__":
    import sys
    cells = load(sys.argv[1])
    for n in ("sg13g2_nand2_1", "sg13g2_inv_1", "sg13g2_dfrbp_1", "sg13g2_xor2_1", "sg13g2_a21oi_1"):
        c = cells[n]
        print(n, c.area, c.pins, c.cap, c.func, {k: round(v, 5) for k, v in c.e_int.items()}, c.ff)
