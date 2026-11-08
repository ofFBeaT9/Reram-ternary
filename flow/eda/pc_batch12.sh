#!/bin/bash
# PC batch 12 (reram-eda image, repository at /w), 12 October 2026: sign-off of the final GDS (md5 in pc_batch12.log).
# Batch 11 found met2.2 x3 in Magic DRC (fixed in top.py: the pin stubs are 0.14 um wide inside the digital block) and
# its KLayout BEOL check stalled for 8 h in the first metal3 area rule, so that check runs here on its own with a time
# limit, after a diagnostic of the metal layers. CVC needed libreadline-dev.
#  1. tools: KLayout, gawk, CVC (built from source)
#  2. mutation test of TCIM0, both trit codes (pack from tb/mutation_remote.py gen), in the background on 24 cores
#  3. ChipFoundry precheck, all checks except the KLayout BEOL deck, Magic DRC included
#  4. KLayout BEOL deck alone, 3 h limit; metal-layer diagnostic first
#  5. formal proofs and their injected faults
cd /w
G=/w/flow/eda/caravel_golden
GDS=/w/chip/sky130/caravan/gds/user_analog_project_wrapper.gds
md5sum $GDS
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq > /dev/null 2>&1
apt-get install -y -qq gawk gettext autopoint bison flex autoconf automake libtool pkg-config libreadline-dev > /tmp/apt.log 2>&1 || tail -5 /tmp/apt.log
for v in 0.29.12 0.30.4; do curl -sfL -o /tmp/klayout.deb "https://www.klayout.org/downloads/Ubuntu-24/klayout_${v}-1_amd64.deb" && break; done
apt-get install -y -qq /tmp/klayout.deb > /tmp/kl.log 2>&1 || tail -5 /tmp/kl.log
klayout -v; gawk --version | head -1
echo "=== mutation (background)"
( cd /w/flow/eda && rm -rf mutpack11 && tar xzf mutpack11.tgz && \
  nice python3 mutpack11/mutation_remote.py run mutpack11 24 > mutation12.log 2>&1; echo MUTATION_EXIT=$? >> mutation12.log ) &
MUTPID=$!
echo "=== cvc"
rm -rf /tmp/cvc; git clone --depth 1 https://github.com/d-m-bailey/cvc /tmp/cvc > /tmp/cvc_build.log 2>&1
( cd /tmp/cvc && (autoreconf -vif && ./configure --disable-nls && make -j8 && make install) >> /tmp/cvc_build.log 2>&1 )
cp /tmp/cvc_build.log /w/flow/eda/cvc_build.log
which cvc_rv && echo CVC_OK || { echo CVC_BUILD_FAILED; grep -m5 -i "error" /tmp/cvc_build.log; }
python3 -m venv /tmp/v && /tmp/v/bin/pip -q install /w/flow/eda/cf-precheck numpy > /tmp/pip.log 2>&1 || tail -20 /tmp/pip.log
/tmp/v/bin/cf-precheck --version
[ -f $G/gds/user_analog_project_wrapper_empty.gds ] || gunzip -k $G/gds/user_analog_project_wrapper_empty.gds.gz
echo "=== precheck (all but the KLayout BEOL deck)"
rm -rf /w/flow/eda/precheck_out /w/chip/sky130/caravan/.cf /w/chip/sky130/caravan/precheck_results
timeout 4h /tmp/v/bin/cf-precheck -i /w/chip/sky130/caravan -p /opt/pdk/sky130B -c $G --magic-drc \
   -o /w/flow/eda/precheck_out --skip-checks klayout_beol
echo "PRECHECK_RC=$?"
echo "=== metal diagnostic"
timeout 30m klayout -b -r /w/flow/eda/klayout_m3_diag.py -rd gdsin=$GDS 2>&1 | tee /w/flow/eda/klayout_m3_diag.log
echo "=== KLayout BEOL deck"
D=$(dirname $(/tmp/v/bin/python3 -c "import cf_precheck,sys;print(cf_precheck.__file__)"))/drc_scripts
mkdir -p /w/flow/eda/beol_out
( time timeout 3h klayout -b -r $D/sky130B_mr.drc -rd input=$GDS -rd topcell=user_analog_project_wrapper \
   -rd report=/w/flow/eda/beol_out/klayout_beol_check.xml -rd thr=16 -rd beol=true ) > /w/flow/eda/beol_out/klayout_beol_check.log 2>&1
echo "BEOL_RC=$? items $(grep -c '<item>' /w/flow/eda/beol_out/klayout_beol_check.xml 2>/dev/null)"
tail -3 /w/flow/eda/beol_out/klayout_beol_check.log
echo "=== waiting for the mutation test"
wait $MUTPID; tail -6 /w/flow/eda/mutation12.log; ls /w/flow/eda/mutpack11/*.json
echo "=== formal"
cd /w/formal
yosys -q -p "read_slang --help" > /dev/null 2>&1 || {
  echo "read_slang needs the plugin: loading it in copies of the .sby files"
  for f in tcim_spi.sby tcim_core.sby; do sed -i "s/^\[script\]$/[script]\nplugin -i slang/" $f; done; }
( sby -f tcim_spi.sby > /tmp/f_spi.log 2>&1 & sby -f tcim_core.sby safety > /tmp/f_safety.log 2>&1 & \
  sby -f tcim_core.sby safety_pnx > /tmp/f_pnx.log 2>&1 & sby -f tcim_core.sby progress > /tmp/f_prog.log 2>&1 & wait )
cat /tmp/f_spi.log /tmp/f_safety.log /tmp/f_pnx.log /tmp/f_prog.log > /w/flow/eda/formal12.log
grep "DONE" /w/flow/eda/formal12.log
cd /w && SBY=sby python3 formal/check_faults.py > /w/flow/eda/formal_faults12.log 2>&1; tail -12 /w/flow/eda/formal_faults12.log
cd /w/formal && for f in tcim_spi.sby tcim_core.sby; do sed -i '/^plugin -i slang$/d' $f; done
echo BATCH12_DONE
