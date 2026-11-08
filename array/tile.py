"""Electrical model of one 2T2R ternary tile (default 72 rows x 24 ternary columns).

Per column pair and row there are three nodes: BL+, BL- and the shared source line SL.
  cell (r, c): conductance Gp between BL+ and SL, Gn between BL- and SL, switched by the row select
  bit lines and source line are resistive ladders along the rows
  each bit line is held at v_read by a clamp with input resistance r_clamp and an offset voltage
  the source line is grounded at the same end as the clamps (worst case) or at both ends
The solver is exact for this linear network (banded nodal analysis).

Device statistics are the published IHP 4-kbit array values (uA at 0.2 V, 1T1R path, Gaussian fits):
Perez et al., Electronics 10, 1084 (2021), Table 2, optimized scheme.
"""
from dataclasses import dataclass, field
import numpy as np
from scipy.linalg import solve_banded

IHP_STATS = {"HRS": (2.85, 1.85), "LRS1": (18.08, 1.96), "LRS2": (31.01, 1.60), "LRS3": (43.59, 1.55)}   # (mean, sigma) uA
RSHEET = {"M2-5": 0.088, "TM1": 0.018, "M1": 0.110}                                                        # ohm/sq (IHP spec targets)


@dataclass
class TileConfig:
    rows: int = 72
    cols: int = 24
    lrs: str = "LRS3"
    v_read: float = 0.2
    bl_metal: str = "TM1"
    bl_width_um: float = 1.64
    sl_metal: str = "M2-5"
    sl_width_um: float = 1.0
    row_pitch_um: float = 2.0          # ASSUMPTION until the foundry cell is known
    both_ends: bool = False            # clamp / ground the lines at both ends
    r_clamp: float = 1.0               # ohm, input resistance of the bit-line clamp (see exp_analog_error.py)
    sigma_vos: float = 0.0             # V, clamp offset (per bit line)
    sigma_gain: float = 0.0            # relative gain error of each bit-line current path
    spread_scale: float = 1.0          # multiplies the published sigmas (relaxation, new layout)
    read_noise: float = 0.0            # relative temporal noise per device per read
    hrs_floor_uA: float = 0.05         # lower truncation of the HRS distribution


