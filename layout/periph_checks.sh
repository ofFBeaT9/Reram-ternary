#!/bin/bash
# DRC and LVS of layout/tcim_periphery.gds (cells tcim_ls and tcim_wld) with the IHP SG13G2 KLayout decks
# (IHP-Open-PDK 5e6d592e, packed in drc_deck.tgz and lvs_deck.tgz). Runs inside openroad/orfs:26Q4-71-g9b26ff8ff
# (KLayout application; its Python module is replaced by drc_stub, which is enough when --topcell is given).
# Output: periph_checks/<cell>_drc.log, <cell>_lvs.log and the run folders.
cd "$(dirname "$0")"; W=$(pwd); O=$W/periph_checks; mkdir -p $O /tmp/k
tar xzf drc_deck.tgz -C /tmp/k; tar xzf lvs_deck.tgz -C /tmp/k
python3 -c 'import klayout.db' 2>/dev/null || export PYTHONPATH=$W/drc_stub
klayout -b -v
T=/tmp/k/IHP-Open-PDK/ihp-sg13g2/libs.tech/klayout/tech
for c in tcim_ls tcim_wld; do
  (cd $T/drc && python3 run_drc.py --path=$W/tcim_periphery.gds --topcell=$c --run_dir=$O/drc_$c --no_density --mp=4) > $O/${c}_drc.log 2>&1
  echo "$c DRC: $(grep -E 'Passed|violations|Failed' $O/${c}_drc.log | tail -1)"
  (cd $T/lvs && python3 run_lvs.py --layout=$W/tcim_periphery.gds --netlist=$W/periphery_cells.cdl --topcell=$c --run_dir=$O/lvs_$c) > $O/${c}_lvs.log 2>&1
  echo "$c LVS: $(grep -E Outcome $O/${c}_lvs.log | tail -1)"
done
# The comparison must be able to fail: the same layout against netlists with one deliberate change each
# (tcim_ls: gate of M5 moved from xb to x; tcim_wld: PMOS width 12 um -> 10 um). Both must report a mismatch.
sed 's/^M5 x xb vddh/M5 x x vddh/' periphery_cells.cdl > $O/fault_ls.cdl
sed 's/^M1 out in vr vr sg13_hv_pmos w=12u/M1 out in vr vr sg13_hv_pmos w=10u/' periphery_cells.cdl > $O/fault_wld.cdl
for c in tcim_ls tcim_wld; do
  f=$O/fault_${c#tcim_}.cdl
  cmp -s $f periphery_cells.cdl && echo "$c FAULT NOT INSERTED"
  (cd $T/lvs && python3 run_lvs.py --layout=$W/tcim_periphery.gds --netlist=$f --topcell=$c --run_dir=$O/lvs_fault_$c) > $O/${c}_lvs_fault.log 2>&1
  echo "$c LVS with fault: $(grep -E 'Outcome' $O/${c}_lvs_fault.log | tail -1)"
done
