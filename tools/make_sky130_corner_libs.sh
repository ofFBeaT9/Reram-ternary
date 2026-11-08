#!/bin/bash
# SkyWater SKY130 sky130_fd_sc_hd Liberty files for the slow and fast corners (the ORFS sky130hd platform ships only
# the typical one). Generated from the cell library's own timing data (JSON) with SkyWater's generator.
#   usage: tools/make_sky130_corner_libs.sh <work folder>    -> <work folder>/libs/sky130_fd_sc_hd__{ss_100C_1v60,ff_n40C_1v95,tt_025C_1v80}.lib
# Check used on 9 October 2026: the generated tt_025C_1v80 file gives the same post-route slack, to the last digit,
# as the typical file of the ORFS platform (setup 1.850 ns, hold 0.350 ns on the revision 4.2 layout).
# Commits used: google/skywater-pdk-libs-sky130_fd_sc_hd ac7fb61f06e6, google/skywater-pdk 7198cf647113.
set -e
W=$(realpath -m "${1:?work folder}"); mkdir -p "$W/libs" "$W/stub/dataclasses_json"
[ -d "$W/schd" ] || { git clone -q --filter=blob:none https://github.com/google/skywater-pdk-libs-sky130_fd_sc_hd.git "$W/schd"; git -C "$W/schd" checkout -q ac7fb61f06e6470b94e8afdf7c25268f62fbd7b1; }
[ -d "$W/swpdk" ] || { git clone -q --filter=blob:none https://github.com/google/skywater-pdk.git "$W/swpdk"; git -C "$W/swpdk" checkout -q 7198cf647113f56041e02abf3eb623692820c5e1; }
# the generator imports dataclasses_json only for a class decorator; a stand-in avoids the package
cat > "$W/stub/dataclasses_json/__init__.py" <<'EOF'
def dataclass_json(cls=None, **kw):
    return (lambda c: c) if cls is None else cls
class LetterCase:
    CAMEL = SNAKE = KEBAB = PASCAL = None
def config(**kw):
    return {}
EOF
# liberty.py's module doctests fail on Python 3.13, so main() is called directly instead of "python -m"
cd "$W/libs"
PYTHONPATH="$W/stub:$W/swpdk/scripts/python-skywater-pdk" python3 - "$W/schd" ss_100C_1v60 ff_n40C_1v95 tt_025C_1v80 -o "$W/libs" <<'EOF'
import sys
from skywater_pdk import liberty
sys.argv = ["liberty"] + sys.argv[1:]
sys.exit(liberty.main())
EOF
ls -la "$W/libs"
