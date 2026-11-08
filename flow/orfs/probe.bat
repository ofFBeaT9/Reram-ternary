@echo off
REM Probe: is Docker reachable, which images exist, and how the OpenROAD-flow-scripts image is laid out.
REM Output goes to probe.log next to this file. Safe to run more than once.
cd /d "%~dp0"
echo === %date% %time% > probe.log
docker version >> probe.log 2>&1
docker images >> probe.log 2>&1
docker run --rm openroad/orfs:26Q4-71-g9b26ff8ff bash -lc "pwd; ls /; ls /OpenROAD-flow-scripts; ls /OpenROAD-flow-scripts/flow | head -40; which openroad yosys klayout iverilog verilator; openroad -version; yosys -V; nproc; free -g" >> probe.log 2>&1
echo === done >> probe.log
