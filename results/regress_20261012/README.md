# Fresh regression of 12 October 2026

A copy of the repository was taken and twelve suites were run again from scratch (`run.sh`; `resume.sh` finished the last
three after the background job reached its time limit during fault 23 of `tb/chip/mutation_chip.py`). `summary.txt` has the
exit code and duration of each step, `logs/` the output of each, `summary.json` the parsed results and the comparison of every
result file the suites rewrote with the stored copy (21 identical byte for byte, 6 identical apart from run times, 0 different).
Summarized in docs/STATUS.md, section 12.