class Tile:
    def __init__(self, cfg: TileConfig, rng=None):
        self.cfg = cfg
        self.rng = rng or np.random.default_rng(0)
        c = cfg
        self.g_bl = 1.0 / (RSHEET[c.bl_metal] * c.row_pitch_um / c.bl_width_um)
        self.g_sl = 1.0 / (RSHEET[c.sl_metal] * c.row_pitch_um / c.sl_width_um)
        self.g_end = 1.0 / (1.0 / self.g_bl + c.r_clamp)
        self.W = np.zeros((c.rows, c.cols), dtype=int)
        self.Gp = np.zeros((c.rows, c.cols)); self.Gn = np.zeros((c.rows, c.cols))
        self.vos = self.rng.normal(0, c.sigma_vos, (2, c.cols)) if c.sigma_vos > 0 else np.zeros((2, c.cols))
        self.gain = 1 + (self.rng.normal(0, c.sigma_gain, (2, c.cols)) if c.sigma_gain > 0 else np.zeros((2, c.cols)))

    # ------------------------------------------------------------------ programming
    def _sample(self, state, shape):
        mu, sg = IHP_STATS[state]
        i = self.rng.normal(mu, sg * self.cfg.spread_scale, shape)
        i = np.maximum(i, self.cfg.hrs_floor_uA)
        return i * 1e-6 / 0.2                       # siemens; statistics were taken at 0.2 V

    def program(self, W):
        W = np.asarray(W, dtype=int)
        assert W.shape == (self.cfg.rows, self.cfg.cols) and np.isin(W, (-1, 0, 1)).all()
        self.W = W
        hi = self._sample(self.cfg.lrs, W.shape); lo1 = self._sample("HRS", W.shape); lo2 = self._sample("HRS", W.shape)
        self.Gp = np.where(W == 1, hi, lo1)
        self.Gn = np.where(W == -1, hi, lo2)

    def ideal_step(self):
        return (IHP_STATS[self.cfg.lrs][0] - IHP_STATS["HRS"][0]) * 1e-6 * self.cfg.v_read / 0.2

    # ------------------------------------------------------------------ analog read of a set of rows
    def read_currents(self, active):
        """active: boolean vector over rows. Returns (Ip, In) per column in amperes, as seen by the converters."""
        c = self.cfg; R, C = c.rows, c.cols
        act = np.asarray(active, dtype=float)[:, None]
        Gp = self.Gp * act; Gn = self.Gn * act
        if c.read_noise > 0:
            Gp = Gp * (1 + self.rng.normal(0, c.read_noise, Gp.shape)); Gn = Gn * (1 + self.rng.normal(0, c.read_noise, Gn.shape))
        n = 3 * R
        ab = np.zeros((7, C, n)); rhs = np.zeros((C, n))
        # diagonal index 3 ; ab[3 + i - j, j] = A[i, j]
        iP = np.arange(R) * 3; iN = iP + 1; iS = iP + 2
        gb, gs, ge = self.g_bl, self.g_sl, self.g_end
        dP = Gp.T.copy(); dN = Gn.T.copy(); dS = (Gp + Gn).T.copy()          # (C, R)
        nb = np.full(R, 2.0); nb[0] = 1.0; nb[-1] = 1.0                       # neighbours inside the ladder
        dP += gb * nb; dN += gb * nb; dS += gs * nb
        dP[:, 0] += ge; dN[:, 0] += ge; dS[:, 0] += gs                         # ends at row 0
        rhs[:, iP[0]] = ge * (c.v_read + self.vos[0]); rhs[:, iN[0]] = ge * (c.v_read + self.vos[1])
        if c.both_ends:
            dP[:, -1] += ge; dN[:, -1] += ge; dS[:, -1] += gs
            rhs[:, iP[-1]] = ge * (c.v_read + self.vos[0]); rhs[:, iN[-1]] = ge * (c.v_read + self.vos[1])
        ab[3][:, iP] = dP; ab[3][:, iN] = dN; ab[3][:, iS] = dS
        # couplings: P_i - S_i (offset 2), N_i - S_i (offset 1), ladder neighbours (offset 3)
        ab[1][:, iS] = -Gp.T; ab[5][:, iP] = -Gp.T          # A[P,S] at ab[3+P-S=1, S]; A[S,P] at ab[3+2=5, P]
        ab[2][:, iS] = -Gn.T; ab[4][:, iN] = -Gn.T
        for idx, g in ((iP, gb), (iN, gb), (iS, gs)):
            ab[0][:, idx[1:]] = -g                            # A[i, i+3] stored at column i+3
            ab[6][:, idx[:-1]] = -g                           # A[i+3, i] stored at column i
        abf = ab.reshape(7, C * n); bf = rhs.reshape(C * n)
        # columns are independent; clear band entries that would couple the last nodes of one column to the next
        for k in range(1, C):
            s = k * n
            for off in (1, 2, 3):
                abf[3 - off, s:s + off] = 0.0                # upper band entries of the first nodes
                abf[3 + off, s - off:s] = 0.0                # lower band entries of the last nodes
        v = solve_banded((3, 3), abf, bf).reshape(C, n)
        Ip = ge * (c.v_read + self.vos[0] - v[:, iP[0]]); In = ge * (c.v_read + self.vos[1] - v[:, iN[0]])
        if c.both_ends:
            Ip += ge * (c.v_read + self.vos[0] - v[:, iP[-1]]); In += ge * (c.v_read + self.vos[1] - v[:, iN[-1]])
        self._last_power = c.v_read * (Ip.sum() + In.sum())
        return Ip * self.gain[0], In * self.gain[1]

    # ------------------------------------------------------------------ products
    def exact(self, x):
        return np.asarray(x, dtype=int) @ self.W

    def analog_raw(self, x, rows_per_read=None):
        """Two-phase analog evaluation. Returns the un-rounded result in amperes per column and the array energy factor (W*reads)."""
        x = np.asarray(x, dtype=int); R = self.cfg.rows
        blocks = [np.arange(R)] if not rows_per_read else [np.arange(s, min(s + rows_per_read, R)) for s in range(0, R, rows_per_read)]
        total = np.zeros(self.cfg.cols); power_time = 0.0; reads = 0
        for b in blocks:
            for sign in (+1, -1):
                act = np.zeros(R, dtype=bool); act[b] = (x[b] == sign)
                if not act.any():
                    continue
                Ip, In = self.read_currents(act)
                total += sign * (Ip - In); power_time += self._last_power; reads += 1
        return total, power_time, reads

    def analog(self, x, step=None, gain=None, offset=None, rows_per_read=None):
        raw, pt, reads = self.analog_raw(x, rows_per_read)
        step = self.ideal_step() if step is None else step
        y = raw / step
        if gain is not None:
            y = (y - offset) / gain
        return np.rint(y).astype(int), y, pt, reads

    def calibrate(self, n_vectors=64, rows_per_read=None, density=0.67):
        """Per-column gain and offset from random ternary test vectors (weights are known to the system)."""
        R = self.cfg.rows; ys = []; ts = []
        for _ in range(n_vectors):
            x = self.rng.choice((-1, 0, 1), size=R, p=((density / 2), 1 - density, density / 2))
            raw, _, _ = self.analog_raw(x, rows_per_read)
            ys.append(raw / self.ideal_step()); ts.append(self.exact(x))
        ys = np.array(ys); ts = np.array(ts, dtype=float)
        gain = np.ones(self.cfg.cols); off = np.zeros(self.cfg.cols)
        for c in range(self.cfg.cols):
            A = np.vstack([ts[:, c], np.ones(len(ts))]).T
            sol, *_ = np.linalg.lstsq(A, ys[:, c], rcond=None)
            gain[c], off[c] = (sol[0] if abs(sol[0]) > 0.2 else 1.0), sol[1]
        return gain, off

    # ------------------------------------------------------------------ digital mode
    def digital_read_row(self, r, i_ref):
        """Read one row: each device compared with i_ref. Returns the recovered weights and the array power."""
        act = np.zeros(self.cfg.rows, dtype=bool); act[r] = True
        Ip, In = self.read_currents(act)
        bp = Ip > i_ref; bn = In > i_ref
        w = bp.astype(int) - bn.astype(int)
        return w, self._last_power

    def hybrid_read_row(self, r, i_ref):
        """Hybrid read of one row (proposal, 9 October 2026): zero when neither device exceeds i_ref,
        otherwise the sign of Ip - In (the two devices of the pair compared with each other)."""
        act = np.zeros(self.cfg.rows, dtype=bool); act[r] = True
        Ip, In = self.read_currents(act)
        nz = np.maximum(Ip, In) > i_ref
        w = np.where(nz, np.where(Ip > In, 1, -1), 0)
        return w, self._last_power

    def digital(self, x, i_ref):
        """Row-by-row product. Without temporal read noise a row read does not depend on the input,
        so the row results are computed once per programmed tile and reused."""
        x = np.asarray(x, dtype=int)
        if self.cfg.read_noise > 0:
            y = np.zeros(self.cfg.cols, dtype=int); pt = 0.0; reads = 0
            for r in np.nonzero(x)[0]:
                w, p = self.digital_read_row(r, i_ref)
                y += x[r] * w; pt += p; reads += 1
            return y, pt, reads
        key = (id(self.Gp), float(i_ref))
        if getattr(self, "_dig_key", None) != key:
            rows = [self.digital_read_row(r, i_ref) for r in range(self.cfg.rows)]
            self._dig_w = np.array([w for w, _ in rows]); self._dig_p = np.array([p for _, p in rows]); self._dig_key = key
        nz = x != 0
        return x @ self._dig_w, float(self._dig_p[nz].sum()), int(nz.sum())


def reference_current(lrs="LRS3", scale=1.0):
    """Equal-z threshold between HRS and the chosen LRS (amperes at 0.2 V)."""
    (m0, s0), (m1, s1) = IHP_STATS["HRS"], IHP_STATS[lrs]
    return (m0 + (m1 - m0) * s0 / (s0 + s1)) * 1e-6
