@echo off
REM Place and route of the TCIM0 logic on both platforms, one after the other, with logs.
REM   usage: run_all.bat            (Docker Desktop running; image openroad/orfs pinned below)
REM Results, reports and logs: out\ ; console output: out\<platform>.log
setlocal
set IMAGE=openroad/orfs:26Q4-71-g9b26ff8ff
cd /d "%~dp0"
if not exist out mkdir out
for %%P in (ihp-sg13g2 sky130hd) do (
  echo === %%P start > out\%%P.log
  docker run --rm -v "%~dp0.":/design -w /OpenROAD-flow-scripts/flow %IMAGE% bash -lc "source ../env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/design/%%P/config.mk WORK_HOME=/design/out" >> out\%%P.log 2>&1
  echo === %%P end >> out\%%P.log
)
endlocal
