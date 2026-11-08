@echo off
rem Copy the DRC and LVS summaries of both platforms to export\ (shallow enough to be read from the cloud session).
cd /d "%~dp0"
if not exist export mkdir export
for %%P in (ihp-sg13g2 sky130hd) do (
  copy /y out\reports\%%P\tcim_top\base\6_drc_count.rpt export\%%P_6_drc_count.rpt
  copy /y out\reports\%%P\tcim_top\base\6_drc.lyrdb export\%%P_6_drc.lyrdb
  copy /y out\results\%%P\tcim_top\base\6_lvs.lvsdb export\%%P_6_lvs.lvsdb
)
