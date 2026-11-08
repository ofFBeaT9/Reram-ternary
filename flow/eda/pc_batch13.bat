@echo off
cd /d "%~dp0..\.."
docker run --rm -v "%CD%":/w openroad/orfs:26Q4-71-g9b26ff8ff bash /w/flow/eda/pc_batch13_orfs.sh > flow\eda\pc_batch13_orfs.log 2>&1
docker run --rm -v "%CD%":/w reram-eda bash /w/flow/eda/pc_batch13.sh > flow\eda\pc_batch13.log 2>&1
