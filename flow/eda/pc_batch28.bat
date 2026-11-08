@echo off
cd /d "%~dp0..\.."
start "formal28" /min cmd /c flow\eda\pc_batch28f.bat
docker run --rm -v "%CD%":/w openroad/orfs:26Q4-71-g9b26ff8ff bash /w/flow/eda/pc_batch28_pnr.sh > flow\eda\pc_batch28_pnr.log 2>&1
docker run --rm -v "%CD%":/w reram-eda bash /w/flow/eda/pc_batch28_post.sh > flow\eda\pc_batch28_post.log 2>&1
