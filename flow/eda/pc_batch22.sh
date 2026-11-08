#!/bin/bash
# PC batch 22 (reram-eda image, repository at /w), 12 October 2026: the final GDS in ChipFoundry's own tool versions
# (cf-precheck 6c401ed: Magic 8.3.471, netgen 1.5.272, CVC v1.1.7, KLayout 0.29.12, PDK open_pdks 3e0e31d from
# ChipFoundry's ciel release site). Batch 21 ran the precheck on a GDS with every standard cell from 3e0e31d: LVS passed,
# the KLayout FEOL check reported one npc.2 violation at an and2_0 (3e0e31d's and2_0 has a notch in its NPC that
# open_pdks 1e35547 fills). The GDS now takes every standard cell from 1e35547 except conb_1, which comes from 3e0e31d
# (layout/sky130/periph/stdcells_cf/README.md).
#   1. ChipFoundry precheck, sky130B, ChipFoundry's tool versions             -> flow/eda/precheck_cfenv3_sky130B
#   2. Magic full-rule DRC and Magic antenna check with ChipFoundry's Magic and tech files (signoff.py)
#                                                                              -> results/sky130_chip/top_signoff_cfenv.json
cd /w
md5sum /w/chip/sky130/caravan/gds/user_analog_project_wrapper.gds
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq > /dev/null 2>&1
apt-get install -y -qq gawk gettext autopoint bison flex autoconf automake libtool pkg-config libreadline-dev git \
   tcl-dev tk-dev libx11-dev libcairo2-dev m4 csh > /tmp/apt.log 2>&1 || tail -5 /tmp/apt.log
curl -sfL -o /tmp/klayout.deb "https://www.klayout.org/downloads/Ubuntu-24/klayout_0.29.12-1_amd64.deb"
apt-get install -y -qq /tmp/klayout.deb > /tmp/kl.log 2>&1 || tail -5 /tmp/kl.log
P=/opt/cf; mkdir -p $P /tmp/src
echo "=== build Magic 8.3.471, netgen 1.5.272, CVC v1.1.7"
( cd /tmp/src && git clone -q --depth=1 --branch 8.3.471 https://github.com/RTimothyEdwards/magic.git magic && cd magic && \
  ./configure --prefix=$P > /tmp/magic.log 2>&1 && make -j16 >> /tmp/magic.log 2>&1 && make install >> /tmp/magic.log 2>&1 ) || { echo MAGIC_BUILD_FAILED; tail -20 /tmp/magic.log; }
( cd /tmp/src && git clone -q --depth=1 --branch 1.5.272 https://github.com/RTimothyEdwards/netgen.git netgen && cd netgen && \
  ./configure --prefix=$P > /tmp/netgen.log 2>&1 && make -j16 >> /tmp/netgen.log 2>&1 && make install >> /tmp/netgen.log 2>&1 ) || { echo NETGEN_BUILD_FAILED; tail -20 /tmp/netgen.log; }
( cd /tmp/src && git clone -q --depth=1 --branch v1.1.7 https://github.com/d-m-bailey/cvc.git cvc && cd cvc && \
  (autoreconf -vif && ./configure --disable-nls --prefix=$P && make -j16 && make install) > /tmp/cvc.log 2>&1 ) || { echo CVC_BUILD_FAILED; tail -20 /tmp/cvc.log; }
export PATH=$P/bin:$PATH
which magic netgen cvc_rv klayout
echo "=== PDK open_pdks 3e0e31d through ciel"
python3 -m venv /tmp/v && /tmp/v/bin/pip -q install /w/flow/eda/cf-precheck numpy ciel > /tmp/pip.log 2>&1 || tail -20 /tmp/pip.log
export CIEL_DATA_SOURCE=static-web:https://chipfoundry.github.io/ciel-releases
/tmp/v/bin/ciel enable 3e0e31dcce8519a7dbb82590346db16d91b7244f --pdk-root /opt/cfpdk --pdk sky130A > /tmp/ciel.log 2>&1 || tail -20 /tmp/ciel.log
cat /opt/cfpdk/sky130B/SOURCES 2>/dev/null; echo
/tmp/v/bin/cf-precheck --version
G=/w/flow/eda/caravel_golden
[ -f $G/gds/user_analog_project_wrapper_empty.gds ] || gunzip -k $G/gds/user_analog_project_wrapper_empty.gds.gz
echo "=== 1. precheck, ChipFoundry tool versions, sky130B"
rm -rf /w/flow/eda/precheck_cfenv3_sky130B /w/chip/sky130/caravan/.cf /w/chip/sky130/caravan/precheck_results
PDK_ROOT=/opt/cfpdk PDK_PATH=/opt/cfpdk/sky130B PDKPATH=/opt/cfpdk/sky130B timeout 3h /tmp/v/bin/cf-precheck -i /w/chip/sky130/caravan \
   -p /opt/cfpdk/sky130B -c $G --magic-drc -o /w/flow/eda/precheck_cfenv3_sky130B
echo "PRECHECK_CFENV_RC=$?"
cat /w/flow/eda/precheck_cfenv3_sky130B/logs/tools.info /w/flow/eda/precheck_cfenv3_sky130B/logs/pdks.info 2>/dev/null; echo
grep -E "Final result|property|Property" /w/flow/eda/precheck_cfenv3_sky130B/logs/LVS_check.log 2>/dev/null | head -20
echo "=== 2. Magic DRC and antenna check, ChipFoundry's Magic 8.3.471 and sky130B tech"
magic -dnull -noconsole --version 2>/dev/null | head -1
PDK_ROOT=/opt/cfpdk python3 /w/layout/sky130/periph/signoff.py /w/chip/sky130/caravan/gds/user_analog_project_wrapper.gds \
   /w/results/sky130_chip/top_signoff_cfenv.json
echo "SIGNOFF_CFENV_RC=$?"
rm -rf /w/chip/sky130/caravan/.cf /w/chip/sky130/caravan/precheck_results
echo BATCH22_DONE
