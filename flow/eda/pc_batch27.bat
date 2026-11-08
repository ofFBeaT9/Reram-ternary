@echo off
cd /d "%~dp0..\.."
start "formal27" /min cmd /c flow\eda\pc_batch27f.bat
docker run --rm -v "%CD%":/w openroad/orfs:26Q4-71-g9b26ff8ff bash /w/flow/eda/pc_batch27_pnr.sh > flow\eda\pc_batch27_pnr.log 2>&1
docker run --rm -v "%CD%":/w reram-eda bash /w/flow/eda/pc_batch27_post.sh > flow\eda\pc_batch27_post.log 2>&1
