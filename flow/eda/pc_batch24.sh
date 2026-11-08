#!/bin/bash
# PC batch 24 (reram-eda image, repository at /w), 4 November 2026: the revision 4.6 GDS (security study: the digital
# block placed and routed again in batch 23, same die; top level rebuilt by top.py) in ChipFoundry's own tool versions,
# the same as batch 22 (cf-precheck 6c401ed: Magic 8.3.471, netgen 1.5.272, CVC v1.1.7, KLayout 0.29.12, PDK open_pdks
# 3e0e31d from ChipFoundry's ciel release site).
#   1. ChipFoundry precheck, sky130B, ChipFoundry's tool versions             -> flow/eda/precheck_cfenv4_sky130B
#   2. Magic full-rule DRC and Magic antenna check with ChipFoundry's Magic and tech files (signoff.py)
#                                                                              -> results/sky130_chip/top_signoff_cfenv.json
cd /w
md5sum /w/chip/sky130/caravan/gds/user_analog_project_wrapper.gds
export DEBIAN_FRONTEND=noninteractive
# (batch 24, 5 November: archive.ubuntu.com could not be reached, KLayout was not installed and 10 of 14 checks failed
#  in 0.0 s; the package steps are now retried, and the run stops if KLayout is missing)
for i in 1 2 3 4 5; do apt-get update -qq > /dev/null 2>&1 && \
  apt-get install -y -qq --fix-missing gawk gettext autopoint bison flex autoconf automake libtool pkg-config libreadline-dev git \
   tcl-dev tk-dev libx11-dev libcairo2-dev m4 csh zip > /tmp/apt.log 2>&1 && break; tail -3 /tmp/apt.log; sleep 60; done
for i in 1 2 3 4 5; do curl -sfL -o /tmp/klayout.deb "https://www.klayout.org/downloads/Ubuntu-24/klayout_0.29.12-1_amd64.deb" && \
  apt-get install -y -qq --fix-missing /tmp/klayout.deb > /tmp/kl.log 2>&1 && break; tail -3 /tmp/kl.log; sleep 60; done
# (batch 28, 7 November: the KLayout package unpacked but its Qt dependencies could not be fetched, so ruby was missing and
#  the XOR check failed; finish the dependencies with retries and require a working KLayout and ruby)
for i in $(seq 1 15); do klayout -b -v > /dev/null 2>&1 && ruby -v > /dev/null 2>&1 && break
  apt-get update -qq > /dev/null 2>&1; apt-get -f install -y -qq --fix-missing > /tmp/fix.log 2>&1 && apt-get install -y -qq ruby > /tmp/fix2.log 2>&1; tail -2 /tmp/fix.log; sleep 60; done
klayout -b -v > /dev/null 2>&1 && ruby -v > /dev/null 2>&1 || { echo "KLAYOUT_MISSING: no precheck"; echo BATCH24_DONE; exit 1; }
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
M=/w/flow/eda/cfpdk_mirror
if [ -f $M/sky130/manifest.json ]; then
  # the same release, downloaded on 6 November from github.com/chipfoundry/ciel-releases (tools/cf_pdk_mirror.sh) because
  # chipfoundry.github.io timed out from this PC in batch 24; checked against SHA256SUMS, served on 127.0.0.1
  (cd $M/files && sha256sum -c SHA256SUMS) || { echo "MIRROR_HASH_MISMATCH"; echo BATCH24_DONE; exit 1; }
  (cd $M && python3 -m http.server 8765 --bind 127.0.0.1 > /dev/null 2>&1 &) ; sleep 2
  export CIEL_DATA_SOURCE=static-web:http://127.0.0.1:8765 NO_PROXY=127.0.0.1 no_proxy=127.0.0.1
fi
# --pdk-family sky130: both variants with ciel's default libraries, which for sky130B include sky130_fd_pr_reram
# (batch 22 used "--pdk sky130A", which left that library out of /opt/cfpdk/sky130B)
/tmp/v/bin/ciel enable 3e0e31dcce8519a7dbb82590346db16d91b7244f --pdk-root /opt/cfpdk --pdk-family sky130 > /tmp/ciel.log 2>&1 || tail -20 /tmp/ciel.log
[ -d /opt/cfpdk/sky130B/libs.tech/magic ] || { echo "PDK_MISSING: no precheck"; tail -5 /tmp/ciel.log; echo BATCH24_DONE; exit 1; }
ls /opt/cfpdk/sky130B/libs.ref
cat /opt/cfpdk/sky130B/SOURCES 2>/dev/null; echo
/tmp/v/bin/cf-precheck --version
G=/w/flow/eda/caravel_golden
[ -f $G/gds/user_analog_project_wrapper_empty.gds ] || gunzip -k $G/gds/user_analog_project_wrapper_empty.gds.gz
echo "=== 1. precheck, ChipFoundry tool versions, sky130B"
rm -rf /w/flow/eda/precheck_cfenv4_sky130B /w/chip/sky130/caravan/.cf /w/chip/sky130/caravan/precheck_results
PDK_ROOT=/opt/cfpdk PDK_PATH=/opt/cfpdk/sky130B PDKPATH=/opt/cfpdk/sky130B timeout 3h /tmp/v/bin/cf-precheck -i /w/chip/sky130/caravan \
   -p /opt/cfpdk/sky130B -c $G --magic-drc -o /w/flow/eda/precheck_cfenv4_sky130B
echo "PRECHECK_CFENV_RC=$?"
cat /w/flow/eda/precheck_cfenv4_sky130B/logs/tools.info /w/flow/eda/precheck_cfenv4_sky130B/logs/pdks.info 2>/dev/null; echo
grep -E "Final result|property|Property" /w/flow/eda/precheck_cfenv4_sky130B/logs/LVS_check.log 2>/dev/null | head -20
echo "=== 2. Magic DRC and antenna check, ChipFoundry's Magic 8.3.471 and sky130B tech"
magic -dnull -noconsole --version 2>/dev/null | head -1
PDK_ROOT=/opt/cfpdk python3 /w/layout/sky130/periph/signoff.py /w/chip/sky130/caravan/gds/user_analog_project_wrapper.gds \
   /w/results/sky130_chip/top_signoff_cfenv.json
echo "SIGNOFF_CFENV_RC=$?"
rm -rf /w/chip/sky130/caravan/.cf /w/chip/sky130/caravan/precheck_results
echo BATCH24_DONE
