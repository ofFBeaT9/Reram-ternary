"""Export the ternary digits network and its test set for the RTL test bench.
Files (plain text, integers separated by spaces):
  net_w1.txt   72 lines x 72 weights  (rows = inputs, columns = hidden units)
  net_w2.txt   72 lines x 10 weights
  net_x.txt    one line per test sample: 72 input trits, then the label
  net_meta.txt theta n_samples software_correct
"""
import sys, os
import numpy as np
here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
sys.path.insert(0, os.path.join(root, "array"))
from exp_network import load, infer_exact
d = np.load(os.path.join(root, "results", "ternary_digits_weights.npz"))
T1, T2, theta = d["T1"], d["T2"], int(d["theta"])
Xtr, ytr, Xte, yte = load()
pred, _, _ = infer_exact(Xte, T1, T2, theta)
out = os.path.join(here, "vectors")
np.savetxt(os.path.join(out, "net_w1.txt"), T1, fmt="%d")
np.savetxt(os.path.join(out, "net_w2.txt"), T2, fmt="%d")
np.savetxt(os.path.join(out, "net_x.txt"), np.hstack([Xte, yte[:, None], pred[:, None]]), fmt="%d")
open(os.path.join(out, "net_meta.txt"), "w").write(f"{theta} {len(yte)} {int((pred == yte).sum())}\n")
print("exported", T1.shape, T2.shape, Xte.shape, "theta", theta, "software correct", int((pred == yte).sum()), "of", len(yte))
