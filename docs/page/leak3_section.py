"""Section 13d of the page: the 3T3R leakage evidence at transistor level (8 November 2026).
Reads results/security/{tvla_circuit*,attack_sparsity,sa_transient}.json; anything missing shows as 'running'."""
import json
from html import escape as esc
from pathlib import Path

R = Path(__file__).resolve().parents[2] / "results" / "security"


def J(n):
    f = R / n
    return json.loads(f.read_text()) if f.exists() else None


def tv(js, enc, sec="weights"):
    for c in (js or {}).get("cases", []):
        if c["encoding"] == enc and c["secret"] == sec:
            return c
    return None


def cell(c):
    if c is None:
        return '<td class="num">running</td>'
    cls = "bad" if c["leaks"] else "ok"
    return f'<td class="num"><span class="tag t-{"warn" if c["leaks"] else "ok"}">{c["max_abs_t"]:.2f}</span></td>'


def attack_chart(att):
    W, H, x0, x1, y0, y1 = 760, 300, 70, 600, 250, 30
    ns = [r["reads_per_row"] for r in att["results"]["2T2R"]]
    import math
    lx = lambda n: x0 + (math.log10(n) - 0) / math.log10(ns[-1]) * (x1 - x0)
    ly = lambda v: y0 - (v + 0.2) / 1.2 * (y0 - y1)
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Sparsity-recovery attack: correlation between true and estimated zero counts per row '
         f'against reads per row. 2T2R rises to {att["results"]["2T2R"][-1]["corr_mean"]}; one-of-three stays near zero.">']
    for v in (-0.2, 0, 0.2, 0.4, 0.6, 0.8, 1.0):
        o.append(f'<line x1="{x0}" y1="{ly(v):.1f}" x2="{x1}" y2="{ly(v):.1f}" stroke="var(--grid)"/>'
                 f'<text x="{x0 - 8}" y="{ly(v) + 4:.1f}" text-anchor="end" class="tick">{v:g}</text>')
    for n in ns:
        o.append(f'<text x="{lx(n):.1f}" y="{y0 + 18}" text-anchor="middle" class="tick">{n:,}</text>')
    o.append(f'<line x1="{x0}" y1="{ly(0):.1f}" x2="{x1}" y2="{ly(0):.1f}" stroke="var(--axis)"/>')
    for key, col, lab in (("2T2R", "var(--s2)", "2T2R"), ("1of3", "var(--s1)", "3T3R one-of-three")):
        pts = att["results"][key]
        o.append('<polyline fill="none" stroke="' + col + '" stroke-width="2" points="' +
                 " ".join(f'{lx(p["reads_per_row"]):.1f},{ly(p["corr_mean"]):.1f}' for p in pts) + '"/>')
        for p in pts:
            o.append(f'<circle cx="{lx(p["reads_per_row"]):.1f}" cy="{ly(p["corr_mean"]):.1f}" r="4.5" fill="{col}" stroke="var(--surface)" stroke-width="2" '
                     f'data-tip="{esc(lab)}, {p["reads_per_row"]:,} reads per row: correlation {p["corr_mean"]}, rows exact {p["rows_exact_mean"]:.0%}"/>')
        q = pts[-1]
        o.append(f'<text x="{lx(q["reads_per_row"]) + 10:.1f}" y="{ly(q["corr_mean"]) + 4:.1f}" class="sm">{esc(lab)}</text>')
    o.append(f'<text x="{(x0 + x1) / 2}" y="{H - 6}" text-anchor="middle" class="axl">reads of each row averaged by the attacker (log scale)</text>'
             f'<text x="16" y="{(y0 + y1) / 2}" transform="rotate(-90 16 {(y0 + y1) / 2})" text-anchor="middle" class="axl">correlation, true vs estimated zeros</text></svg>')
    a2 = att["results"]["2T2R"][-1]
    return (f'<figure>{"".join(o)}<figcaption>A profiled attacker who knows which row each read belongs to estimates every row\'s number of zero '
            f'weights from its mean current (fit on a second device). On 2T2R the correlation reaches {a2["corr_mean"]} and '
            f'{a2["rows_exact_mean"]:.0%} of rows are exact (a best guess gets about 17 %); this attacker uses the summed current only, '
            f'and one using every window does better (below). On 3T3R neither estimate carries information about the zero count. 20 devices per point; '
            f'<code>tools/attack_sparsity.py</code>.</figcaption></figure>')


def mw_txt(att):
    mw = att.get("results_all_windows")
    if not mw:
        return ""
    a, b = mw["2T2R"][-1], mw["1of3"][-1]
    return (f'<p class="sm">A second attacker fits all five 50 ns windows of the read (profiled on 8 devices): 2T2R correlation {a["corr_mean"]}, '
            f'{a["rows_exact_mean"]:.0%} of rows exact at {a["reads_per_row"]:,} reads per row; 3T3R {b["corr_mean"]}, {b["rows_exact_mean"]:.0%} '
            f'(the best-guess rate).</p>')


