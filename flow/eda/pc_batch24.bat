@echo off
cd /d "%~dp0..\.."
start "formal24" /min cmd /c flow\eda\pc_batch24f.bat
docker run --rm -v "%CD%":/w reram-eda bash /w/flow/eda/pc_batch24.sh > flow\eda\pc_batch24.log 2>&1
