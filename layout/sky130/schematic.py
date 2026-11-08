"""Schematic netlist of the 72 x 24 SKY130 TCIM0 tile for LVS (and a copy with one deliberate change)."""
import sys
ROWS, COLS = 72, 24
ports = [f"WL{r}" for r in range(ROWS)] + [f"BLP{c}" for c in range(COLS)] + [f"BLN{c}" for c in range(COLS)] + [f"SL{c}" for c in range(COLS)] + ["VSS"]
def netlist(fault=False):
    out = [".subckt tcim_sky130_array " + " ".join(ports)]
    for r in range(ROWS):
        for c in range(COLS):
            for s, bl in (("p", f"BLP{c}"), ("n", f"BLN{c}")):
                d = f"d{s}_{r}_{c}"
                out.append(f"XM{s}_{r}_{c} {d} WL{r} SL{c} VSS sky130_fd_pr__nfet_g5v0d10v5 w=1 l=0.5")
                top = bl
                if fault and r == 37 and c == 5 and s == "n":
                    top = "BLP5"                       # the fault: one ReRAM element on the wrong bit line
                out.append(f"XR{s}_{r}_{c} {top} {d} sky130_fd_pr_reram__reram_cell area_ox=0.0676")
    out.append(".ends")
    return "\n".join(out) + "\n"
open("schematic.spice", "w").write(netlist())
open("schematic_fault.spice", "w").write(netlist(True))
