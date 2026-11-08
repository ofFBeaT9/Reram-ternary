@echo off
rem Builds the reram-eda Docker image (magic, netgen, sky130A/B PDK, OSS CAD Suite). Log: build_eda.log
cd /d "%~dp0"
docker build -t reram-eda . > build_eda.log 2>&1
echo BUILD_EXIT %ERRORLEVEL% >> build_eda.log
docker run --rm reram-eda bash -lc "magic --version; echo quit | timeout 20 netgen -noconsole 2>&1 | head -3; cat /usr/local/magic.commit /usr/local/netgen.commit /opt/pdk.version /opt/oss-cad-suite.url; yosys -V; nextpnr-himbaechel --version; which gowin_pack openFPGALoader; ls /opt/pdk; ls /opt/pdk/sky130B/libs.tech" >> build_eda.log 2>&1
echo done >> build_eda.log
