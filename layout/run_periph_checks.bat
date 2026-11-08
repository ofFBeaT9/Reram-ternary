@echo off
rem DRC and LVS of layout\tcim_periphery.gds in the OpenROAD-flow-scripts image (Docker Desktop running).
rem Summary in periph_checks.log, details in periph_checks\.
set IMAGE=openroad/orfs:26Q4-71-g9b26ff8ff
cd /d "%~dp0"
docker run --rm -v "%~dp0.":/w -w /w %IMAGE% bash /w/periph_checks.sh > periph_checks.log 2>&1
echo done >> periph_checks.log
