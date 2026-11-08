// Fig B: one ReRAM device, cut in half through its filament, at nanometre scale. HfO2 thickness, gap range and the
// current law are SkyWater's model as chip/sky130/sim/macro_sim.py uses it (Tox 5 nm; I = I0 exp(-g/g0) sinh(V/V0),
// I0 6.14e-5 A, g0 0.2751 nm, V0 0.43 V; gap 0.1 to 1.7 nm). Electrode and Ti thicknesses are not published: drawn
// 4 nm and 3 nm. The filament's width and taper are schematic. Built with the Anatomy kit (MIT).
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import * as k from "../ext_anatomy/anatomy/kit/iso-kit.mjs";
import * as A from "../ext_anatomy/anatomy/kit/audit.mjs";
import { kitScript } from "../ext_anatomy/anatomy/scripts/inline-kit.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const N = 10;                       // world units per nanometre
const W = 600, H = 420;
const nm = (v) => v * N;
const SL = { x: 0, y: 0, w: nm(16), d: nm(8), r: 0 };   // a 16 nm x 8 nm slice of the 260 nm device; cut face at y = 8 nm
const LAY = [   // [name, z0 nm, z1 nm, tone, description]
  ["stand.plug", 0, 3, "lo", "via1 plug (top of it; the plug is 150 nm wide): connects to metal1 and the transistor drain below. Made of: not published by SkyWater"],
  ["tin_bottom", 3, 7, "mid", "bottom electrode: titanium nitride (TiN), per SkyWater's ReRAM documentation (thickness not published; drawn 4 nm)"],
  ["hfo2", 7, 12, "hi", "switching oxide: hafnium oxide (HfO2), 5 nm in SkyWater's model; insulating except where the filament of oxygen vacancies (missing oxygen atoms) bridges it"],
  ["ti", 12, 15, "lo", "titanium (Ti) layer, per SkyWater's ReRAM documentation (thickness not published; drawn 3 nm); in the usual account of such stacks it takes oxygen from the HfO2 and leaves vacancies there"],
  ["tin_top", 15, 19, "mid", "top electrode: titanium nitride (TiN), per SkyWater's ReRAM documentation (thickness not published; drawn 4 nm)"],
  ["met2", 19, 22, "lo", "metal2 bit line (bottom of it): the top electrode connection. Made of: aluminum (Al), per T. Edwards (Efabless); SkyWater's own documents do not say"],
];
const FX = nm(8), FY = SL.d;        // filament axis on the cut face
const OX = [nm(7), nm(12)];
const GAP = [0.1, 1.7];

const P = k.fitProjection(k.boxCorners(SL, 0, nm(22)), W, H, { pad: 26, azimuth: 52, elevation: 26 });
const R = A.recorder(P);
const esc = (t) => t.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
const out = [`<path class="iso-halo" d="${k.haloOf(SL, 0, nm(3), P)}"/>`];
for (const [name, z0, z1, tone, say] of LAY) {
  const svg = k.solidSvg(k.slabOf(SL, nm(z0), nm(z1 - z0), P, 2, 0.6), { tone });
  const mat = { "stand.plug": "via1", tin_bottom: "tin", tin_top: "tin" }[name] ?? name;
  R.put({ name, at: [SL.w / 2, SL.d / 2, nm((z0 + z1) / 2)], svg: `<g data-mat="${mat}" data-say="${esc(say)}">${svg}</g>`, shapes: [R.solid(A.slab(SL, nm(z0), nm(z1 - z0), { name }, 2))] });
}
A.settle(R, P);
R.items.sort((a, b) => a.key - b.key);
A.auditOrExit(R, P);
out.push(...R.items.map((i) => i.svg));

