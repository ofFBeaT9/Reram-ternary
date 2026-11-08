#!/bin/bash
# PC batch 19 (reram-eda image, repository at /w), 12 October 2026: ChipFoundry's precheck in ChipFoundry's own tool
# versions, as pinned by cf-precheck (dependencies/Dockerfile, .github/workflows/precheck_test.yml, commit 6c401ed):
# Magic 8.3.471, netgen 1.5.272, CVC v1.1.7, KLayout 0.29.12, and the PDK open_pdks 3e0e31d (ciel, ChipFoundry's
# release site). Batches 12-16 used Magic 8.3.685, the image's netgen, CVC from its main branch and open_pdks 1e35547.
# Runs the precheck on the final GDS twice: with sky130B (the variant with the ReRAM layer) and, for information, with
# sky130A (the default of ChipFoundry's analog template).
cd /w
md5sum /w/chip/sky130/caravan/gds/user_analog_project_wrapper.gds
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq > /dev/null 2>&1
apt-get install -y -qq gawk gettext autopoint bison flex autoconf automake libtool pkg-config libreadline-dev git \
   tcl-dev tk-dev libx11-dev libcairo2-dev m4 csh > /tmp/apt.log 2>&1 || tail -5 /tmp/apt.log
for v in 0.29.12; do curl -sfL -o /tmp/klayout.deb "https://www.klayout.org/downloads/Ubuntu-24/klayout_${v}-1_amd64.deb"; done
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
magic --version 2>/dev/null || magic -dnull -noconsole --version 2>/dev/null | head -2
echo "=== PDK open_pdks 3e0e31d through ciel"
python3 -m venv /tmp/v && /tmp/v/bin/pip -q install /w/flow/eda/cf-precheck numpy ciel > /tmp/pip.log 2>&1 || tail -20 /tmp/pip.log
export CIEL_DATA_SOURCE=static-web:https://chipfoundry.github.io/ciel-releases
/tmp/v/bin/ciel enable 3e0e31dcce8519a7dbb82590346db16d91b7244f --pdk-root /opt/cfpdk --pdk sky130A > /tmp/ciel.log 2>&1 || tail -20 /tmp/ciel.log
ls /opt/cfpdk; cat /opt/cfpdk/sky130B/SOURCES 2>/dev/null; ls /opt/cfpdk/sky130B/libs.ref 2>/dev/null | grep -i reram
/tmp/v/bin/cf-precheck --version
G=/w/flow/eda/caravel_golden
for V in sky130B sky130A; do
  echo "=== precheck, ChipFoundry tool versions, $V"
  rm -rf /w/flow/eda/precheck_cfenv_$V /w/chip/sky130/caravan/.cf /w/chip/sky130/caravan/precheck_results
  PDK_ROOT=/opt/cfpdk PDK_PATH=/opt/cfpdk/$V PDKPATH=/opt/cfpdk/$V timeout 3h /tmp/v/bin/cf-precheck -i /w/chip/sky130/caravan \
     -p /opt/cfpdk/$V -c $G --magic-drc -o /w/flow/eda/precheck_cfenv_$V
  echo "PRECHECK_${V}_RC=$?"
  cat /w/flow/eda/precheck_cfenv_$V/logs/tools.info /w/flow/eda/precheck_cfenv_$V/logs/pdks.info 2>/dev/null; echo
done
rm -rf /w/chip/sky130/caravan/.cf /w/chip/sky130/caravan/precheck_results
echo BATCH19_DONE
