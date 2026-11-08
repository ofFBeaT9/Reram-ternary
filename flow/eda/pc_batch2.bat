@echo off
rem PC batch 2: Tang Nano 9K bitstream at 13.5 MHz (reram-eda image), DRC and LVS of the forming switch and the
rem pitch-matched word-line driver column (ORFS image, IHP KLayout decks). Logs: flow\eda\pc_batch2.log, layout\ihp_checks.log
cd /d "%~dp0..\.."
docker run --rm -v "%CD%":/w reram-eda bash /w/rtl/fpga/pnr_fpga.sh > rtl\fpga\pnr_fpga.log 2>&1
echo fpga done > flow\eda\pc_batch2.log
docker run --rm -v "%CD%\layout":/w -w /w openroad/orfs:26Q4-71-g9b26ff8ff bash /w/ihp_checks.sh > layout\ihp_checks.log 2>&1
echo ihp checks done >> flow\eda\pc_batch2.log
