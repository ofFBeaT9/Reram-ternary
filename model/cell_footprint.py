"""Lower bound on the 2T2R cell footprint from the front-end layout rules of the open PDK.

Counts only what the select transistor needs: gate, contacts, active spacing. It does NOT include the ReRAM
element and its rules (not in the open PDK), bit-line and source-line routing, word-line straps or substrate
taps. The real cell will be larger; the foundry's MEMRES cell decides.

Arrangement assumed: word lines are poly lines along a row; two rows share one source diffusion and are
mirrored about it; each cell has its own drain diffusion (it connects to that cell's ReRAM), so neighbouring
drains are separated by an active-to-active space; devices of one row are separated by the same space.

Writes results/cell_footprint.json.
"""
import json, os, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
W_UM, ROWS, COLS = 4.5, 72, 24

deck = Path(os.environ["IHP_GNUCAP"]).parent / "klayout" / "tech" / "drc" / "rule_decks" / "sg13g2_tech_default.json"
r = json.loads(deck.read_text())["drc_rules"]

L      = r["Gat_a3"]          # minimum gate length of the 3.3 V NMOS
cnt    = r["Cnt_a"]           # contact size
cnt_g  = r["Cnt_f"]           # contact to gate
cnt_a  = r["Cnt_c"]           # active enclosure of contact
act_s  = r["Act_b"]           # active to active space

shared_source = cnt_g + cnt + cnt_g                 # one row of contacts between two gates
own_drain     = cnt_g + cnt + cnt_a                 # one row of contacts, then the end of the active area
pair_height   = own_drain + L + shared_source + L + own_drain + act_s
row_pitch     = pair_height / 2
dev_pitch     = W_UM + act_s                        # along the word line, per device
area_dev      = row_pitch * dev_pitch
n_dev         = 2 * ROWS * COLS

# yardstick: the same 3,456 bits in the standard-cell flip-flop that synthesis uses (cell area only)
lib = Path(os.environ["IHP_STDCELL_LIB"]).read_text()
ff_area = float(re.search(r'cell\s*\(\s*"?sg13g2_dfrbpq_1"?\s*\)\s*\{.*?\barea\s*:\s*([0-9.]+)', lib, re.S).group(1))
ff_mm2 = n_dev * ff_area * 1e-6

out = dict(
    rules_um=dict(Gat_a3=L, Cnt_a=cnt, Cnt_f=cnt_g, Cnt_c=cnt_a, Act_b=act_s), transistor_width_um=W_UM,
    row_pitch_um=round(row_pitch, 4), device_pitch_um=round(dev_pitch, 4), column_pitch_um=round(2 * dev_pitch, 4),
    area_per_device_um2=round(area_dev, 3), area_per_ternary_cell_um2=round(2 * area_dev, 3),
    devices=n_dev, array_area_mm2=round(n_dev * area_dev * 1e-6, 5),
    array_height_um=round(ROWS * row_pitch, 1), array_width_um=round(COLS * 2 * dev_pitch, 1),
    assumed_in_tile_model=dict(row_pitch_um=2.0, device_pitch_um=3.28, area_per_device_um2=6.56,
                               array_area_mm2=round(n_dev * 6.56e-6, 5)),
    flipflop=dict(cell="sg13g2_dfrbpq_1", area_um2=ff_area, storage_mm2=round(ff_mm2, 4),
                  ratio_to_rule_count=round(ff_mm2 / (n_dev * area_dev * 1e-6), 2), ratio_to_assumed_pitch=round(ff_mm2 / (n_dev * 6.56e-6), 2)),
    contacts=dict(pitch_um=round(r["Cnt_a"] + r["Cnt_b"], 3), em_limit_mA_each=0.3, fit_in_width=int((W_UM - 2 * r["Cnt_c"] + r["Cnt_b"]) // (r["Cnt_a"] + r["Cnt_b"]))),
    note="lower bound from transistor rules only; ReRAM element, routing, straps and taps not included",
)
(ROOT / "results" / "cell_footprint.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
