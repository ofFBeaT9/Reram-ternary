#!/bin/bash
# PC batch 27, part F (reram-eda image, /w), 6 November 2026, revision 4.7: make formal (serial port, safety, safety_pnx,
# progress, both miter tasks, then the injected faults) and the mutation test of both trit codes (pack
# flow/eda/mutpack27.tgz from tb/mutation_remote.py gen), side by side.
cd /w && source /w/flow/eda/pc_batch27_env.sh
O=/w/flow/eda/batch27; mkdir -p $O
md5sum rtl/*.sv formal/*.sv formal/*.sby formal/check_faults.py tb/tb_tcim.cc tb/mutation_test.py > $O/md5_formal_inputs.txt
( make formal > $O/formal.log 2>&1; echo "formal rc=$?" > $O/F.txt ) &
( cd /w/flow/eda && rm -rf mutpack27 && tar xzf mutpack27.tgz && nice python3 mutpack27/mutation_remote.py run mutpack27 24 > $O/mutation27.log 2>&1
  echo "mutation rc=$?" > $O/M.txt; tar czf /w/flow/eda/mutres27.tgz mutpack27/*.json ) &
wait
cat $O/F.txt $O/M.txt; grep -h DONE results/formal.log results/security/miter_*.log; tail -n 2 $O/formal.log $O/mutation27.log
echo FORMAL27_DONE
