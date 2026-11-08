@echo off
REM Design-rule and layout-versus-schematic checks of the routed TCIM0 block on both platforms (after run_all.bat).
REM Logs: out\checks_<platform>.log ; reports under out\reports\<platform>\tcim_top\base\
setlocal
set IMAGE=openroad/orfs:26Q4-71-g9b26ff8ff
cd /d "%~dp0"
for %%P in (ihp-sg13g2 sky130hd) do (
  echo === %%P drc > out\checks_%%P.log
  docker run --rm -v "%~dp0.":/design -w /OpenROAD-flow-scripts/flow %IMAGE% bash -lc "source ../env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/design/%%P/config.mk WORK_HOME=/design/out drc" >> out\checks_%%P.log 2>&1
  echo === %%P lvs >> out\checks_%%P.log
  docker run --rm -v "%~dp0.":/design -w /OpenROAD-flow-scripts/flow %IMAGE% bash -lc "source ../env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/design/%%P/config.mk WORK_HOME=/design/out lvs" >> out\checks_%%P.log 2>&1
  echo === %%P end >> out\checks_%%P.log
)
endlocal
