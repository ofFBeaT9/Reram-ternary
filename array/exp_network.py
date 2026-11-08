"""E4: a small all-ternary network (ternary inputs, weights and activations) on the 8x8 digits set,
run through the tile model. Layer 1: 72 -> 72 (three 72 x 24 tiles). Layer 2: 72 -> 10 (one tile).
Integer arithmetic only at inference: y = x.W ; hidden = QNT(y, theta) ; class = argmax(hidden.W2).
This is the REBEL-6 kernel shape (TMAC.T for the dot products, QNT.T for the activation)."""
import sys, json, time
import numpy as np
from sklearn.datasets import load_digits
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from tile import *

def tern(w, d): return (w > d).astype(int) - (w < -d).astype(int)

def load():
    d = load_digits(); X = d.data; y = d.target
    Xt = np.zeros((len(X), 72), dtype=int)
    Xt[:, :64] = (X >= 9).astype(int) - (X <= 1).astype(int)       # bright -> +1, dark -> -1, middle -> 0
    Xt[:, 64] = 1                                                   # constant row (bias)
    rng = np.random.default_rng(0); idx = rng.permutation(len(X)); n = int(0.8 * len(X))
    return Xt[idx[:n]], y[idx[:n]], Xt[idx[n:]], y[idx[n:]]

def train(Xtr, ytr, H=72, epochs=250, seed=1, theta=4, dthr=0.33):
    rng = np.random.default_rng(seed)
    W1 = rng.uniform(-1, 1, (72, H)); W2 = rng.uniform(-1, 1, (H, 10))
    m = [np.zeros_like(W1), np.zeros_like(W2)]; v = [np.zeros_like(W1), np.zeros_like(W2)]
    lr = 0.01; b1, b2, eps = 0.9, 0.999, 1e-8; t = 0; Y = np.eye(10)[ytr]
    for ep in range(epochs):
        perm = rng.permutation(len(Xtr))
        for s in range(0, len(Xtr), 64):
            xb = Xtr[perm[s:s + 64]]; yb = Y[perm[s:s + 64]]
            T1, T2 = tern(W1, dthr), tern(W2, dthr)
            z1 = xb @ T1; h = tern(z1, theta); h[:, 0] = 1            # hidden unit 0 is a constant (bias for layer 2)
            z2 = h @ T2; logit = z2 / 4.0
            p = np.exp(logit - logit.max(1, keepdims=True)); p /= p.sum(1, keepdims=True)
            dz2 = (p - yb) / len(xb) / 4.0
            g2 = h.T @ dz2
            dh = dz2 @ T2.T
            dz1 = dh * (np.abs(z1) <= 3 * theta) / (2.0 * theta)       # straight-through estimate of the ternary activation
            dz1[:, 0] = 0
            g1 = xb.T @ dz1
            t += 1
            for k, (W, g) in enumerate(((W1, g1), (W2, g2))):
                m[k] = b1 * m[k] + (1 - b1) * g; v[k] = b2 * v[k] + (1 - b2) * g * g
                W -= lr * (m[k] / (1 - b1 ** t)) / (np.sqrt(v[k] / (1 - b2 ** t)) + eps)
                np.clip(W, -1, 1, out=W)
    return tern(W1, dthr), tern(W2, dthr), theta

def infer_exact(X, T1, T2, theta):
    h = tern(X @ T1, theta); h[:, 0] = 1
    return (h @ T2).argmax(1), X @ T1, h

class Hardware:
    """Layer 1 on three tiles, layer 2 on one tile."""
    def __init__(self, T1, T2, cfg_kw, seed=5):
        rng = np.random.default_rng(seed)
        self.t1 = []
        for k in range(3):
            t = Tile(TileConfig(**cfg_kw), rng); t.program(T1[:, 24 * k:24 * (k + 1)]); self.t1.append(t)
        W2 = np.zeros((72, 24), dtype=int); W2[:, :10] = T2
        self.t2 = Tile(TileConfig(**cfg_kw), rng); self.t2.program(W2)
        self.cal = None
    def calibrate(self, n=48):
        self.cal = [t.calibrate(n) for t in self.t1 + [self.t2]]
    def run(self, X, theta, mode, iref=None, use_cal=True):
        pred = []; pt = 0.0; reads = 0; mism = 0; tot = 0
        for x in X:
            ys = []
            for k, t in enumerate(self.t1):
                if mode == "digital":
                    y, p, r = t.digital(x, iref)
                else:
                    g, o = (self.cal[k] if (self.cal and use_cal) else (None, None))
                    y, _, p, r = t.analog(x, gain=g, offset=o)
                ys.append(y); pt += p; reads += r
            z1 = np.concatenate(ys); mism += int((z1 != x @ np.hstack([t.W for t in self.t1])).sum()); tot += z1.size
            h = tern(z1, theta); h[0] = 1
            if mode == "digital":
                y2, p, r = self.t2.digital(h, iref)
            else:
                g, o = (self.cal[3] if (self.cal and use_cal) else (None, None))
                y2, _, p, r = self.t2.analog(h, gain=g, offset=o)
            pt += p; reads += r
            pred.append(int(np.argmax(y2[:10])))
        return np.array(pred), pt / len(X), reads / len(X), mism / tot