// nanometre ruler on the cut face: ticks hang from the left edge of the face, 1 nm apart, majors at the interfaces
const at = (p) => k.iso(p, P).map((v) => Math.round(v * 10) / 10);
const seg = (a, b) => { const [p, q] = [at(a), at(b)]; return `M${p[0]} ${p[1]}L${q[0]} ${q[1]}`; };
let minor = "", major = "";
for (let z = 1; z < 22; z++) {
  const isMajor = LAY.some(([, z0]) => z0 === z);
  const len = isMajor ? 1.2 : 0.6;
  (isMajor ? (major += seg([0, FY, nm(z)], [nm(len), FY, nm(z)])) : (minor += seg([0, FY, nm(z)], [nm(len), FY, nm(z)])));
}
out.push(k.lineSvg(minor, { tone: "lo" }), k.lineSvg(major, { tone: "mid" }));
// oxygen vacancies scattered in the oxide (schematic positions, fixed), on the cut face
let seed = 7; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
const vac = [];
for (let i = 0; i < 34; i++) { const x = nm(1.2 + rnd() * 13.6), z = OX[0] + nm(0.4) + rnd() * (OX[1] - OX[0] - nm(0.8)); if (Math.abs(x - FX) > nm(1.8)) vac.push(at([x, FY, z])); }
out.push(k.dotsSvg(vac, { size: 0.7, tone: "mid" }));
// the filament: its section on the cut face, rebuilt live as the gap changes
const filament = (gap) => {
  const tip = OX[0] + nm(gap), top = OX[1];
  const pts = [[FX - nm(1.3), FY, top], [FX + nm(1.3), FY, top], [FX + nm(0.75), FY, tip], [FX - nm(0.75), FY, tip]].map(at);
  return "M" + pts.map((p) => p.join(" ")).join("L") + "Z";
};
out.push(`<path data-part="filament" class="bf-fil" d="${filament(GAP[0])}"/>`);
const css = `.bf-fil{fill:var(--anatomy-lit);stroke:var(--anatomy-lit);stroke-width:.6;stroke-linejoin:round}`;

const svg = k.figureSvg({
  width: W, height: H,
  label: "One ReRAM device cut in half through its conducting filament, at nanometre scale: the top of the via1 plug, the TiN bottom electrode, the 5 nanometre hafnium oxide, the titanium layer, the TiN top electrode and the bottom of the metal2 bit line. A filament of oxygen vacancies hangs from the titanium side toward the bottom electrode; the gap left between its tip and the electrode sets the device's conductance.",
  body: out,
});

const MODEL = { I0: 6.14e-5, g0: 0.2751, V0: 0.43, V: 0.2, set: 27.36, reset: 7.93, read: 12.4 };
const live = `{
const root = document.querySelector('[data-fig="reramcut"]');
const stage = root.querySelector('.iso-stage');
const readout = root.querySelector('[data-readout]');
const fil = stage.querySelector('[data-part="filament"]');
const line = root.querySelector('.iso-say'); let hov = null;
const P = ${JSON.stringify(P)};
const M = ${JSON.stringify(MODEL)};
const FX = ${FX}, FY = ${FY}, OX = ${JSON.stringify(OX)}, NM = ${N}, GAP = ${JSON.stringify(GAP)};
const still = matchMedia('(prefers-reduced-motion: reduce)');
const at = (p) => iso(p, P).map((v) => Math.round(v * 10) / 10);
const filament = ${filament.toString().replace(/nm\(/g, "NMf(")};
const NMf = (v) => v * NM;
const G = (g) => M.I0 * Math.exp(-g / M.g0) * Math.sinh(M.V / M.V0) / M.V * 1e6;
let gap = GAP[1], target = GAP[1], frame = 0, last = 0, visible = false, touring = !still.matches, clock = 0, naming = false, idle = 0;
const tourAt = (t) => (Math.floor(t / 3.2) % 2 ? GAP[1] : GAP[0]);
function say() {
  const g = G(gap), i = g * M.V;
  const state = g >= M.set ? 'it passes the set verify (27.4 µS)' : g <= M.reset ? 'it passes the reset verify (7.9 µS)' : 'it is between the two verify levels, so programming would continue';
  const t = 'gap ' + gap.toFixed(2) + ' nm · ' + g.toFixed(g < 10 ? 2 : 1) + ' µS · reads ' + (g > M.read ? '1' : '0');
  if (readout.textContent !== t) readout.textContent = t;
  const L = 'Gap ' + gap.toFixed(2) + ' nm: ' + i.toFixed(2) + ' µA at 0.2 V (' + g.toFixed(g < 10 ? 2 : 1) + ' µS), ' + (g > M.read ? 'above' : 'below') + ' the read reference of about 12.4 µS; ' + state + '.';
  if (!hov && line.textContent !== L) line.textContent = L;
  stage.setAttribute('aria-valuenow', gap.toFixed(2)); stage.setAttribute('aria-valuetext', t);
}
function draw() { fil.setAttribute('d', filament(gap)); say(); }
function tick(now) {
  const dt = last ? Math.min((now - last) / 1000, 1 / 30) : 1 / 60; last = now;
  if (touring) { clock += dt; target = tourAt(clock); }
  gap = still.matches ? target : gap + (target - gap) * (1 - Math.exp(-dt / 0.45));
  if (Math.abs(target - gap) < 0.002) gap = target;
  draw();
  frame = visible && (touring || gap !== target) ? requestAnimationFrame(tick) : 0;
}
const run = () => { if (!frame && visible) { last = 0; frame = requestAnimationFrame(tick); } };
const steer = (g) => { touring = false; target = Math.min(GAP[1], Math.max(GAP[0], g)); clearTimeout(idle); idle = setTimeout(() => { touring = !still.matches; clock = 0; run(); }, 5000); run(); };
new IntersectionObserver((e) => { visible = e[e.length - 1].isIntersecting; if (visible) run(); }, { rootMargin: '80px 0px' }).observe(stage);
stage.addEventListener('pointermove', (e) => {
  const part = e.target.closest('[data-say]');
  if (part !== hov) { if (hov) hov.removeAttribute('data-hov'); hov = part; if (part) { part.setAttribute('data-hov', ''); line.textContent = part.getAttribute('data-say'); } else say(); }
  const b = stage.getBoundingClientRect(); const share = Math.min(1, Math.max(0, ((e.clientX - b.left) / b.width - 0.2) / 0.6));
  steer(GAP[0] + share * (GAP[1] - GAP[0]));
});
stage.addEventListener('pointerleave', () => { if (hov) hov.removeAttribute('data-hov'); hov = null; say(); });
stage.addEventListener('keydown', (e) => {
  let g = null;
  if (e.key === 'ArrowRight' || e.key === 'ArrowUp') g = target + 0.1;
  if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') g = target - 0.1;
  if (e.key === 'Home') g = GAP[0]; if (e.key === 'End') g = GAP[1];
  if (g === null) return; e.preventDefault(); naming = false; steer(Math.round(g * 10) / 10);
});
if (still.matches) touring = false;
draw();
}`;

