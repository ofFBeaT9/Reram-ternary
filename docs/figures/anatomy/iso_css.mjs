// The Anatomy kit's CSS, rethemed for the explainer page: light values by default, dark under the page's dark selectors.
import { writeFileSync } from "node:fs";
import { ISO_CSS } from "../ext_anatomy/anatomy/kit/iso-kit.mjs";
import { matCss } from "./mat_css.mjs";
const dark = ISO_CSS.match(/\.iso\{([^}]*)\}/)[1];
const light = ISO_CSS.match(/\.iso\[data-theme="light"\]\{([^}]*)\}/)[1];
let css = ISO_CSS.replace(/\.iso\{[^}]*\}/, `.iso{${dark}${light}}`).replace(/\.iso\[data-theme="light"\]\{[^}]*\}/, "");
css += `@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .iso{${dark}}}:root[data-theme="dark"] .iso{${dark}}`;
css += `.iso-embed{margin:22px 0}.iso-embed .iso-figure{margin:0}.iso-embed .iso-stage:focus{outline:none}.iso-embed .iso-solid[data-lit]>.iso-edge{stroke-width:1.4px}.iso-embed .iso-stage:focus-visible{outline:2px solid var(--anatomy-strong);outline-offset:4px}`;
css += matCss();
writeFileSync(new URL("./iso_page.css", import.meta.url), css);
console.log(css.length);
