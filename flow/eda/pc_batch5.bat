@echo off
rem PC batch 5: sky130B place and route, resumed after the platform copy fix (rcx rules), with export.
cd /d "%~dp0..\.."
docker run --rm -v "%CD%":/w openroad/orfs:26Q4-71-g9b26ff8ff bash /w/flow/orfs/sky130b_platform.sh > flow\orfs\sky130b_2.log 2>&1
echo done > flow\eda\pc_batch5.log
