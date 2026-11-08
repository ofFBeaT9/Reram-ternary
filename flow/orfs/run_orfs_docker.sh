#!/bin/bash
# Place and route of the TCIM0 digital block with OpenROAD-flow-scripts in Docker (Linux, WSL or macOS).
#   usage: flow/orfs/run_orfs_docker.sh [ihp-sg13g2 | sky130hd]
# Uses the flow scripts and platforms inside the image. Results, logs and reports go to flow/orfs/out/.
set -e
PLATFORM=${1:-ihp-sg13g2}
HERE=$(cd "$(dirname "$0")" && pwd)
docker run --rm -v "$HERE":/design -w /OpenROAD-flow-scripts/flow openroad/orfs:26Q4-71-g9b26ff8ff \
  bash -lc "source ../env.sh 2>/dev/null; make DESIGN_CONFIG=/design/$PLATFORM/config.mk WORK_HOME=/design/out"
