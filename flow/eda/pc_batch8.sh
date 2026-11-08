#!/bin/bash
# PC batch 8 (reram-eda image, repository at /w): statistical check of the reduced SKY130 library for the mismatch
# Monte Carlo (chip/sky130/sim/mc_libcheck.py): 48 trip points per reference level with the full library, on all cores.
cd /w
python3 -m venv /tmp/v && /tmp/v/bin/pip -q install numpy
export SKY130_NGSPICE_LIB=/opt/pdk/sky130B/libs.tech/ngspice/sky130.lib.spice SKY130_FD_PR=/unused JOBS=$(nproc)
ngspice -v | head -2; echo "cores: $(nproc)"
mkdir -p results/sky130_chip; rm -f results/sky130_chip/mc_libcheck.json
cd chip/sky130/sim && /tmp/v/bin/python mc_libcheck.py run 48 reset read set
echo BATCH8_DONE
