#!/bin/sh
# PAPER.md and BOS_BRIEF.md -> PDF (pandoc + xelatex). Run in this folder.
set -e
for f in PAPER BOS_BRIEF; do
  pandoc $f.md -o $f.pdf --pdf-engine=xelatex -V geometry:a4paper,margin=2cm -V fontsize=10pt \
    -V mainfont="${MAINFONT:-DejaVu Serif}" -V monofont="DejaVu Sans Mono" -V monofontoptions=Scale=0.8 \
    -V colorlinks=true -V linkcolor=black -V urlcolor=blue \
    -H header.tex
done
