@echo off
cd /d "%~dp0..\.."
start "precheck24" /min cmd /c flow\eda\pc_batch24p.bat
docker run --rm -v "%CD%":/w reram-eda bash /w/flow/eda/pc_batch26.sh > flow\eda\pc_batch26.log 2>&1
