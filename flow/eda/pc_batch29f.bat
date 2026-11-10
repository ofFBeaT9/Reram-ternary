@echo off
cd /d "%~dp0..\.."
docker run --rm -v "%CD%":/w reram-eda bash /w/flow/eda/pc_batch29f.sh > flow\eda\pc_batch29f.log 2>&1
