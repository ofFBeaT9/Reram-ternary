@echo off
REM Place and route, DRC and LVS of the TCIM0 logic on both platforms, then a small export for the cloud session.
REM   usage: run_full.bat <work folder>     e.g.  run_full.bat out42      (Docker Desktop running)
REM Work folder: <work folder>\ ; console logs: <work folder>\<platform>.log ;
REM export: export\<work folder>_<platform>.tgz (logs, reports, 6_final.v/.sdc/.spef, DRC count)
setlocal
set IMAGE=openroad/orfs:26Q4-71-g9b26ff8ff
set OUT=%1
if "%OUT%"=="" set OUT=out
cd /d "%~dp0"
if not exist %OUT% mkdir %OUT%
if not exist export mkdir export
for %%P in (ihp-sg13g2 sky130hd) do (
  echo === %%P start > %OUT%\%%P.log
  docker run --rm -v "%~dp0.":/design -w /OpenROAD-flow-scripts/flow %IMAGE% bash -lc "source ../env.sh >/dev/null 2>&1; M='make DESIGN_CONFIG=/design/%%P/config.mk WORK_HOME=/design/%OUT%'; $M && echo '=== drc' && $M drc; echo '=== lvs'; $M lvs; cd /design/%OUT% && tar czf /design/export/%OUT%_%%P.tgz logs/%%P reports/%%P results/%%P/tcim_top/base/6_final.v results/%%P/tcim_top/base/6_final.sdc results/%%P/tcim_top/base/6_final.spef && echo '=== exported'" >> %OUT%\%%P.log 2>&1
  echo === %%P end >> %OUT%\%%P.log
)
endlocal
