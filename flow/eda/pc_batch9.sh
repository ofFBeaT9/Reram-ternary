#!/bin/bash
# PC batch 9 (reram-eda image, repository at /w), 11 October 2026: sign-off checks of the SKY130 test chip.
#  1. ChipFoundry's precheck (cf-precheck, all checks for an analog project, with the optional Magic DRC) on the project
#     folder chip/sky130/caravan; KLayout is installed into the container for its KLayout checks.
#  2. Magic antenna check of the whole user area.
#  3. The programming ladders again with the longest routed lines and the highest set-verify trip seen under mismatch
#     (chip/sky130/sim/macro_sim.py, worst case; values from results/sky130_chip/macro_rc.json).
cd /w
export DEBIAN_FRONTEND=noninteractive
echo "=== tools"; magic --version; netgen -batch quit 2>&1 | head -2; cat /opt/pdk.version
apt-get update -qq > /dev/null 2>&1
for v in 0.29.12 0.30.4 0.29.11; do
  curl -sfL -o /tmp/klayout.deb "https://www.klayout.org/downloads/Ubuntu-24/klayout_${v}-1_amd64.deb" && break
done
if [ -s /tmp/klayout.deb ]; then apt-get install -y -qq /tmp/klayout.deb > /tmp/kl_install.log 2>&1; else apt-get install -y -qq klayout > /tmp/kl_install.log 2>&1; fi
klayout -v || { echo KLAYOUT_MISSING; tail -20 /tmp/kl_install.log; }
python3 -m venv /tmp/v && /tmp/v/bin/pip -q install /w/flow/eda/cf-precheck numpy > /tmp/pip.log 2>&1 || tail -20 /tmp/pip.log
/tmp/v/bin/cf-precheck --version
G=/w/flow/eda/caravel_golden
[ -f $G/gds/user_analog_project_wrapper_empty.gds ] || gunzip -k $G/gds/user_analog_project_wrapper_empty.gds.gz
echo "=== precheck"
rm -rf /w/flow/eda/precheck_out
/tmp/v/bin/cf-precheck -i /w/chip/sky130/caravan -p /opt/pdk/sky130B -c $G --magic-drc -o /w/flow/eda/precheck_out
echo "PRECHECK_RC=$?"
echo "=== antenna"
mkdir -p /tmp/ant && cd /tmp/ant
cat > ant.tcl <<'TCL'
gds read /w/chip/sky130/caravan/gds/user_analog_project_wrapper.gds
load user_analog_project_wrapper
select top cell
extract do local
extract all
antennacheck debug
antennacheck
puts "ANTENNA_ERRORS [feedback count]"
quit -noprompt
TCL
magic -dnull -noconsole -rcfile /opt/pdk/sky130B/libs.tech/magic/sky130B.magicrc ant.tcl > /w/flow/eda/antenna.log 2>&1
grep -E "ANTENNA_ERRORS|antenna" /w/flow/eda/antenna.log | tail -5
echo "=== worst-case ladders"
cd /w/chip/sky130/sim
python3 -m venv /tmp/v2 && /tmp/v2/bin/pip -q install numpy
RBL=$(python3 -c "import json;d=json.load(open('/w/results/sky130_chip/macro_rc.json'));print(d['worst_case']['R_bitline_ohm'])")
RSL=$(python3 -c "import json;d=json.load(open('/w/results/sky130_chip/macro_rc.json'));print(d['worst_case']['R_sourceline_ohm'])")
ST=$(python3 -c "import json;d=json.load(open('/w/results/sky130_chip/macro_rc.json'));print(d['worst_case']['set_target_uS'])")
echo "RBL=$RBL RSL=$RSL SET_TARGET_US=$ST"
SKY130_NGSPICE_LIB=/opt/pdk/sky130B/libs.tech/ngspice/sky130.lib.spice JOBS=$(nproc) LADDERS_ONLY=1 RBL=$RBL RSL=$RSL \
  SET_TARGET_US=$ST MACRO_SIM_OUT=macro_sim_worst.json /tmp/v2/bin/python macro_sim.py | tail -30
echo BATCH9_DONE
