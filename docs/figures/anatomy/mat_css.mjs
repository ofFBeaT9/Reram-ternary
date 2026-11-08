// Material colours for Figs A and B: the same layer colours as the page's top view and cross-sections (layers.py),
// shaded into the kit's five face tones. Dark theme: the near-black contact colours are lightened so they stay visible.
const MAT = {
  silicon: ["#c9c3b6", "#8f8a80"], diff: ["#4aa04a", "#4aa04a"], tap: ["#7fbf7f", "#6fae6f"], poly: ["#c83232", "#d24a4a"],
  licon: ["#5a3a1a", "#9a6a3a"], li1: ["#8c6ec8", "#9a80d4"], mcon: ["#2a2a2a", "#8a8a8a"], met1: ["#2f6edc", "#4a84e6"],
  via1: ["#111111", "#a8a8a8"], reram: ["#f2b705", "#f2b705"], met2: ["#d246be", "#d860c6"],
  // Fig B (nanometre view): colours of the page's nanometre figure
  tin: ["#7c8a99", "#8d9aa8"], hfo2: ["#f6dc8a", "#e8c860"], ti: ["#b9a27a", "#b9a27a"],
};
const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const mix = (a, b, t) => "#" + hex(a).map((v, i) => Math.round(v + (hex(b)[i] - v) * t).toString(16).padStart(2, "0")).join("");
const vars = (c, dark) => {
  const W = "#ffffff", K = "#000000";
  const t = dark
    ? { top: mix(c, K, 0.05), s3: mix(c, K, 0.18), s2: mix(c, K, 0.3), s1: mix(c, K, 0.42), s0: mix(c, K, 0.52), litTop: mix(c, W, 0.35), litShade: mix(c, W, 0.15) }
    : { top: mix(c, W, 0.3), s3: mix(c, W, 0.1), s2: c, s1: mix(c, K, 0.12), s0: mix(c, K, 0.24), litTop: mix(c, W, 0.6), litShade: mix(c, W, 0.35) };
  return `--anatomy-paper:${c};--anatomy-face:${c};--anatomy-top:${t.top};--anatomy-shade-3:${t.s3};--anatomy-shade-2:${t.s2};--anatomy-shade-1:${t.s1};--anatomy-shade-0:${t.s0};--anatomy-lit-top:${t.litTop};--anatomy-lit-shade:${t.litShade}`;
};
export function matCss() {
  const light = Object.entries(MAT).map(([m, [c]]) => `.iso [data-mat="${m}"]{${vars(c, false)}}`).join("");
  const dark = Object.entries(MAT).map(([m, [, c]]) => `.iso [data-mat="${m}"]{${vars(c, true)}}`).join("");
  return light + `@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) ${dark.replace(/\}\.iso/g, "}:root:not([data-theme=\"light\"]) .iso")}}` + `:root[data-theme="dark"] ${dark.replace(/\}\.iso/g, "}:root[data-theme=\"dark\"] .iso")}`;
}
export const COLORS = MAT;
