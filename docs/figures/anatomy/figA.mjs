// Fig A: one 2T2R weight of the SKY130 array, as built: every rectangle from the cell's GDS (structure rr2t2r of
// layout/sky130/tcim_sky130_array.gds), every height from open_pdks' sky130B Magic tech file. The dielectric between the
// layers is removed so the conductors stand free. Built with the Anatomy kit (github.com/wheresryan22/anatomy, MIT).
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import * as k from "../ext_anatomy/anatomy/kit/iso-kit.mjs";
import * as A from "../ext_anatomy/anatomy/kit/audit.mjs";
import { COLORS } from "./mat_css.mjs";
import { kitScript } from "../ext_anatomy/anatomy/scripts/inline-kit.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const G = JSON.parse(readFileSync(join(HERE, "cell.json"), "utf8"));   // written by cell_json.py from the GDS and the tech file
const U = 40;                       // world units per micrometre
const W = 600, H = 400;
const um = (v) => v * U;
const plan = ([x0, y0, x1, y1], r = 0) => ({ x: um(x0), y: um(y0), w: um(x1 - x0), d: um(y1 - y0), r });
const Z = Object.fromEntries(Object.entries(G.z).map(([n, [a, b]]) => [n, [um(a), um(b)]]));
const SUB = um(0.05);               // the silicon is cut 0.28 um below its surface (0.3262 um in Magic's heights)
const SI = Z.poly[0];               // silicon surface = bottom of poly (0.3262 um)
const RR = [um(G.rr_split), Z.via1[1]];   // ReRAM stack in the top of the via1 slot (split as in the cross-sections)
const CELL = { x: 0, y: 0, w: um(3.6), d: um(3.0), r: 0 };

const P = k.fitProjection(k.boxCorners(CELL, SUB, Z.met2[1]), W, H, { pad: 14, azimuth: 38, elevation: 36 });
const R = A.recorder(P);
const S = (paths, style) => k.solidSvg(paths, style);

// which conductors carry the read current of the BL+ device (p), the BL- device (n), or either (s)
const xc = (r) => (r[0] + r[2]) / 2;
const sideOf = (r) => (xc(r) < 1.5 ? "p" : xc(r) > 2.1 ? "n" : "s");

const esc = (t) => t.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
// what each part is made of; sources: SkyWater's ReRAM documentation (sky130_fd_pr_reram), T. Edwards (Efabless),
// "Introduction to the SkyWater PDK" slides, 2021 (li = TiN, "5 layers of aluminum metal"); SkyWater does not publish the rest
const MAT = {
  silicon: "single-crystal silicon (Si), lightly doped p-type (SkyWater: P-substrate; which acceptor element is not published, boron being the usual one)",
  diff: "silicon (Si) heavily doped n-type with donor atoms (element not published by SkyWater; arsenic or phosphorus are usual)",
  tap: "silicon (Si) heavily doped p-type with acceptor atoms (element not published; boron is usual)",
  poly: "polycrystalline silicon (poly-Si; SkyWater's layer table: Polysilicon), doped to conduct; it rests on the gate oxide, 11.6 nm in the transistor model (too thin to draw; SkyWater calls it oxide and does not publish its composition, silicon dioxide SiO2 being standard)",
  licon: "not published by SkyWater",
  li1: "titanium nitride (TiN), per T. Edwards (Efabless); SkyWater's own documents do not say",
  mcon: "not published by SkyWater",
  met1: "aluminum (Al), per T. Edwards (Efabless): \"5 layers of aluminum metal\"; SkyWater's own documents do not say",
  via1: "not published by SkyWater",
  reram: "titanium nitride (TiN) top electrode / titanium (Ti) / hafnium oxide (HfO2) / titanium nitride (TiN) bottom electrode, per SkyWater's ReRAM documentation",
  met2: "aluminum (Al), per T. Edwards (Efabless); SkyWater's own documents do not say",
};
const SOL = [];
function put(name, r, z0, z1, { tone = "mid", path = null, flat = false, bevel = 0, say = "" } = {}) {
  const p = plan(r);
  const kind = name.replace("stand.", "");
  say = `${say}. Made of: ${MAT[kind]}.`;
  SOL.push({ p: [p.x, p.y, p.w, p.d], z: [z0, z1], tone, bevel, path, say, mat: kind });
  const svg = S(k.slabOf(p, z0, z1 - z0, P, 2, bevel), { tone, crease: flat ? "none" : "faint", flat });
  const at = [p.x + p.w / 2, p.y + p.d / 2, (z0 + z1) / 2];
  R.put({ name, at, svg: `<g${path ? ` data-path="${path}"` : ""} data-mat="${kind}" data-say="${esc(say)}">${svg}</g>`, shapes: [R.solid(A.slab(p, z0, z1 - z0, { name }, 2))] });
}
const dims = (r) => `${(r[2] - r[0]).toFixed(2)} × ${(r[3] - r[1]).toFixed(2)} µm`;
const col = (r) => (sideOf(r) === "p" ? "BL+" : "BL−");

