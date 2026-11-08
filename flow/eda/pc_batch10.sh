#!/bin/bash
# PC batch 10 (reram-eda image, repository at /w), 11 October 2026: sign-off of the SKY130 test chip, second pass.
#  0. Tools the precheck needs beyond batch 9: KLayout, gawk (the OEB script is gawk), CVC (cvc_rv, built from source).
#  1. ChipFoundry's precheck on chip/sky130/caravan (all checks, with the optional Magic DRC).
#  2. Magic antenna check of the whole user area (extraction without parasitics).
#  3. The programming ladders with the longest routed lines and the highest set-verify trip (worst case).
cd /w
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq > /dev/null 2>&1
apt-get install -y -qq gawk bison flex autoconf automake libtool pkg-config > /tmp/apt.log 2>&1 || tail -5 /tmp/apt.log
for v in 0.29.12 0.30.4; do curl -sfL -o /tmp/klayout.deb "https://www.klayout.org/downloads/Ubuntu-24/klayout_${v}-1_amd64.deb" && break; done
apt-get install -y -qq /tmp/klayout.deb > /tmp/kl.log 2>&1 || tail -5 /tmp/kl.log
echo "=== cvc"
git clone --depth 1 https://github.com/d-m-bailey/cvc /tmp/cvc > /tmp/cvc_build.log 2>&1
( cd /tmp/cvc && (autoreconf -vif && ./configure --disable-nls && make -j"$(nproc)" && make install) >> /tmp/cvc_build.log 2>&1 )
which cvc_rv || { echo CVC_BUILD_FAILED; tail -30 /tmp/cvc_build.log; }
cp /tmp/cvc_build.log /w/flow/eda/cvc_build.log
klayout -v; gawk --version | head -1
python3 -m venv /tmp/v && /tmp/v/bin/pip -q install /w/flow/eda/cf-precheck numpy > /tmp/pip.log 2>&1 || tail -20 /tmp/pip.log
/tmp/v/bin/cf-precheck --version
G=/w/flow/eda/caravel_golden
[ -f $G/gds/user_analog_project_wrapper_empty.gds ] || gunzip -k $G/gds/user_analog_project_wrapper_empty.gds.gz
echo "=== precheck"
rm -rf /w/flow/eda/precheck_out /w/chip/sky130/caravan/.cf /w/chip/sky130/caravan/precheck_results
/tmp/v/bin/cf-precheck -i /w/chip/sky130/caravan -p /opt/pdk/sky130B -c $G --magic-drc -o /w/flow/eda/precheck_out
echo "PRECHECK_RC=$?"
echo "=== antenna"
mkdir -p /tmp/ant && cd /tmp/ant
cat > ant.tcl <<'TCL'
gds readonly true
gds read /w/chip/sky130/caravan/gds/user_analog_project_wrapper.gds
load user_analog_project_wrapper
select top cell
extract no capacitance
extract no coupling
extract no resistance
extract no length
extract do local
extract all
antennacheck debug
antennacheck
puts "ANTENNA_ERRORS [feedback count]"
quit -noprompt
TCL
magic -dnull -noconsole -rcfile /opt/pdk/sky130B/libs.tech/magic/sky130B.magicrc ant.tcl > /w/flow/eda/antenna.log 2>&1
grep -E "ANTENNA_ERRORS" /w/flow/eda/antenna.log
echo "=== worst-case ladders"
cd /w/chip/sky130/sim
python3 -m venv /tmp/v2 && /tmp/v2/bin/pip -q install numpy
RBL=$(python3 -c "import json;d=json.load(open('/w/results/sky130_chip/macro_rc.json'));print(d['worst_case']['R_bitline_ohm'])")
RSL=$(python3 -c "import json;d=json.load(open('/w/results/sky130_chip/macro_rc.json'));print(d['worst_case']['R_sourceline_ohm'])")
ST=$(python3 -c "import json;d=json.load(open('/w/results/sky130_chip/macro_rc.json'));print(d['worst_case']['set_target_uS'])")
echo "RBL=$RBL RSL=$RSL SET_TARGET_US=$ST"
SKY130_NGSPICE_LIB=/opt/pdk/sky130B/libs.tech/ngspice/sky130.lib.spice JOBS=$(nproc) LADDERS_ONLY=1 RBL=$RBL RSL=$RSL \
  SET_TARGET_US=$ST MACRO_SIM_OUT=macro_sim_worst.json /tmp/v2/bin/python macro_sim.py | tail -30
echo BATCH10_DONE
