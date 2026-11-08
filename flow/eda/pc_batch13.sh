#!/bin/bash
# PC batch 13, part 2 (reram-eda image, repository at /w), 12 October 2026: ChipFoundry's precheck exactly as it runs at
# submission (all checks, the KLayout BEOL deck included, default thread count), optional Magic DRC included, on the final
# GDS. Batch 12 ran the BEOL deck separately (0 markers) because batch 11 stalled in it on the GDS of 11 October.
cd /w
G=/w/flow/eda/caravel_golden
md5sum /w/chip/sky130/caravan/gds/user_analog_project_wrapper.gds
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq > /dev/null 2>&1
apt-get install -y -qq gawk gettext autopoint bison flex autoconf automake libtool pkg-config libreadline-dev > /tmp/apt.log 2>&1 || tail -5 /tmp/apt.log
for v in 0.29.12 0.30.4; do curl -sfL -o /tmp/klayout.deb "https://www.klayout.org/downloads/Ubuntu-24/klayout_${v}-1_amd64.deb" && break; done
apt-get install -y -qq /tmp/klayout.deb > /tmp/kl.log 2>&1 || tail -5 /tmp/kl.log
rm -rf /tmp/cvc; git clone --depth 1 https://github.com/d-m-bailey/cvc /tmp/cvc > /tmp/cvc_build.log 2>&1
( cd /tmp/cvc && (autoreconf -vif && ./configure --disable-nls && make -j8 && make install) >> /tmp/cvc_build.log 2>&1 )
which cvc_rv && echo CVC_OK || echo CVC_BUILD_FAILED
python3 -m venv /tmp/v && /tmp/v/bin/pip -q install /w/flow/eda/cf-precheck numpy > /tmp/pip.log 2>&1 || tail -20 /tmp/pip.log
/tmp/v/bin/cf-precheck --version; klayout -v; nproc
[ -f $G/gds/user_analog_project_wrapper_empty.gds ] || gunzip -k $G/gds/user_analog_project_wrapper_empty.gds.gz
echo "=== precheck (all checks)"
rm -rf /w/flow/eda/precheck_full /w/chip/sky130/caravan/.cf /w/chip/sky130/caravan/precheck_results
timeout 3h /tmp/v/bin/cf-precheck -i /w/chip/sky130/caravan -p /opt/pdk/sky130B -c $G --magic-drc -o /w/flow/eda/precheck_full
echo "PRECHECK_RC=$?"
rm -rf /w/chip/sky130/caravan/.cf /w/chip/sky130/caravan/precheck_results
echo BATCH13_DONE
