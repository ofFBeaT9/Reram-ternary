#!/bin/bash
# Resume of run.sh after the background job hit its time limit during fault 23 of mutation_chip (12 October 2026).
cd "$(dirname "$0")/reram-ternary"; L=../logs; S=../summary.txt
source env_sandbox.sh
step(){ n=$1; shift; t0=$(date +%s); ( "$@" ) > $L/$n.log 2>&1; rc=$?; echo "$n rc=$rc $(( $(date +%s)-t0 ))s" >> $S; }
step mutation_chip_23_25 python3 tb/chip/mutation_chip.py 23 25
step fpga bash tb/fpga/run_fpga_checks.sh
step check_model make check-model
echo DONE >> $S
