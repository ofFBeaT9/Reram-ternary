@echo off
rem PC batch 3: sky130_fd_pr SPICE models export (reram-eda image), then place and route of TCIM0 on sky130B at the
rem slow corner (ORFS image). Logs: flow\eda\pc_batch3.log, flow\orfs\sky130b.log
cd /d "%~dp0..\.."
docker run --rm -v "%CD%":/w reram-eda bash -c "tar czf /w/export/pdk_fdpr_spice.tgz -C /opt/pdk sky130B/libs.ref/sky130_fd_pr/spice && ls -l /w/export" > flow\eda\pc_batch3.log 2>&1
docker run --rm -v "%CD%":/w openroad/orfs:26Q4-71-g9b26ff8ff bash /w/flow/orfs/sky130b_platform.sh > flow\orfs\sky130b.log 2>&1
echo done >> flow\eda\pc_batch3.log
docker run --rm -v "%CD%":/w -w /w openroad/orfs:26Q4-71-g9b26ff8ff bash -c "python3 model/fit_skywater.py transfer 200" > results\fit_skywater_transfer.log 2>&1
echo transfer done >> flow\eda\pc_batch3.log
