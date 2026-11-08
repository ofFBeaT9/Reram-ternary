"""Reference implementation of the Stanford-PKU ReRAM compact model with the IHP
multi-level extension (gap floor set by the select-transistor gate voltage).

Equations (Jiang et al. 2016; Perez-Bosch Quesada et al., Electronics 10, 645 (2021)):
    I      = I0 * exp(-g/g0) * sinh(V/V0)
    dg/dt  = -v0 * exp(-Ea/kT) * sinh(gamma * a0 * V / (tox * kT/q))
    gamma  = gamma0 - beta * (g / 1 nm)**alpha
    T      = T0 + |V*I| * Rth                       (static thermal model)
    g_min  = Kth * (W/L) / Vgate + C,   g <= g_max
V is the voltage from top to bottom electrode; V > 0 closes the gap (SET).

Parameter sets
    IHP_PUBLISHED   Table 3 of the 2021 paper, as printed.
    IHP_CALIBRATED  same static parameters; switching kinetics re-fitted in this project
                    (see model/calibrate.py and results/device_model.json).
"""
from dataclasses import dataclass, replace
import math
import numpy as np

KB_EV = 8.617333262e-5      # eV/K


@dataclass(frozen=True)
class ReRAMParams:
    I0: float = 854e-6       # A
    g0: float = 0.28e-9      # m
    V0: float = 0.35         # V
    v0: float = 0.4          # m/s
    Ea: float = 0.6          # eV
    a0: float = 0.25e-9      # m
    tox: float = 6e-9        # m
    gamma0: float = 20.0
    beta: float = 0.4
    alpha: float = 3.0
    Rth: float = 1500.0      # K/W
    T0: float = 300.0        # K
    gap_max: float = 1.8e-9  # m
    Kth: float = 0.52e-9     # m*V
    C: float = 0.35e-9       # m
    WL: float = 1.154        # select-transistor W/L that reproduces the published gaps (0.95/0.85/0.73 nm)

    def gmin(self, vgate):
        return self.Kth * self.WL / vgate + self.C


IHP_PUBLISHED = ReRAMParams()


def current(p: ReRAMParams, v, g):
    return p.I0 * np.exp(-g / p.g0) * np.sinh(v / p.V0)


def conductance_small_signal(p, g):
    return p.I0 * math.exp(-g / p.g0) / p.V0


def gap_rate(p: ReRAMParams, v, g, i=None):
    """dg/dt in m/s."""
    if i is None:
        i = current(p, v, g)
    T = p.T0 + abs(v * i) * p.Rth
    kT = KB_EV * T
    gamma = p.gamma0 - p.beta * (g / 1e-9) ** p.alpha
    x = gamma * p.a0 * v / (p.tox * kT)
    x = np.clip(x, -300.0, 300.0)
    return -p.v0 * np.exp(-p.Ea / kT) * np.sinh(x)


def step_gap(p, v, g, dt, gmin, gmax=None):
    """Advance the gap by dt with sub-stepping so that one step never moves the gap by more than 2 pm."""
    gmax = p.gap_max if gmax is None else gmax
    t = 0.0
    while t < dt:
        r = gap_rate(p, v, g)
        if r == 0.0:
            break
        h = min(dt - t, 2e-12 / abs(r))
        g = g + r * h
        if g <= gmin:
            return gmin
        if g >= gmax:
            return gmax
        t += h
    return g


# ---------------------------------------------------------------- select transistor (stand-in)
@dataclass(frozen=True)
class NMOS:
    """Square-law NMOS with velocity-saturation-style limiting; a stand-in until the PSP model is used.
    Defaults approximate the SG13G2 3.3 V NMOS targets (Vth 0.70 V, 560 uA/um at Vgs = Vds = 3.3 V, L = 0.45 um)."""
    W: float = 0.52e-6
    L: float = 0.45e-6
    vth: float = 0.70
    idsat_per_um: float = 560e-6   # A/um at vgs = vds = 3.3 V
    lam: float = 0.03
    theta: float = 0.55            # 1/V mobility / velocity degradation

    def kp(self):
        vov = 3.3 - self.vth
        # idsat = 0.5*kp*(W/L)*vov^2/(1+theta*vov) for W = 1 um
        return self.idsat_per_um * 2 * (1 + self.theta * vov) / (vov ** 2) * self.L / 1e-6

    def ids(self, vgs, vds, vsb=0.0):       # the stand-in has no body effect
        vov = vgs - self.vth
        if vov <= 0 or vds <= 0:
            return 0.0
        k = self.kp() * self.W / self.L / (1 + self.theta * vov)
        vdsat = vov
        if vds < vdsat:
            return k * (vov * vds - 0.5 * vds * vds) * (1 + self.lam * vds)
        return 0.5 * k * vov * vov * (1 + self.lam * vds)


def solve_1t1r(p, mos, v_applied, vgate, g):
    """Series ReRAM (top) + NMOS (source grounded). Returns (v_cell, i). v_applied >= 0."""
    lo, hi = 0.0, v_applied
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        i_cell = float(current(p, mid, g))
        i_mos = mos.ids(vgate, v_applied - mid)
        if i_cell > i_mos:
            hi = mid
        else:
            lo = mid
    v = 0.5 * (lo + hi)
    return v, float(current(p, v, g))


def solve_1t1r_reset(p, mos, v_sl, vgate, g):
    """RESET polarity: source line driven to v_sl, bit line (top electrode) at 0 V, gate at vgate.
    The transistor is now a source follower: its source is the ReRAM bottom electrode node.
    Returns (v_cell (negative), i (negative))."""
    lo, hi = 0.0, v_sl                      # voltage of the internal node n (bottom electrode)
    for _ in range(60):
        n = 0.5 * (lo + hi)
        i_cell = -float(current(p, -n, g))  # current flowing from n up through the cell to the 0 V bit line
        i_mos = mos.ids(vgate - n, v_sl - n, n)   # source and so the source-to-body voltage sit at n
        if i_mos > i_cell:
            lo = n
        else:
            hi = n
    n = 0.5 * (lo + hi)
    return -n, float(current(p, -n, g))
