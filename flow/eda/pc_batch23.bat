@echo off
cd /d "%~dp0..\.."
docker run --rm -v "%CD%":/w openroad/orfs:26Q4-71-g9b26ff8ff bash /w/flow/eda/pc_batch23.sh > flow\eda\pc_batch23.log 2>&1
docker run --rm -v "%CD%":/w reram-eda bash /w/flow/eda/pc_batch23_fpga.sh > flow\eda\pc_batch23_fpga.log 2>&1
echo BATCH23_BAT_DONE >> flow\eda\pc_batch23_fpga.log