const fig = k.plateHtml({
  fig: "Fig B",
  title: "One device, cut in half",
  hint: "Move across or ← →: gap",
  readout: "",
  keys: [
    { mark: "lit", label: "Filament of oxygen vacancies (its section on the cut face)" },
    { mark: "raised", label: "HfO2, 5 nm; electrodes above and below" },
  ],
  caption: "A 16 nm wide slice of the 260 nm device, cut through its filament; ticks on the cut edge are 1 nm apart, long ticks at the layer boundaries. Setting grows the filament across the oxide and reset shortens it; the remaining gap, 0.1 to 1.7 nm, sets the current, I = I0·exp(−gap/g0)·sinh(V/V0) with SkyWater's constants. The readout compares the conductance at 0.2 V with the chip's read reference (about 12.4 µS) and its verify levels (set 27.4 µS, reset 7.9 µS, worst corners). The HfO2 thickness and gap range are SkyWater's model; the electrode and Ti thicknesses are not published (drawn 4 and 3 nm), and the filament's width and taper, which electrode the gap sits at, and the vacancy positions are schematic: SkyWater's model tracks only the gap length.",
  body: `<div class="iso-stage" tabindex="0" role="slider" aria-label="ReRAM filament gap in nanometres: arrow keys change it" aria-valuemin="0.1" aria-valuemax="1.7" aria-valuenow="0.1">${svg}</div>`,
});
const SAYCSS = `.iso-mats{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12.5px;color:var(--anatomy-text)}.iso-mats>span{display:inline-flex;align-items:center;gap:6px}.iso-mats i{width:11px;height:11px;border-radius:2px;background:var(--anatomy-top);box-shadow:inset 0 0 0 1px var(--anatomy-shade-0)}.iso-say{display:block;min-height:3.2em;margin:0 0 6px;font:12.5px/1.6 var(--anatomy-mono);color:var(--anatomy-strong)}`;
const fragX = `<div class="iso iso-embed" data-fig="reramcut"><style>${css}${SAYCSS}[data-hov]>.iso-solid>.iso-edge{stroke:var(--anatomy-strong);stroke-width:1.4px}</style>${fig.replace('<figcaption class="iso-legend">', '<figcaption class="iso-legend"><span class="iso-say" aria-live="polite">Point at a part to see what it is.</span><span class="iso-mats"><span data-mat="via1"><i></i>via1 plug</span><span data-mat="tin"><i></i>TiN</span><span data-mat="hfo2"><i></i>HfO2</span><span data-mat="ti"><i></i>Ti</span><span data-mat="met2"><i></i>metal2 (Al)</span></span>')}</div>`;
const frag = fragX;
writeFileSync(join(HERE, "figB.frag.json"), JSON.stringify({ html: frag, script: live }));
for (const theme of ["dark", "light"]) {
  writeFileSync(join(HERE, `figB-${theme}.html`), k.pageHtml({ title: "ReRAM device", theme, body: frag.replace('class="iso iso-embed"', 'class="iso-embed"'), script: kitScript() + live }));
}
console.log("gap for 27.36, 12.4, 7.93 uS:", [27.36, 12.4, 7.93].map((g) => (-MODEL.g0 * Math.log(g * 1e-6 * MODEL.V / (MODEL.I0 * Math.sinh(MODEL.V / MODEL.V0)))).toFixed(3)));
