"""Small driver for Gnucap decks: build a deck, run it, parse the printed tables.

Environment variables
  GNUCAP      gnucap executable (default: "gnucap" from PATH)
  IHP_GNUCAP  path to <IHP-Open-PDK>/ihp-sg13g2/libs.tech/gnucap with the model plugins built
              (make -C models sg13g2_moshv_paramset sg13g2_moslv_paramset)
The ReRAM plugin is built by build_reram.sh into ./plugins.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
GNUCAP = os.environ.get("GNUCAP", "gnucap")
IHP = os.environ.get("IHP_GNUCAP", "")
RERAM_SO = HERE / "plugins" / "reram_stanford_ihp.so"

_SUFFIX = {"f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "K": 1e3, "Meg": 1e6, "G": 1e9, "T": 1e12}
_NUM = re.compile(r"^([-+]?[0-9]*\.?[0-9]*(?:[eE][-+]?[0-9]+)?)(Meg|[fpnumKGT])?$")


def num(tok: str) -> float:
    m = _NUM.match(tok)
    if not m or m.group(1) in ("", "-", "+", "."):
        raise ValueError(tok)
    return float(m.group(1)) * _SUFFIX.get(m.group(2), 1.0)


def header(corner: str = "tt", lv: bool = False, mc: bool = False) -> str:
    """Deck preamble: load the ReRAM plugin and the IHP PSP103 transistor models for one corner."""
    if not IHP:
        raise RuntimeError("set IHP_GNUCAP to <IHP-Open-PDK>/ihp-sg13g2/libs.tech/gnucap")
    lines = [
        "load mgsim",
        f"load {RERAM_SO}",
        "verilog",
    ]
    if mc:      # PDK commands for Monte Carlo ($seed sweeps, $rdist_normal); must be loaded before the models
        lines += [f"load {IHP}/plugins/gnucap"]
    lines += [
        f"load {IHP}/plugins/models/sg13g2_moshv_paramset.so",
        f"include {IHP}/models/sg13g2_moshv_module.va",
        f"include {IHP}/models/cornerMOShv.va",
        f"moshv_{corner} corner_moshv();",
    ]
    if lv:
        lines += [
            f"load {IHP}/plugins/models/sg13g2_moslv_paramset.so",
            f"include {IHP}/models/sg13g2_moslv_module.va",
            f"include {IHP}/models/cornerMOSlv.va",
            f"moslv_{corner} corner_moslv();",
        ]
    return "\n".join(lines) + "\n"


def run(deck: str, timeout: int = 600, keep: str | None = None) -> list[dict]:
    """Run a deck. Returns one dict per printed table: {'cols': [...], 'data': ndarray}."""
    with tempfile.NamedTemporaryFile("w", suffix=".gc", dir=HERE, delete=False) as f:
        f.write(deck)
        path = f.name
    try:
        out = subprocess.run([GNUCAP, path], capture_output=True, text=True, timeout=timeout, cwd=HERE)
    finally:
        if keep:
            os.replace(path, HERE / keep)
        else:
            os.unlink(path)
    text = out.stdout + out.stderr
    tables: list[dict] = []
    cur = None
    problems = []
    for line in text.splitlines():
        if line.startswith("#"):
            names = line[1:].split()
            if line[1:2].isspace():          # DC sweeps print the swept variable without a name
                names = ["sweep"] + names
            cur = {"cols": names, "rows": []}
            tables.append(cur)
            continue
        if re.search(r"\^ \?|open circuit|did not converge|convergence failure|zero time step|very backward", line):
            problems.append(line.strip())
        if cur is None:
            continue
        toks = line.split()
        if len(toks) != len(cur["cols"]):
            continue
        try:
            cur["rows"].append([num(t) for t in toks])
        except ValueError:
            continue
    for t in tables:
        t["data"] = np.array(t.pop("rows"), dtype=float).reshape(-1, len(t["cols"]))
    if not tables:
        raise RuntimeError("gnucap produced no table:\n" + text[-3000:])
    tables[0]["problems"] = problems
    tables[0]["raw"] = text
    return tables


def col(table: dict, name: str) -> np.ndarray:
    return table["data"][:, table["cols"].index(name)]
