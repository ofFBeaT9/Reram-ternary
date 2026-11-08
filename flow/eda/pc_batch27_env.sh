# shared by the reram-eda parts of batch 27: OSS CAD Suite with the slang front end loaded, Verilator root, PDK paths
mkdir -p /tmp/bin && printf '#!/bin/bash\nexec /opt/oss-cad-suite/bin/yosys -m slang "$@"\n' > /tmp/bin/yosys && chmod +x /tmp/bin/yosys
export PATH=/tmp/bin:$PATH
VR=/opt/oss-cad-suite/share/verilator
if [ ! -x $VR/bin/verilator ]; then
  mkdir -p /tmp/vroot/bin && ln -sf /opt/oss-cad-suite/bin/verilator* /tmp/vroot/bin/ && ln -sf $VR/include /tmp/vroot/include; VR=/tmp/vroot; fi
export VERILATOR_ROOT=$VR SBY=sby
export SKY130_STDCELL_LIB=/opt/pdk/sky130B/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
