@echo off
cd /d "%~dp0..\.."
docker run --rm -v "%CD%":/w reram-eda bash /w/flow/eda/pc_batch29h.sh > flow\eda\pc_batch29h.log 2>&1
