#!/bin/bash
# PC batch 21 (reram-eda image, repository at /w), 12 October 2026: final check of the GDS rebuilt with the standard
# cells of ChipFoundry's pinned PDK (layout/sky130/periph/stdcells_cf, open_pdks 3e0e31d), in ChipFoundry's own tool
# versions (cf-precheck 6c401ed: Magic 8.3.471, netgen 1.5.272, CVC v1.1.7, KLayout 0.29.12, PDK open_pdks 3e0e31d
# from ChipFoundry's ciel release site). Batch 19 ran the same precheck on the previous GDS: everything passed except
# LVS (property errors on the tie cell conb_1, whose poly resistors are 0.045 um long in 3e0e31d and 0.5 um in 1e35547).
#   1. ChipFoundry precheck, sky130B, ChipFoundry's tool versions             -> flow/eda/precheck_cfenv2_sky130B
#   2. Magic full-rule DRC and Magic antenna check with ChipFoundry's Magic and tech files (signoff.py)
#                                                                              -> results/sky130_chip/top_signoff_cfenv.json
#   3. for information: the same precheck in the image's tool versions (open_pdks 1e35547); a conb_1 property error
#      is expected there now, in the opposite direction                       -> flow/eda/precheck_ourenv2_sky130B
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
OLDPATH=$PATH
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
rm -rf /w/flow/eda/precheck_cfenv2_sky130B /w/chip/sky130/caravan/.cf /w/chip/sky130/caravan/precheck_results
PDK_ROOT=/opt/cfpdk PDK_PATH=/opt/cfpdk/sky130B PDKPATH=/opt/cfpdk/sky130B timeout 3h /tmp/v/bin/cf-precheck -i /w/chip/sky130/caravan \
   -p /opt/cfpdk/sky130B -c $G --magic-drc -o /w/flow/eda/precheck_cfenv2_sky130B
echo "PRECHECK_CFENV_RC=$?"
cat /w/flow/eda/precheck_cfenv2_sky130B/logs/tools.info /w/flow/eda/precheck_cfenv2_sky130B/logs/pdks.info 2>/dev/null; echo
grep -E "Final result|property|Property" /w/flow/eda/precheck_cfenv2_sky130B/logs/LVS_check.log 2>/dev/null | head -20
echo "=== 2. Magic DRC and antenna check, ChipFoundry's Magic 8.3.471 and sky130B tech"
magic -dnull -noconsole --version 2>/dev/null | head -1
PDK_ROOT=/opt/cfpdk python3 /w/layout/sky130/periph/signoff.py /w/chip/sky130/caravan/gds/user_analog_project_wrapper.gds \
   /w/results/sky130_chip/top_signoff_cfenv.json
echo "SIGNOFF_CFENV_RC=$?"
echo "=== 3. for information: precheck in the image's tool versions (open_pdks 1e35547)"
# the image has no CVC of its own: use the CVC v1.1.7 built above
mkdir -p /tmp/cvcbin && ln -sf /opt/cf/bin/cvc_rv /tmp/cvcbin/cvc_rv
export PATH=/tmp/cvcbin:$OLDPATH
which magic netgen cvc_rv
rm -rf /w/flow/eda/precheck_ourenv2_sky130B /w/chip/sky130/caravan/.cf /w/chip/sky130/caravan/precheck_results
timeout 3h /tmp/v/bin/cf-precheck -i /w/chip/sky130/caravan -p /opt/pdk/sky130B -c $G --magic-drc -o /w/flow/eda/precheck_ourenv2_sky130B
echo "PRECHECK_OURENV_RC=$?"
grep -E "Final result|property|Property" /w/flow/eda/precheck_ourenv2_sky130B/logs/LVS_check.log 2>/dev/null | head -20
rm -rf /w/chip/sky130/caravan/.cf /w/chip/sky130/caravan/precheck_results
echo BATCH21_DONE
