@echo off
cd /d "%~dp0..\.."
docker run --rm -v "%CD%":/w reram-eda bash /w/flow/eda/pc_batch29b.sh > flow\eda\pc_batch29b.log 2>&1
