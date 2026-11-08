@echo off
rem PC batch 1: bitstream + PDK/tool export (reram-eda image), then the reset-gate transfer of the SkyWater fit
rem (ORFS image, which has numpy). Logs: flow\eda\pc_batch1.log, results\fit_skywater_transfer.log
cd /d "%~dp0..\.."
docker run --rm -v "%CD%":/w reram-eda bash /w/flow/eda/pc_batch1.sh > flow\eda\pc_batch1.log 2>&1
echo done >> flow\eda\pc_batch1.log
docker run --rm -v "%CD%":/w -w /w openroad/orfs:26Q4-71-g9b26ff8ff bash -c "python3 model/fit_skywater.py transfer 200" > results\fit_skywater_transfer.log 2>&1
echo done >> results\fit_skywater_transfer.log
