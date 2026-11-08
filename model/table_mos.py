"""Select transistor from a table: Id(Vsb, Vgs, Vds) of the real IHP sg13_hv_nmos (PSP103 through Gnucap).
Built by circuits/gnucap/make_mos_table.py; trilinear interpolation. Same interface as the stand-in NMOS."""
from pathlib import Path
import numpy as np

_FILE = Path(__file__).resolve().parents[1] / "results" / "sg13_hv_nmos_table.npz"


class TableNMOS:
    def __init__(self, W_um=4.5, corner="tt", path=_FILE):
        z = np.load(path)
        key = f"id_{corner}_W{float(W_um)}"
        if key not in z:
            raise KeyError(f"{key} not in table; available: {[k for k in z.files if k.startswith('id_')]}")
        self.W = W_um * 1e-6
        self.L = 0.45e-6
        self.corner = corner
        self.vsb, self.vgs, self.vds, self.tab = z["vsb"], z["vgs"], z["vds"], z[key]

    @staticmethod
    def _idx(axis, x):
        x = min(max(x, axis[0]), axis[-1])
        k = min(int((x - axis[0]) / (axis[1] - axis[0])), len(axis) - 2)
        return k, (x - axis[k]) / (axis[k + 1] - axis[k])

    def ids(self, vgs, vds, vsb=0.0):
        if vds <= 0.0 or vgs <= 0.0:
            return 0.0
        a, fa = self._idx(self.vsb, vsb)
        b, fb = self._idx(self.vgs, vgs)
        c, fc = self._idx(self.vds, vds)
        t = self.tab[a:a + 2, b:b + 2, c:c + 2]
        t = t[0] * (1 - fa) + t[1] * fa
        t = t[0] * (1 - fb) + t[1] * fb
        return float(t[0] * (1 - fc) + t[1] * fc)
