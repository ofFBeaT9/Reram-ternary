@echo off
cd /d "%~dp0..\.."
docker run --rm -v "%CD%":/w reram-eda bash /w/flow/eda/pc_batch8.sh > flow\eda\pc_batch8.log 2>&1
