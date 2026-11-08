# Figs A and B of docs/TCIM0_explainer.html

Isometric figures drawn with the Anatomy kit (github.com/wheresryan22/anatomy, MIT, commit e6600ff), from this
design's own data: `cell_json.py` writes `cell.json` from the rr2t2r cell of layout/sky130/tcim_sky130_array.gds and
the sky130B Magic heights; `figA.mjs` (one 2T2R cell, oxide removed) and `figB.mjs` (one ReRAM device cut through its
filament, SkyWater's model constants) import the kit from `../ext_anatomy/anatomy` (clone it there to rebuild);
`node figA.mjs --audit` runs the kit's geometry audit (passed: 38 and 6 solids, 0 problems). `iso_css.mjs` rethemes the
kit's CSS for the page. `liveA.js` is the in-page renderer that lets Fig A turn: it rebuilds the solids with the kit for each view and orders them by casting a ray through each on-screen overlap.
