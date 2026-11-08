#!/bin/bash
# PC batch 6 (reram-eda image): SKY130 read path with the open_pdks sky130B models, all corners and the mismatch
# Monte Carlo, on all cores (circuits/ngspice/sky130_read.py).
cd /w
python3 -m venv /tmp/v && /tmp/v/bin/pip -q install numpy
ngspice -v | head -2
export SKY130_NGSPICE_LIB=/opt/pdk/sky130B/libs.tech/ngspice/sky130.lib.spice SKY130_FD_PR=/unused JOBS=$(nproc)
/tmp/v/bin/python circuits/ngspice/sky130_read.py
echo READ_DONE
