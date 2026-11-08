#!/bin/bash
# Local mirror of ChipFoundry's ciel PDK release sky130-3e0e31d (6 November 2026). The PC's network timed out on
# chipfoundry.github.io during batch 24, so the release's .tar.zst assets are downloaded from github.com/chipfoundry/
# ciel-releases and served to ciel by a local web server inside the precheck container (pc_batch24.sh).
# usage: tools/cf_pdk_mirror.sh <out dir>      -> <out dir>/files/*.tar.zst, SHA256SUMS, sky130/manifest.json, ...
set -e
O=${1:?out dir}; V=3e0e31dcce8519a7dbb82590346db16d91b7244f; T=sky130-$V
mkdir -p $O/files $O/sky130/$V
N="common sky130_fd_io sky130_fd_pr sky130_fd_sc_hd sky130_fd_sc_hvl sky130_ml_xx_hd sky130_sram_macros sky130_fd_pr_reram"
for a in $N; do curl -sfL -o $O/files/$a.tar.zst "https://github.com/chipfoundry/ciel-releases/releases/download/$T/$a.tar.zst"; done
(cd $O/files && sha256sum *.tar.zst > SHA256SUMS)
python3 - $O $V $N <<'PY'
import json, sys
O, V, names = sys.argv[1], sys.argv[2], sys.argv[3:]
json.dump({"pdk": "sky130", "note": "local mirror of ciel release sky130-" + V + "; the date field is a placeholder",
           "versions": [{"version": V, "date": "2000-01-01T00:00:00Z"}]}, open(f"{O}/sky130/manifest.json", "w"), indent=1)
json.dump({"assets": [{"content": n, "filename": n + ".tar.zst", "url": f"http://127.0.0.1:8765/files/{n}.tar.zst"} for n in names]},
          open(f"{O}/sky130/{V}/manifest.json", "w"), indent=1)
PY
# use: (cd <out dir> && python3 -m http.server 8765 --bind 127.0.0.1 &); NO_PROXY=127.0.0.1 CIEL_DATA_SOURCE=static-web:http://127.0.0.1:8765 \
#      ciel enable 3e0e31dcce8519a7dbb82590346db16d91b7244f --pdk-family sky130 --pdk-root <pdk root>
