@echo off
cd /d "%~dp0..\.."
docker run --rm -v "%CD%":/w reram-eda bash /w/flow/eda/pc_batch28b_formal.sh > flow\eda\pc_batch28b_formal.log 2>&1
