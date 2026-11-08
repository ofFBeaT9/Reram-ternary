@echo off
rem Tang Nano 9K bitstream (nextpnr + gowin_pack) in the reram-eda image. Log: rtl\fpga\pnr_fpga.log
cd /d "%~dp0..\.."
docker run --rm -v "%CD%":/w reram-eda bash /w/rtl/fpga/pnr_fpga.sh > rtl\fpga\pnr_fpga.log 2>&1
echo done >> rtl\fpga\pnr_fpga.log