if __name__ == "__main__":
    Xtr, ytr, Xte, yte = load()
    t0 = time.time(); T1, T2, theta = train(Xtr, ytr)
    p_tr, _, _ = infer_exact(Xtr, T1, T2, theta); p_te, z1, h = infer_exact(Xte, T1, T2, theta)
    out = {"train_acc": float((p_tr == ytr).mean()), "test_acc_software": float((p_te == yte).mean()),
           "nonzero_w1": float((T1 != 0).mean()), "nonzero_w2": float((T2 != 0).mean()), "nonzero_inputs": float((Xte != 0).mean()),
           "nonzero_hidden": float((h != 0).mean()), "n_test": int(len(yte))}
    print(f"trained in {time.time()-t0:.0f} s: train {out['train_acc']*100:.1f} %, test {out['test_acc_software']*100:.1f} % ({len(yte)} samples); non-zero weights {out['nonzero_w1']*100:.0f} % / {out['nonzero_w2']*100:.0f} %, inputs {out['nonzero_inputs']*100:.0f} %, hidden {out['nonzero_hidden']*100:.0f} %")
    np.savez(__file__.rsplit('/', 2)[0] + "/results/ternary_digits_weights.npz", T1=T1, T2=T2, theta=theta)
    best = dict(bl_metal="TM1", bl_width_um=1.64, sl_metal="TM1", sl_width_um=1.64, both_ends=True, r_clamp=1.0)
    poor = dict(bl_metal="M2-5", bl_width_um=0.4, sl_metal="M2-5", sl_width_um=1.0, both_ends=False, r_clamp=50.0)
    cases = [
        ("digital, LRS3, published spread, poor wiring", "digital", dict(lrs="LRS3", **poor), True),
        ("digital, LRS3, spread x2, poor wiring", "digital", dict(lrs="LRS3", spread_scale=2.0, **poor), True),
        ("analog, LRS3, published spread, best wiring, calibrated", "analog", dict(lrs="LRS3", **best), True),
        ("analog, LRS3, spread x2, best wiring, calibrated", "analog", dict(lrs="LRS3", spread_scale=2.0, **best), True),
        ("analog, LRS3, spread x3, best wiring, calibrated", "analog", dict(lrs="LRS3", spread_scale=3.0, **best), True),
        ("analog, LRS1, published spread, best wiring, calibrated", "analog", dict(lrs="LRS1", **best), True),
        ("analog, LRS3, published spread, poor wiring, calibrated", "analog", dict(lrs="LRS3", **poor), True),
        ("analog, LRS3, published spread, poor wiring, not calibrated", "analog", dict(lrs="LRS3", **poor), False),
    ]
    out["hardware"] = {}
    for name, mode, kw, cal in cases:
        accs = []; mm = []; ptm = []; rd = []
        for seed in range(3):
            hw = Hardware(T1, T2, kw, seed=seed)
            if mode == "analog" and cal: hw.calibrate()
            pred, pt, reads, mism = hw.run(Xte, theta, mode, iref=reference_current(kw["lrs"]), use_cal=cal)
            accs.append(float((pred == yte).mean())); mm.append(mism); ptm.append(pt); rd.append(reads)
        out["hardware"][name] = dict(acc_mean=float(np.mean(accs)), acc_min=float(np.min(accs)), acc_max=float(np.max(accs)),
                                     layer1_result_mismatch=float(np.mean(mm)), array_power_x_reads_W=float(np.mean(ptm)), reads_per_inference=float(np.mean(rd)))
        print(f"{name}: accuracy {np.mean(accs)*100:.1f} % (min {np.min(accs)*100:.1f}, max {np.max(accs)*100:.1f}); layer-1 results differing from exact {np.mean(mm)*100:.2f} %; reads per inference {np.mean(rd):.0f}; sum of read powers {np.mean(ptm)*1e3:.2f} mW", flush=True)
    json.dump(out, open(__file__.rsplit('/', 2)[0] + "/results/array_network.json", "w"), indent=1)