def section():
    circ, red = J("tvla_circuit.json"), J("tvla_circuit_redraw.json")
    al, rot = J("tvla_circuit_redraw_aligned.json"), J("tvla_circuit_redraw_aligned_rot.json")
    att, sa, sp = J("attack_sparsity.json"), J("sa_transient.json"), J("sa_programmed_states.json")
    rows = ""
    for enc, lab in (("2T2R", "2T2R (this chip)"), ("1of3", "3T3R one-of-three (next chip)"),
                     ("4T4R", "4T4R as proposed (one of four; a fourth device always HRS)")):
        rows += (f"<tr><td>{lab}</td>{cell(tv(circ, enc))}{cell(tv(red, enc))}"
                 + (cell(tv(al, enc)) + cell(tv(rot, enc)) if enc != "4T4R" else '<td class="num">—</td><td class="num">—</td>') + "</tr>")
    ntr = (red or circ)["cases"][0]["traces_per_group"]
    mu = sa["mean_uA_nominal"]
    il, ih = mu["60uS"], mu["4.5uS"]
    import re
    return re.sub(r"(\d)%", r"\1 %", _sec(circ, red, al, rot, att, sa, sp, rows, ntr, il, ih))


def _sec(circ, red, al, rot, att, sa, sp, rows, ntr, il, ih):
    a1, r1 = tv(al, "1of3"), tv(rot, "1of3")
    r = lambda w, a, b: w / ((1 - a) * b[0] + a * b[1])
    pl, ph = (sp["mean_uA"]["29.9uS"], sp["mean_uA"]["0.31uS"]) if sp else (None, None)
    prog = (f" With the states the drawn drivers program (about 30 µS and 0.31 µS) the ratio is {r(pl + 2 * ph, 1 / 3, (pl + ph, 2 * ph)):.2f}× at one third "
            f"and {r(pl + 2 * ph, 0.7, (pl + ph, 2 * ph)):.2f}× at 70 % zeros.") if sp else ""
    return f"""
<section id="leak3">
<h2>13d · 3T3R leakage with sense-amplifier waveforms</h2>
<p>Every sense amplifier of the tile is a SPICE transient template of the drawn SKY130 sense amplifier with its own frozen mismatch sample
({sa['mismatch_samples']} Monte Carlo samples, <code>chip/sky130/sim/sa_transient.py</code>): {il:.2f} µA mean supply current on a 60 µS LRS read,
{ih:.2f} µA on a 4.5 µS HRS read, mismatch {sa['mismatch_sd_uA_LRS60']:.3f} µA sd on LRS. A 2T2R zero weight draws {2 * ih:.2f} µA, a ±1 weight
{il + ih:.2f} µA; a one-of-three weight always draws {il + 2 * ih:.2f} µA. Revision 4.7 logic, 5 µA rms noise per 50 ns window
(<code>tools/tvla_circuit.py</code>). Evidence about the model, not silicon.</p>
<p>Each test answers a different question. <b>One frozen instance</b>: the test also sees that instance's conductances, a fingerprint present
for every cell. <b>Reprogrammed every trace, shuffled</b>: with a random start row every sample sees the matrix average, so the test only sees the
matrix-wide zero count. <b>Row-aligned</b>: each row and each position; a margin check gives such reads, also under LOCK.</p>
<div class="tbl"><table><thead><tr><th>Cell</th><th class="num">shuffled, one frozen instance</th><th class="num">shuffled, reprogrammed</th>
<th class="num">row-aligned, reprogrammed</th><th class="num">row-aligned, sense-amp rotation (proposal)</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<p class="sm">Max Welch |t| over 360 samples, {ntr:,} traces per group; leaks above 4.5.</p>
<p><b>What the row-aligned test found</b> (council red team, 8 November). One-of-three removes the zero count, but each sense amplifier's own
mismatch makes the current depend on <i>which</i> device holds the LRS: {a1['max_abs_t'] if a1 else 'not run'} row-aligned. That residual is specific
to one chip: profiling another chip does not calibrate it, but reprogramming a row of the victim would (revision 4.7 ran programming under LOCK; revision 4.9 refuses it,
13e), and so do collisions between rows. <b>Proposal:</b> rotate at random, on every read, which of a cell's three sense amplifiers reads
which device (a 3:1 switch per amplifier, decode rotated back in logic): {r1['max_abs_t'] if r1 else 'not run'} in the model. Not drawn, not in the RTL.</p>
{attack_chart(att)}
{mw_txt(att)}
<p>Cost of a constant LRS count: the one-of-three read current is {r(il + 2 * ih, 1 / 3, (il + ih, 2 * ih)):.2f}× the 2T2R mean at one third zero weights,
{r(il + 2 * ih, 0.7, (il + ih, 2 * ih)):.2f}× at 70 % zeros (SkyWater's published states).{prog} Gain besides security: every single-device flip gives an invalid code
(9 of 9; 2 of 6 in 2T2R, where the other 4 become another valid weight). Still open (the two LOCK gaps are closed in revision 4.9, 13e): the
sense register's switching; the programming profile with reprogrammed groups; localized EM on the separate bit lines; trained weights.</p>
</section>
"""
