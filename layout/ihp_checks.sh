#!/bin/bash
# DRC and LVS of the revision 4.4 IHP cells with the SG13G2 KLayout decks (same decks and image as periph_checks.sh):
#   tcim_form   (layout/tcim_form.gds, tcim_form.cdl)     forming switch
#   tcim_wld72  (layout/tcim_wld72.gds, tcim_wld72.cdl)   pitch-matched word-line driver column, 72 rows
# Each LVS is also run against a netlist with one deliberate change, which must fail. Also writes the extracted
# netlists (for the re-simulation). Output: ihp_checks/<cell>_*.log and run folders.
cd "$(dirname "$0")"; W=$(pwd); O=$W/ihp_checks; mkdir -p $O /tmp/k
tar xzf drc_deck.tgz -C /tmp/k; tar xzf lvs_deck.tgz -C /tmp/k
python3 -c 'import klayout.db' 2>/dev/null || export PYTHONPATH=$W/drc_stub
klayout -b -v
T=/tmp/k/IHP-Open-PDK/ihp-sg13g2/libs.tech/klayout/tech
sed 's/^M10 m ya vform vform sg13_hv_pmos w=20u/M10 m ya vform vform sg13_hv_pmos w=16u/' tcim_form.cdl > $O/fault_form.cdl
sed 's/^M5 out3 in3 vss vss/M5 out3 in2 vss vss/' tcim_wld72.cdl > $O/fault_wld72.cdl
for c in tcim_form tcim_wld72; do
  (cd $T/drc && python3 run_drc.py --path=$W/$c.gds --topcell=$c --run_dir=$O/drc_$c --no_density --mp=8) > $O/${c}_drc.log 2>&1
  echo "$c DRC: $(grep -E 'Passed|violations|Failed' $O/${c}_drc.log | tail -1)"
  (cd $T/lvs && python3 run_lvs.py --layout=$W/$c.gds --netlist=$W/$c.cdl --topcell=$c --run_dir=$O/lvs_$c) > $O/${c}_lvs.log 2>&1
  echo "$c LVS: $(grep -E Outcome $O/${c}_lvs.log | tail -1)"
  f=$O/fault_${c#tcim_}.cdl
  cmp -s $f $c.cdl && echo "$c FAULT NOT INSERTED"
  (cd $T/lvs && python3 run_lvs.py --layout=$W/$c.gds --netlist=$f --topcell=$c --run_dir=$O/lvs_fault_$c) > $O/${c}_lvs_fault.log 2>&1
  echo "$c LVS with fault: $(grep -E 'Outcome' $O/${c}_lvs_fault.log | tail -1)"
done
ls $O/lvs_tcim_wld72 | head
