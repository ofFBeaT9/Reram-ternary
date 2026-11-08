{
const root = document.querySelector('[data-fig="cell2t2r"]');
const stage = root.querySelector('.iso-stage');
const svg = stage.querySelector('svg');
const readout = root.querySelector('[data-readout]');
const line = root.querySelector('.iso-say');
const D = __DATA__;
const SOL = D.sol, STATES = D.states, W = D.W, H = D.H;
const still = matchMedia('(prefers-reduced-motion: reduce)');
const R2D = Math.PI / 180;
const box = (s) => ({ lo: [s.p[0], s.p[1], s.z[0]], hi: [s.p[0] + s.p[2], s.p[1] + s.p[3], s.z[1]] });
const B = SOL.map(box);
const ALL = []; for (const x of [0, D.cell[0]]) for (const y of [0, D.cell[1]]) for (const z of D.zr) ALL.push([x, y, z]);
const CEN = [D.cell[0] / 2, D.cell[1] / 2, (D.zr[0] + D.zr[1]) / 2];
// one scale per elevation (the smallest over all azimuths, and never larger than at lower elevations), so turning never zooms
const KEL = [];
for (let e = 8; e <= 88; e += 2) { let m = Infinity; for (let a = 0; a < 360; a += 6) m = Math.min(m, fitProjection(ALL, W, H, { pad: 14, azimuth: a, elevation: e }).scale); KEL.push(m); }
for (let i = 1; i < KEL.length; i++) KEL[i] = Math.min(KEL[i], KEL[i - 1]);
const kAt = (e) => { const f = (Math.max(8, Math.min(88, e)) - 8) / 2, i = Math.min(KEL.length - 2, Math.floor(f)); return KEL[i] + (KEL[i + 1] - KEL[i]) * (f - i); };
function projAt(az, el) { const KMIN = kAt(el); const P0 = { origin: [0, 0], scale: KMIN, azimuth: az, elevation: el }; const c = iso(CEN, P0); return { origin: [W / 2 - c[0], H / 2 - c[1]], scale: KMIN, azimuth: az, elevation: el }; }
function hull(pts) {
  pts = pts.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cr = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lo = [], up = [];
  for (const p of pts) { while (lo.length >= 2 && cr(lo[lo.length - 2], lo[lo.length - 1], p) <= 0) lo.pop(); lo.push(p); }
  for (let i = pts.length - 1; i >= 0; i--) { const p = pts[i]; while (up.length >= 2 && cr(up[up.length - 2], up[up.length - 1], p) <= 0) up.pop(); up.push(p); }
  up.pop(); lo.pop(); return lo.concat(up);
}
function clip(subject, clipper) {   // convex polygons, both counter-clockwise in screen coordinates
  let out = subject;
  for (let i = 0; i < clipper.length && out.length; i++) {
    const a = clipper[i], b = clipper[(i + 1) % clipper.length], inp = out; out = [];
    const side = (p) => (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]);
    for (let j = 0; j < inp.length; j++) {
      const p = inp[j], q = inp[(j + 1) % inp.length], sp = side(p), sq = side(q);
      if (sp >= 0) out.push(p);
      if ((sp >= 0) !== (sq >= 0)) { const t = sp / (sp - sq); out.push([p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]); }
    }
  }
  return out;
}
function area(poly) { let a = 0; for (let i = 0; i < poly.length; i++) { const p = poly[i], q = poly[(i + 1) % poly.length]; a += p[0] * q[1] - q[0] * p[1]; } return a / 2; }
function order(P) {
  const { sinA, cosA, sinE, cosE, k } = cameraOf(P);
  const r = [sinA, -cosA, 0], d = [cosA * sinE, sinA * sinE, -cosE], v = [cosA * cosE, sinA * cosE, sinE];
  const hulls = B.map((b) => { const pts = []; for (const x of [b.lo[0], b.hi[0]]) for (const y of [b.lo[1], b.hi[1]]) for (const z of [b.lo[2], b.hi[2]]) pts.push(iso([x, y, z], P)); return hull(pts); });
  const ext = hulls.map((h) => [Math.min(...h.map((p) => p[0])), Math.min(...h.map((p) => p[1])), Math.max(...h.map((p) => p[0])), Math.max(...h.map((p) => p[1]))]);
  const front = (b, sx, sy) => {   // depth of the nearest face of box b along the camera ray through (sx, sy)
    const u = (sx - P.origin[0]) / k, w = (sy - P.origin[1]) / k; let t0 = -Infinity, t1 = Infinity;
    for (let i = 0; i < 3; i++) {
      const p0 = u * r[i] + w * d[i];
      if (Math.abs(v[i]) < 1e-9) { if (p0 < b.lo[i] - 1e-6 || p0 > b.hi[i] + 1e-6) return null; continue; }
      let a = (b.lo[i] - p0) / v[i], c = (b.hi[i] - p0) / v[i]; if (a > c) [a, c] = [c, a];
      t0 = Math.max(t0, a); t1 = Math.min(t1, c);
    }
    return t0 <= t1 + 1e-6 ? t1 : null;
  };
  const n = B.length, after = Array.from({ length: n }, () => []), indeg = new Array(n).fill(0);
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
    const a = ext[i], b = ext[j];
    if (a[2] <= b[0] || b[2] <= a[0] || a[3] <= b[1] || b[3] <= a[1]) continue;
    const ov = clip(hulls[i], hulls[j]); if (ov.length < 3 || Math.abs(area(ov)) < 0.3) continue;
    const cx = ov.reduce((s, p) => s + p[0], 0) / ov.length, cy = ov.reduce((s, p) => s + p[1], 0) / ov.length;
    const ti = front(B[i], cx, cy), tj = front(B[j], cx, cy); if (ti === null || tj === null || Math.abs(ti - tj) < 1e-6) continue;
    const [back, fwd] = ti < tj ? [i, j] : [j, i]; after[back].push(fwd); indeg[fwd]++;
  }
  const depth = B.map((b) => ((b.lo[0] + b.hi[0]) / 2) * v[0] + ((b.lo[1] + b.hi[1]) / 2) * v[1] + ((b.lo[2] + b.hi[2]) / 2) * v[2]);
  const ready = [], out = [], done = new Array(n).fill(false);
  for (let i = 0; i < n; i++) if (!indeg[i]) ready.push(i);
  while (out.length < n) {
    if (!ready.length) { let m = -1; for (let i = 0; i < n; i++) if (!done[i] && (m < 0 || depth[i] < depth[m])) m = i; ready.push(m); indeg[m] = 0; }   // a cycle: break it at the farthest box
    ready.sort((a, b) => depth[b] - depth[a]); const i = ready.pop(); if (done[i]) continue; done[i] = true; out.push(i);
    for (const j of after[i]) if (!done[j] && --indeg[j] === 0) ready.push(j);
  }
  return out;
}
let az = D.az, el = D.el, at = 0, hovI = -1, naming = false;
function lit(s) { const st = STATES[at]; return s.path === 'p' ? st.p : s.path === 'n' ? st.n : s.path === 's' ? st.p || st.n : false; }
function render() {
  const P = projAt(az, el), ord = order(P);
  let html = '<path class="iso-halo" d="' + haloOf(D.cellPlan, D.zr[0], D.siTop - D.zr[0], P) + '"/>';
  for (const i of ord) {
    const s = SOL[i];
    const plan = { x: s.p[0], y: s.p[1], w: s.p[2], d: s.p[3], r: 0 };
    html += '<g data-i="' + i + '" data-mat="' + s.mat + '"' + (i === hovI ? ' data-hov=""' : '') + '>' + solidSvg(slabOf(plan, s.z[0], s.z[1] - s.z[0], P, 2, s.bevel), { tone: s.tone, lit: lit(s) }) + '</g>';
  }
  svg.innerHTML = html;
  stage.setAttribute('aria-valuetext', STATES[at].text + ', seen from ' + Math.round(((az % 360) + 360) % 360) + ' degrees around and ' + Math.round(el) + ' degrees up');
}
function show(i) { at = (i + 3) % 3; readout.textContent = STATES[at].text; if (!naming) line.textContent = STATES[at].long; render(); }
let visible = false, touring = !still.matches, frame = 0, last = 0, clock = 0, idle = 0, nextFlip = 2.6, baseAz = D.az;
function tick(now) {
  const dt = last ? Math.min((now - last) / 1000, 1 / 20) : 1 / 60; last = now;
  if (touring) { clock += dt; az = baseAz + 28 * Math.sin(clock * 0.35); if (clock > nextFlip) { nextFlip += 2.6; show(at + 1); } else render(); }
  frame = visible && touring ? requestAnimationFrame(tick) : 0;
}
const run = () => { if (!frame && visible && touring) { last = 0; frame = requestAnimationFrame(tick); } };
const pause = () => { touring = false; clearTimeout(idle); idle = setTimeout(() => { if (!still.matches) { touring = true; clock = 0; nextFlip = 2.6; baseAz = az; run(); } }, 8000); };
new IntersectionObserver((e) => { visible = e[e.length - 1].isIntersecting; run(); }, { rootMargin: '80px 0px' }).observe(stage);
let down = null, dragged = false;
stage.addEventListener('pointerdown', (e) => { down = [e.clientX, e.clientY, az, el]; dragged = false; pause(); });
stage.addEventListener('pointermove', (e) => {
  if (down && (e.buttons & 1 || e.pointerType !== 'mouse')) {
    const dx = e.clientX - down[0], dy = e.clientY - down[1];
    if (!dragged && Math.hypot(dx, dy) > 5) { dragged = true; try { stage.setPointerCapture(e.pointerId); } catch (_) {} }
    if (dragged) { const sc = 600 / stage.getBoundingClientRect().width; az = down[2] - dx * 0.45 * sc; el = Math.max(8, Math.min(88, down[3] + dy * 0.35 * sc)); hovI = -1; render(); return; }
  }
  const g = e.target.closest('[data-i]'); const i = g ? +g.getAttribute('data-i') : -1;
  if (i !== hovI) {
    const old = svg.querySelector('[data-hov]'); if (old) old.removeAttribute('data-hov');
    hovI = i; if (g) { g.setAttribute('data-hov', ''); naming = true; line.textContent = SOL[i].say; pause(); } else { naming = false; line.textContent = STATES[at].long; }
  }
});
const up = (e) => { if (down && !dragged && e.type === 'pointerup') show(at + 1); down = null; dragged = false; };
stage.addEventListener('pointerup', up); stage.addEventListener('pointercancel', up);
stage.addEventListener('pointerleave', () => { if (down) return; const old = svg.querySelector('[data-hov]'); if (old) old.removeAttribute('data-hov'); hovI = -1; naming = false; line.textContent = STATES[at].long; });
stage.addEventListener('dblclick', () => { az = D.az; el = D.el; render(); });
stage.addEventListener('keydown', (e) => {
  let used = true;
  if (e.key === 'ArrowLeft') az += 10; else if (e.key === 'ArrowRight') az -= 10;
  else if (e.key === 'ArrowUp') el = Math.min(88, el + 8); else if (e.key === 'ArrowDown') el = Math.max(8, el - 8);
  else if (e.key === 'Enter' || e.key === ' ') { show(at + 1); }
  else if (e.key === '+' || e.key === '1') show(0); else if (e.key === '0') show(1); else if (e.key === '-') show(2);
  else if (e.key === 'Home') { az = D.az; el = D.el; } else used = false;
  if (!used) return; e.preventDefault(); pause(); render();
});
show(0);
}
