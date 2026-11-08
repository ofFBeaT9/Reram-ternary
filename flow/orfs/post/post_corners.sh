#!/bin/bash
# Timing of a routed platform at every library corner, and with the extracted parasitics scaled by 0.8 and 1.2.
#   usage: post_corners.sh <platform> <work dir> <lib dir>
#     platform  ihp-sg13g2 | sky130hd
#     work dir  the unpacked export (results/<platform>/tcim_top/base/6_final.{v,sdc,spef}); reports are written there:
#               post_<corner>.rpt and post_k<k>_<corner>.rpt
#     lib dir   ihp-sg13g2: .../libs.ref/sg13g2_stdcell/lib ; sky130hd: the folder made by tools/make_sky130_corner_libs.sh
# OpenSTA (sta) must be on the path.
set -e
P=$1; W=$(realpath "$2"); L=$(realpath "$3"); D=$(cd "$(dirname "$0")" && pwd)
B=$W/results/$P/${DESIGN:-tcim_top}/base        # DESIGN=tcim_chip_digital for the digital block of the SKY130 chip
case $P in
  ihp-sg13g2) C="typ_1p20V_25C slow_1p08V_125C fast_1p32V_m40C"; F=sg13g2_stdcell_%s.lib ;;
  sky130hd)   C="tt_025C_1v80 ss_100C_1v60 ff_n40C_1v95";       F=sky130_fd_sc_hd__%s.lib ;;
  *) echo "unknown platform $P"; exit 1 ;;
esac
for c in $C; do
  POST_LIB=$L/$(printf $F $c) POST_DIR=$B sta -no_init -exit $D/sta_post.tcl > $W/post_$c.rpt
  echo "$c: $(grep -E '^@@ (setup_wns|setup_tns|hold_wns)' $W/post_$c.rpt | tr '\n' ' ')"
done
for k in 0.8 1.2; do
  S=$W/spef_k$k; mkdir -p $S
  cp $B/6_final.v $B/6_final.sdc $S/
  python3 $D/spef_scale.py $B/6_final.spef $S/6_final.spef $k
  for c in $C; do
    POST_LIB=$L/$(printf $F $c) POST_DIR=$S sta -no_init -exit $D/sta_post.tcl > $W/post_k${k}_$c.rpt
    echo "k=$k $c: $(grep -E '^@@ (setup_wns|setup_tns|hold_wns)' $W/post_k${k}_$c.rpt | tr '\n' ' ')"
  done
done
