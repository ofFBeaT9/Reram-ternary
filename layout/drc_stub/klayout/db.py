# Stand-in used only when the container has the KLayout application but not its Python module:
# run_drc.py imports klayout.db solely to find the top cell, which --topcell supplies.
class Layout:
    def __init__(self):
        raise RuntimeError("klayout.db stub: pass --topcell")