// silicon: the cut block, the n+ drain/source diffusions and the p+ tie, flush with its surface
put("stand.silicon", [0, 0, 3.6, 3.0], SUB, SI, { tone: "lo", say: "p-type silicon, cut 0.28 µm below its surface; the cell is 3.6 × 3.0 µm" });
G.rects.diff.forEach((r) => put("diff", r, SI - 0.2, SI + 0.25, { tone: "lo", path: sideOf(r), say: `n+ diffusion of the ${col(r)} select transistor: drain toward the ReRAM, source toward the shared source strip; the channel lies under the word line` }));
G.rects.tap.forEach((r) => put("tap", r, SI - 0.2, SI + 0.25, { tone: "lo", say: "p+ tie in the silicon: holds the substrate at ground" }));
// word line (poly), contacts, local interconnect, mcon, metal1, via1, ReRAM, metal2
G.rects.poly.forEach((r) => put("poly", r, Z.poly[0] + 0.25, Z.poly[1], { tone: "mid", bevel: 0.4, say: `polysilicon word line, ${(r[3] - r[1]).toFixed(2)} µm wide: the gate of both select transistors; raising it selects the row` }));
G.rects.licon.forEach((r) => put("licon", r, SI + 0.25, Z.li1[0], { tone: "mid", path: r[1] > 2.3 ? null : sideOf(r), say: r[1] > 2.3 ? "contact (licon), 0.17 µm: p+ tie to the tie strip" : `contact (licon), 0.17 µm: ${r[1] > 1.5 ? "drain" : "source"} of the ${col(r)} transistor to local interconnect` }));
G.rects.li1.forEach((r) => put("li1", r, Z.li1[0], Z.li1[1], { tone: "mid", path: r[1] > 2.3 ? null : r[2] - r[0] > 2 ? "s" : sideOf(r), bevel: 0.3,
  say: r[1] > 2.3 ? "local interconnect (li1): tie strip along the row" : r[2] - r[0] > 2 ? "local interconnect (li1): joins both sources to the source line" : `local interconnect (li1): drain pad of the ${col(r)} transistor` }));
G.rects.mcon.forEach((r) => put("mcon", r, Z.mcon[0], Z.mcon[1], { tone: "mid", path: sideOf(r), say: sideOf(r) === "s" ? "mcon: source strip to the source line (metal1)" : `mcon: ${col(r)} drain pad up to its metal1 pad` }));
G.rects.met1.forEach((r) => put("met1", r, Z.met1[0], Z.met1[1], { tone: "mid", path: sideOf(r), bevel: 0.4, say: sideOf(r) === "s" ? "metal1 source line (SL), along the column: the return path of the read current" : `metal1 pad under the ${col(r)} ReRAM (${dims(r)})` }));
G.rects.via1.forEach((r) => put("via1", r, Z.via1[0], RR[0], { tone: "mid", path: sideOf(r), say: `via1 plug, 0.15 µm square: metal1 pad to the ${col(r)} ReRAM's bottom electrode` }));
G.rects.reram.forEach((r) => put("reram", r, RR[0], RR[1], { tone: "hi", path: sideOf(r), bevel: 0.4, say: `${col(r)} ReRAM device, 0.26 µm square: TiN / HfO2 / Ti / TiN; set = low resistance, reset = high` }));
G.rects.met2.forEach((r) => put("met2", r, Z.met2[0], Z.met2[1], { tone: "mid", path: sideOf(r), bevel: 0.4, say: `metal2 bit line ${col(r)}, along the column: top electrode connection; carries the read current to its sense amplifier` }));

A.settle(R, P);
R.items.sort((a, b) => a.key - b.key);
A.auditOrExit(R, P);

// one engraved mark: the source line's name is not drawn; the card says which column is which
const halo = `<path class="iso-halo" d="${k.haloOf(CELL, SUB, SI - SUB, P)}"/>`;
const svg = k.figureSvg({
  width: W, height: H,
  label: "One 2T2R weight of the SKY130 array, drawn to scale from the layout with the insulating oxide removed: the silicon with two n+ transistor regions and a p+ tie strip, the polysilicon word line across both transistors, contacts and local interconnect, the metal1 source line in the middle and a metal1 pad under each ReRAM, the via1 plugs, the two ReRAM devices, and the two metal2 bit lines BL+ and BL- on top. The conductors that carry the read current of the low-resistance device are highlighted.",
  body: [halo, ...R.items.map((item) => item.svg)],
});

