#!/bin/bash
# Fresh regression on a copy of the repository (12 October 2026). Each step's log goes to logs/; summary to summary.txt.
cd "$(dirname "$0")/reram-ternary"; L=../logs; mkdir -p $L; S=../summary.txt; : > $S
source env_sandbox.sh
step(){ n=$1; shift; t0=$(date +%s); ( "$@" ) > $L/$n.log 2>&1; rc=$?; echo "$n rc=$rc $(( $(date +%s)-t0 ))s" >> $S; }
step test make test
step lint make lint
step equiv make equiv
step equiv_chip make equiv-chip
step rtl make rtl
step rtl_pnx make rtl-pnx
step rtl_verilator make rtl-verilator
step rtl_chip make rtl-chip
step rtl_chip_verilator make rtl-chip-verilator
step mutation_chip python3 tb/chip/mutation_chip.py
step fpga bash tb/fpga/run_fpga_checks.sh
step check_model make check-model
echo DONE >> $S
