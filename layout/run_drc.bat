@echo off
rem DRC of layout\tcim_2t2r_block.gds with the IHP SG13G2 KLayout deck (copied from IHP-Open-PDK 5e6d592e),
rem in the OpenROAD-flow-scripts image, which has the KLayout application. Density rules are excluded.
set IMAGE=openroad/orfs:26Q4-71-g9b26ff8ff
cd /d "%~dp0"
docker run --rm -v "%~dp0.":/w -w /w %IMAGE% bash -lc "mkdir -p /tmp/k && tar xzf drc_deck.tgz -C /tmp/k && (python3 -c 'import klayout.db' 2>/dev/null && echo klayout-python-module-present || echo using-stub); export PYTHONPATH=/w/drc_stub; python3 -c 'import klayout.db' 2>/dev/null; klayout -v; cd /tmp/k/IHP-Open-PDK/ihp-sg13g2/libs.tech/klayout/tech/drc && python3 run_drc.py --path=/w/tcim_2t2r_block.gds --topcell=tcim_2t2r_block --run_dir=/w/drc_out --no_density --mp=4; ls -la /w/drc_out" > drc.log 2>&1
echo done >> drc.log
