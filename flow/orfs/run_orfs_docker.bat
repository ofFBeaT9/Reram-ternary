@echo off
REM Place and route of the TCIM0 digital block with OpenROAD-flow-scripts in Docker.
REM   usage: run_orfs_docker.bat [ihp-sg13g2 | sky130hd]
REM Uses the flow scripts and platforms inside the image, so nothing outside this folder is written.
REM Results, logs and reports go to flow\orfs\out\ . Docker Desktop must be running.
setlocal
set PLATFORM=%1
if "%PLATFORM%"=="" set PLATFORM=ihp-sg13g2
set HERE=%~dp0
set HERE=%HERE:~0,-1%
docker run --rm -v "%HERE%":/design -w /OpenROAD-flow-scripts/flow openroad/orfs:26Q4-71-g9b26ff8ff bash -lc "source ../env.sh 2>/dev/null; make DESIGN_CONFIG=/design/%PLATFORM%/config.mk WORK_HOME=/design/out"
endlocal
