# FPGA demonstration: what the evidence is, how strong it is, and how to make it publication-grade

12 October 2026. TCIM0's logic on a Sipeed Tang Nano 9K (Gowin GW1NR-9) with an **emulated** ReRAM array, driven from a PC
over the board's USB serial port. Runs on the board on 10 October 2026.

## 1. What the claim is, and what it is not

- **Claim:** the TCIM0 logic (register file, product sequencer, pulse-and-verify programming sequencer, read-back,
  serial protocol) works on real hardware at 13.5 MHz against an array that misbehaves the way devices do: with the
  published device spread every one of 1,728 weights is programmed and read back correctly and every one of 100 random
  digital products equals the exact dot product; with 2× and 3× the spread the sequencer flags the rows it cannot
  program (WERR) instead of computing silently with wrong weights.
- **Not claimed:** anything about ReRAM devices. The array is a block in the FPGA whose devices take pulse thresholds
  from the device model's Monte Carlo and conductance levels from IHP's published distributions (rtl/fpga/arr_emu.sv).

## 2. What exists (files in this repository)

| Item | File | SHA-256 (first 16 hex) |
|---|---|---|
| Bitstream loaded on the board | `rtl/fpga/build/tcim_fpga.fs` (3,556,680 bytes) | daecc0b3afd94bc1 (full value in `results/fpga/bitstream_sha256.txt`; re-hashed 12 Oct: identical) |
| Board run, published spread | `results/fpga/board_bank0.json` (+ PowerShell capture `board_bank0.log`) | ebb4c4b62393774b |
| Board run, 2× spread | `results/fpga/board_bank1.json` | 98e50614b57a9011 |
| Board run, 3× spread | `results/fpga/board_bank2.json` | 02255fa07e559975 |
| Board, directed cases with all 72 × 24 weights and every returned column | `results/fpga/board_debug.json` | a51a6fff72591a55 |
| First bitstream (signed-multiplier fault), summary and directed cases | `results/fpga/board_v1_signed_mult_bank0.json`, `board_v1_signed_mult_debug.json` | 2534c1b0b21cb416 |
| Place and route report (device use, clock) | `results/fpga/nextpnr_report.json`, `nextpnr.log` | d3e0350a74a9278b |
| Same design in simulation (RTL and gate level) | `results/fpga/sim_bank0/1/2.json`, `gls_bank0.json`, `gls_vs_rtl.json` | — |
| Sources | `rtl/tcim_core.sv`, `rtl/fpga/*.sv`, host `tools/fpga_host.py`, `tools/fpga_debug.py` | — |

Re-checked on 12 October 2026 from the stored files: in `board_debug.json` every "exact" column equals the dot product
recomputed from the stored weights and the case's input, and every digital column equals it (6 of 6 cases; the analog
columns differ by at most 1). In `board_v1_signed_mult_debug.json` the digital columns are exact and the analog ones are
off by up to 364, the fault the board found.

## 3. How strong it is (an editor's reading)

**Supports the claim:**
- A fixed, hashed bitstream built from the sources in this repository with open tools (Yosys, nextpnr, gowin_pack).
- The board results differ from the simulation results the way independent random draws do (e.g. 378 vs 214 wrong
  weights at 2× spread), while the deterministic parts agree (digital products exact at 1×).
- The board found a fault that every simulation missed (the first bitstream's signed hard multiplier), and the fix was
  confirmed on the board: that is hard to explain without real hardware runs.
- The directed-case file holds the full weight matrix and every returned column, so its arithmetic can be re-checked.

**Weaknesses a journal editor would raise:**
1. The random-run files hold **summaries** (counts), not the individual products; the inputs and returned results of the
   200 random products per run (100 per mode) were not stored.
2. No **byte-level transcript** of the serial line and no timestamps inside the files; the files are written by our own
   host program.
3. No record that identifies the **board** (JTAG IDCODE) or of the bitstream **load** (openFPGALoader output).
4. No **photo or video** of the run, and no run by anyone outside the project.
5. The repository is not under version control, so there is no commit to point to; the exact source state is fixed
   only by the bitstream hash.

So: good engineering evidence, not yet publication-grade proof.

## 4. Protocol for a publication-grade re-run (about 15 minutes on the PC)

Tools added on 12 October 2026: `tools/fpga_host.py --transcript FILE --bitstream FILE` records every byte sent and received
with times, the start time (UTC), the host, the bitstream's SHA-256 and the SHA-256 of the RTL sources;
`tools/fpga_verify.py FILE` re-derives every result from the bytes alone (it decodes the register protocol itself and
does not use the host program) and checks the host's summary against it. Both were tested on the Verilator model of
the same design (section 5).

1. Start a screen recording, and point a phone camera at the board (its LEDs show activity).
2. `openFPGALoader --detect` (records the FPGA's IDCODE) and save the output.
3. `certutil -hashfile rtl\fpga\build\tcim_fpga.fs SHA256` (Windows) and check it is daecc0b3…a7ea.
4. `openFPGALoader -b tangnano9k rtl\fpga\build\tcim_fpga.fs` (loads into SRAM) and save the output.
5. For each spread bank b = 0, 1, 2, with a seed chosen at the time (for example the current time):
   `python tools\fpga_host.py --port COMx --bank b --noise 1 --products 100 --seed S --bitstream rtl\fpga\build\tcim_fpga.fs --transcript evidence\fpga_b_S.jsonl --json evidence\fpga_b_S.json`
6. `python tools\fpga_verify.py evidence\fpga_b_S.jsonl --json evidence\fpga_b_S.verify.json` for each run: verdict must be "consistent".
7. Hash every file in `evidence\` and keep the list with the video. An outside reader can repeat steps 6 and the hash check
   without the board; with a Tang Nano 9K they can repeat steps 2 to 6.

## 5. Check of the new tools on the simulation model

See `results/fpga/transcript_sim_check.json` (written on 12 October 2026): a full run of `fpga_host.py --transcript` on the
Verilator model of the FPGA design, and `fpga_verify.py` on its transcript.
