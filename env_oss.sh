# Tool paths with YosysHQ's OSS CAD Suite 2026-10-09 (the release in the PC's reram-eda image), used from 6 November 2026
# after the cloud sandbox's own builds were lost. yosys is wrapped to load the slang front end (-m slang).
OSS=${OSS:-/home/claude/opt/oss-cad-suite}
export PATH=/home/claude/bin:$OSS/bin:$PATH
export VERILATOR_ROOT=$OSS/share/verilator SBY=sby
