#!/bin/bash
# PC batch 11 (reram-eda image, repository at /w), 11 October 2026: final sign-off runs on 32 cores.
#  1. ChipFoundry's precheck on chip/sky130/caravan (all checks, optional Magic DRC included), with CVC built from source
#     (the LVS and OEB checks run it) and KLayout installed.
#  2. Magic antenna check of the final GDS.
#  3. Mutation test of TCIM0, both trit codes (pack made by tb/mutation_remote.py gen in the sandbox).
#  4. Formal proofs again (SymbiYosys from OSS CAD Suite), in parallel, then the injected faults that must make them fail.
cd /w
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq > /dev/null 2>&1
apt-get install -y -qq gawk gettext autopoint bison flex autoconf automake libtool pkg-config > /tmp/apt.log 2>&1 || tail -5 /tmp/apt.log
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
echo "=== mutation"
cd /w/flow/eda && rm -rf mutpack11 && tar xzf mutpack11.tgz && python3 mutpack11/mutation_remote.py run mutpack11 30 > mutation11.log 2>&1
tail -5 mutation11.log; ls mutpack11/*.json
echo "=== formal"
cd /w/formal
yosys -q -p "read_slang --help" > /dev/null 2>&1 || {
  echo "read_slang needs the plugin: loading it in copies of the .sby files"
  for f in tcim_spi.sby tcim_core.sby; do sed -i "s/^\[script\]$/[script]\nplugin -i slang/" $f; done; }
( sby -f tcim_spi.sby > /tmp/f_spi.log 2>&1 & sby -f tcim_core.sby safety > /tmp/f_safety.log 2>&1 & \
  sby -f tcim_core.sby safety_pnx > /tmp/f_pnx.log 2>&1 & sby -f tcim_core.sby progress > /tmp/f_prog.log 2>&1 & wait )
cat /tmp/f_spi.log /tmp/f_safety.log /tmp/f_pnx.log /tmp/f_prog.log > /w/flow/eda/formal11.log
grep "DONE" /w/flow/eda/formal11.log
cd /w && SBY=sby python3 formal/check_faults.py > /w/flow/eda/formal_faults11.log 2>&1; tail -12 /w/flow/eda/formal_faults11.log
cd /w/formal && git status > /dev/null 2>&1; for f in tcim_spi.sby tcim_core.sby; do sed -i '/^plugin -i slang$/d' $f; done
echo BATCH11_DONE
