@echo off
rem PC batch 29 (9 November 2026), revision 4.9: verification in its own window; place and route, then the post-route checks
cd /d "%~dp0..\.."
start "verify29" /min cmd /c flow\eda\pc_batch29v.bat
docker run --rm -v "%CD%":/w openroad/orfs:26Q4-71-g9b26ff8ff bash /w/flow/eda/pc_batch29_pnr.sh > flow\eda\pc_batch29_pnr.log 2>&1
docker run --rm -v "%CD%":/w reram-eda bash /w/flow/eda/pc_batch29_post.sh > flow\eda\pc_batch29_post.log 2>&1
echo BATCH29_FINISHED > flow\eda\pc_batch29_finished.txt
