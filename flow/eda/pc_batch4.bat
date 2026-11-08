@echo off
rem PC batch 4: Tang Nano 9K bitstream with the PLL clock (reram-eda), DRC/LVS of the corrected IHP cells (ORFS).
cd /d "%~dp0..\.."
docker run --rm -v "%CD%":/w reram-eda bash /w/rtl/fpga/pnr_fpga.sh > rtl\fpga\pnr_fpga.log 2>&1
echo fpga done > flow\eda\pc_batch4.log
docker run --rm -v "%CD%\layout":/w -w /w openroad/orfs:26Q4-71-g9b26ff8ff bash /w/ihp_checks.sh > layout\ihp_checks.log 2>&1
echo ihp checks done >> flow\eda\pc_batch4.log
