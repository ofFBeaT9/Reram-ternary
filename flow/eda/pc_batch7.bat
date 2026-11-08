@echo off
cd /d "%~dp0..\.."
docker run --rm -v "%CD%":/w openroad/orfs:26Q4-71-g9b26ff8ff bash /w/flow/eda/pc_batch7.sh > flow\eda\pc_batch7.log 2>&1