const STATES = [
  { w: "+1", p: true, n: false, text: "+1 · bits 1 0", long: "Weight +1: the BL+ device is set (low resistance), the BL− device reset. Only BL+ draws a read current above the reference, so the sense bits are 1 0." },
  { w: "0", p: false, n: false, text: "0 · bits 0 0", long: "Weight 0: both devices are reset (high resistance). Neither read current exceeds the reference, so the sense bits are 0 0." },
  { w: "−1", p: false, n: true, text: "−1 · bits 0 1", long: "Weight −1: the BL− device is set, the BL+ device reset. Only BL− draws a read current above the reference, so the sense bits are 0 1." },
];
const DATA = { sol: SOL, states: STATES, W, H, cell: [CELL.w, CELL.d], cellPlan: CELL, zr: [SUB, Z.met2[1]], siTop: SI, az: 38, el: 36 };
const live = readFileSync(join(HERE, "liveA.js"), "utf8").replace("__DATA__", JSON.stringify(DATA));

const fig = k.plateHtml({
  fig: "Fig A",
  title: "One weight, oxide removed",
  hint: "Drag to turn · click: weight",
  readout: STATES[0].text,
  keys: [
    { mark: "lit", label: "Conductors carrying the read current of the set (low-resistance) device" },
    { mark: "raised", label: "The two ReRAM devices, 0.26 µm square, under the metal2 bit lines" },
  ],
  caption: "Drawn to scale from the cell's layout (3.6 × 3.0 µm) and SkyWater's sky130B layer heights; only the insulating oxide is left out. Read current path, from front to back: bit line (metal2) → ReRAM → via1 plug → metal1 pad → mcon → local interconnect → contacts → n+ drain, under the polysilicon word line through the transistor channel → n+ source → contacts → shared local-interconnect strip → mcon → source line (metal1, middle). The near strip is the p+ tie that holds the silicon at ground. How the 0.565 µm via1 slot divides between plug and ReRAM stack is not published; the split drawn is the same as in the cross-sections. A set device conducts more than the read reference (about 12.4 µS), a reset device less, so the two sense bits give the trit.",
  body: `<div class="iso-stage" tabindex="0" role="slider" aria-label="2T2R cell in 3D: arrow keys turn it, Enter changes the weight" aria-valuemin="-1" aria-valuemax="1" aria-valuenow="1">${svg}</div>`,
});
const SWATCH = [["silicon", "silicon"], ["diff", "n+ silicon"], ["tap", "p+ silicon"], ["poly", "polysilicon"], ["licon", "licon"], ["li1", "li1 (TiN)"], ["mcon", "mcon"], ["met1", "metal1 (Al)"], ["via1", "via1"], ["reram", "ReRAM"], ["met2", "metal2 (Al)"]];
const LEG = `<span class="iso-mats">${SWATCH.map(([m, n]) => `<span data-mat="${m}"><i></i>${n}</span>`).join("")}</span>`;
const SAYCSS = `.iso-mats{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12.5px;color:var(--anatomy-text)}.iso-mats>span{display:inline-flex;align-items:center;gap:6px}.iso-mats i{width:11px;height:11px;border-radius:2px;background:var(--anatomy-top);box-shadow:inset 0 0 0 1px var(--anatomy-shade-0)}.iso-say{display:block;min-height:3.2em;margin:0 0 6px;font:12.5px/1.6 var(--anatomy-mono);color:var(--anatomy-strong)}`;
const fragX = `<div class="iso iso-embed" data-fig="cell2t2r"><style>${SAYCSS}[data-hov]>.iso-solid>.iso-edge{stroke:var(--anatomy-strong);stroke-width:1.4px}[data-fig=cell2t2r] .iso-stage{touch-action:pan-y;cursor:grab;user-select:none}[data-fig=cell2t2r] .iso-stage:active{cursor:grabbing}</style>${fig.replace('<figcaption class="iso-legend">', '<figcaption class="iso-legend"><span class="iso-say" aria-live="polite">Point at a part to see what it is.</span>' + LEG)}</div>`;
const frag = fragX;
writeFileSync(join(HERE, "figA.frag.json"), JSON.stringify({ html: frag, script: live }));
for (const theme of ["dark", "light"]) {
  writeFileSync(join(HERE, `figA-${theme}.html`), k.pageHtml({ title: "2T2R cell", theme, body: frag.replace('class="iso iso-embed"', 'class="iso-embed"'), script: kitScript() + live }));
}
console.log("items", R.items.length, "solids", R.solids.length);
