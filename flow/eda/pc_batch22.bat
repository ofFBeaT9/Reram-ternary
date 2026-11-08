@echo off
cd /d "%~dp0..\.."
docker run --rm -v "%CD%":/w reram-eda bash /w/flow/eda/pc_batch22.sh > flow\eda\pc_batch22.log 2>&1
