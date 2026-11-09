# Reproduce the results in results/. Tool paths come from the environment (see env_sandbox.sh).
PY      ?= python3
GC      := circuits/gnucap
PDKT    := $(IHP_GNUCAP)/tests/gnucap
CXXRTL  := $(shell yosys-config --datdir 2>/dev/null)/include/backends/cxxrtl/runtime
RTL     := rtl/tcim_pkg.sv rtl/tcim_core.sv rtl/tcim_spi.sv rtl/tcim_top.sv

.PHONY: rtl-1of3 rtl-chip rtl-chip-verilator equiv-chip signoff all check-model pdk-check cell array rtl rtl-pnx mutation mutation-pnx equiv test synth sta orfs-src sense clean \
        lint rtl-verilator formal gls post-corners layout sense-env periphery program-mc sky130-port

all: check-model rtl

# ---- device model -----------------------------------------------------------------------------------
$(GC)/plugins/reram_stanford_ihp.so: model/reram_stanford_ihp.va
	mkdir -p $(GC)/plugins && $(GC)/build_reram.sh

check-model: $(GC)/plugins/reram_stanford_ihp.so
	$(PY) model/calibrate.py
	$(PY) model/check_three_solvers.py

# ---- the PDK's own transistor reference tests (without the RF variants, which are not built here),
#      and a comparison of 16 sweeps with the PDK's ngspice reference data
pdk-check:
	$(PY) $(GC)/pdk_check.py

# ---- 1T1R cell with the real transistor ---------------------------------------------------------------
results/sg13_hv_nmos_table.npz:
	cd $(GC) && $(PY) make_mos_table.py

cell: results/sg13_hv_nmos_table.npz $(GC)/plugins/reram_stanford_ihp.so
	cd $(GC) && $(PY) exp_transistor.py
	$(PY) model/sizing_real_mos.py
	cd $(GC) && $(PY) exp_cell.py 4.5
	$(PY) model/cell_footprint.py

# ---- tile -------------------------------------------------------------------------------------------
array:
	$(PY) array/exp_analog_error.py
	$(PY) array/exp_digital_mode.py
	$(PY) array/exp_network.py
	$(PY) array/exp_energy.py
	$(PY) array/exp_pitch.py

# ---- digital ------------------------------------------------------------------------------------------
tb/build/tcim_top.h: $(RTL)
	mkdir -p tb/build
	yosys -q -p "read_slang --top tcim_top $(RTL); hierarchy -top tcim_top; proc; flatten; opt; write_cxxrtl -header -namespace cxxrtl_design tb/build/tcim_top.cc"

tb/build/tb_tcim: tb/tb_tcim.cc tb/build/tcim_top.h
	$(CXX) -std=c++14 -O1 -I tb/build -I $(CXXRTL) tb/tb_tcim.cc tb/build/tcim_top.cc -o $@

rtl: tb/build/tb_tcim tb/vectors/net_x.txt tb/build/spi_speed
	tb/build/spi_speed | tee results/spi_speed.log
	tb/build/tb_tcim tb/vectors | tee results/rtl_test.log

# the same test bench on the RTL built with the BSD-PNX trit code (the code of the REBEL group's tools)
tb/build_pnx/tcim_top.h: $(RTL)
	mkdir -p tb/build_pnx
	yosys -q -p "read_slang -D TCIM_ENC_PNX --top tcim_top $(RTL); hierarchy -top tcim_top; proc; flatten; opt; write_cxxrtl -header -namespace cxxrtl_design tb/build_pnx/tcim_top.cc"

tb/build_pnx/tb_tcim: tb/tb_tcim.cc tb/build_pnx/tcim_top.h
	$(CXX) -std=c++14 -O1 -DTCIM_ENC_PNX -I tb/build_pnx -I $(CXXRTL) tb/tb_tcim.cc tb/build_pnx/tcim_top.cc -o $@

rtl-pnx: tb/build_pnx/tb_tcim tb/vectors/net_x.txt
	tb/build_pnx/tb_tcim tb/vectors | tee results/rtl_test_pnx.log

# next-chip cell (3T3R, one-of-three; 8 November 2026): the same test bench on the build with a Z device per weight
tb/build_1of3/tcim_top.h: $(RTL)
	mkdir -p tb/build_1of3
	yosys -q -p "read_slang -D TCIM_CELL_1OF3 --top tcim_top $(RTL); hierarchy -top tcim_top; proc; flatten; opt; write_cxxrtl -header -namespace cxxrtl_design tb/build_1of3/tcim_top.cc"

tb/build_1of3/tb_tcim: tb/tb_tcim.cc tb/build_1of3/tcim_top.h
	$(CXX) -std=c++14 -O1 -DTCIM_CELL_1OF3 -I tb/build_1of3 -I $(CXXRTL) tb/tb_tcim.cc tb/build_1of3/tcim_top.cc -o $@

tb/build_1of3_pnx/tcim_top.h: $(RTL)
	mkdir -p tb/build_1of3_pnx
	yosys -q -p "read_slang -D TCIM_CELL_1OF3 -D TCIM_ENC_PNX --top tcim_top $(RTL); hierarchy -top tcim_top; proc; flatten; opt; write_cxxrtl -header -namespace cxxrtl_design tb/build_1of3_pnx/tcim_top.cc"

tb/build_1of3_pnx/tb_tcim: tb/tb_tcim.cc tb/build_1of3_pnx/tcim_top.h
	$(CXX) -std=c++14 -O1 -DTCIM_CELL_1OF3 -DTCIM_ENC_PNX -I tb/build_1of3_pnx -I $(CXXRTL) tb/tb_tcim.cc tb/build_1of3_pnx/tcim_top.cc -o $@

rtl-1of3: tb/build_1of3/tb_tcim tb/build_1of3_pnx/tb_tcim tb/vectors/net_x.txt
	tb/build_1of3/tb_tcim tb/vectors | tee results/next_chip/rtl_test_1of3.log
	tb/build_1of3_pnx/tb_tcim tb/vectors | tee results/next_chip/rtl_test_1of3_pnx.log


# how fast the serial clock may run for a host that samples MISO on the rising edge
tb/build/spi_fuzz: tb/extra/spi_fuzz.cc tb/build/tcim_top.h
	$(CXX) -std=c++14 -O2 -I tb/build -I $(CXXRTL) tb/extra/spi_fuzz.cc tb/build/tcim_top.cc -o $@

# serial-port fuzzing (revision 4.8): 200,000 random frames, four planted faults that must fail it, then 1,000,000 frames
fuzz: tb/build/spi_fuzz
	$(PY) tb/extra/spi_fuzz_faults.py 200000
	tb/build/spi_fuzz 1000000 2 | tee results/spi_fuzz_1M.log

tb/build/spi_speed: tb/extra/spi_speed.cc tb/build/tcim_top.h
	$(CXX) -std=c++14 -O1 -I tb/build -I $(CXXRTL) tb/extra/spi_speed.cc tb/build/tcim_top.cc -o $@

tb/vectors/net_x.txt:
	$(PY) tb/gen_vectors.py

# ---- mutation test: one deliberate fault at a time; every one must make the test bench fail (about an hour, two jobs)
mutation: tb/vectors/net_x.txt
	N=$$($(PY) tb/mutation_test.py count); H=$$((N / 2)); \
	$(PY) tb/mutation_test.py 0 $$((H - 1)) & $(PY) tb/mutation_test.py $$H $$((N - 1)) & wait
	$(PY) tb/mutation_merge.py

# the same faults, and the faults that only matter in that code, on the BSD-PNX build
mutation-pnx: tb/vectors/net_x.txt
	N=$$(TB_ENC=pnx $(PY) tb/mutation_test.py count); H=$$((N / 2)); \
	TB_ENC=pnx $(PY) tb/mutation_test.py 0 $$((H - 1)) & TB_ENC=pnx $(PY) tb/mutation_test.py $$H $$((N - 1)) & wait
	$(PY) tb/mutation_merge.py _pnx

# ---- formal: the conversion table equals its definition; the default-code RTL equals the RTL audited in revision 4
equiv:
	tests/equiv/run_equiv.sh

# ---- audit: independent re-derivations, and every quoted number against results/ ---------------------
test:
	$(PY) tests/test_independent.py
	$(PY) tests/test_claims.py

# ---- static timing before layout: IHP SG13G2 at three corners, both trit codes; SKY130 if SKY130_STDCELL_LIB is set
sta:
	$(PY) synth/run_sta.py

# ---- plain Verilog of the whole design for place and route (flow/orfs): no SystemVerilog front end needed there
flow/orfs/src/tcim_top.v: $(RTL)
	mkdir -p flow/orfs/src
	yosys -q -p "read_slang --top tcim_top $(RTL); hierarchy -top tcim_top; proc; flatten; memory_map; bwmuxmap; pmuxtree; opt -fast; opt_clean -purge; write_verilog -noattr flow/orfs/src/tcim_top.v"

orfs-src: flow/orfs/src/tcim_top.v

# the chip block's plain-Verilog copy for place and route (proved equal to the RTL by make equiv-chip)
CHIPRTL = $(RTL) rtl/chip/tcim_actl.sv rtl/chip/tcim_chip_core.sv rtl/chip/tcim_chip_digital.sv
flow/orfs/src/tcim_chip_digital.v: $(CHIPRTL)
	yosys -q -p "read_slang --top tcim_chip_digital $(CHIPRTL); hierarchy -top tcim_chip_digital; proc; flatten; memory_map; bwmuxmap; pmuxtree; opt -fast; opt_clean -purge; write_verilog -noattr flow/orfs/src/tcim_chip_digital.v"

chip-src: flow/orfs/src/tcim_chip_digital.v

synth:
	synth/run_synth.sh tcim_top $(RTL)
	synth/run_synth.sh tcim_core rtl/tcim_pkg.sv rtl/tcim_core.sv
	CLKGATE="sg13g2_lgcp_1 GATE:CLK:GCLK" synth/run_synth.sh tcim_top $(RTL)
	CLKGATE="sg13g2_lgcp_1 GATE:CLK:GCLK" synth/run_synth.sh tcim_core rtl/tcim_pkg.sv rtl/tcim_core.sv
	synth/run_synth.sh tmac24 rtl/tcim_pkg.sv rtl/baseline/tmac24.sv
	synth/run_synth.sh dtile72x24 rtl/tcim_pkg.sv rtl/baseline/dtile72x24.sv
	CLKGATE="sg13g2_lgcp_1 GATE:CLK:GCLK" synth/run_synth.sh dtile72x24 rtl/tcim_pkg.sv rtl/baseline/dtile72x24.sv
	$(PY) synth/baseline_energy.py
	$(PY) synth/tcim_energy.py
	$(PY) synth/tcim_energy.py tcim_core_cg
	$(PY) array/exp_energy_system.py

# ---- lint and the second simulator (Verilator; VERILATOR_ROOT must point at a Verilator 5 build) --------
VL      := $(VERILATOR_ROOT)/bin/verilator
VLFLAGS := --cc --exe --build -j 2 -O3 --top-module tcim_top -CFLAGS "-std=c++17 -O2 -I$(CURDIR)/tb/verilator"

lint:
	$(VL) --lint-only -Wall --top-module tcim_top $(RTL)
	$(VL) --lint-only -Wall +define+TCIM_ENC_PNX --top-module tcim_top $(RTL)

rtl-verilator: tb/vectors/net_x.txt
	$(VL) $(VLFLAGS) -Mdir tb/build_vl $(RTL) tb/tb_tcim.cc -o tb_vl
	tb/build_vl/tb_vl tb/vectors | tee results/rtl_test_verilator.log
	$(VL) $(VLFLAGS) +define+TCIM_ENC_PNX -CFLAGS -DTCIM_ENC_PNX -Mdir tb/build_vl_pnx $(RTL) tb/tb_tcim.cc -o tb_vl
	tb/build_vl_pnx/tb_vl tb/vectors | tee results/rtl_test_verilator_pnx.log

# ---- formal proofs of sequencer and serial-port properties (SymbiYosys; SBY = path to sby) ---------------
SBY ?= sby
formal:
	cd formal && bash -o pipefail -c '($(SBY) -f tcim_spi.sby && $(SBY) -f tcim_core.sby safety && $(SBY) -f tcim_core.sby safety_pnx && $(SBY) -f tcim_core.sby progress && $(SBY) -f tcim_core.sby lfsr) 2>&1 | tee ../results/formal.log'
	mkdir -p results/security
	cd formal && $(SBY) -f tcim_miter.sby prove > ../results/security/miter_prove.log 2>&1 && $(SBY) -f tcim_miter.sby prove_pnx > ../results/security/miter_prove_pnx.log 2>&1
	SBY="$(SBY)" $(PY) formal/check_faults.py

# ---- after place and route (flow/orfs; POST_DIR = folder with 6_final.v/.spef/.sdc of a platform) -----
#   timing with extracted parasitics:  POST_LIB=<liberty> POST_DIR=... sta -no_init -exit flow/orfs/post/sta_post.tcl
#   gate-level test of the routed netlist with the full test bench, and the same with one gate changed:
gls:
	flow/orfs/post/gls.sh $(POST_DIR)/6_final.v $(POST_LIB) build/gls
	flow/orfs/post/gls.sh $(POST_DIR)/6_final.v $(POST_LIB) build/gls_fault xnor
	flow/orfs/post/gls.sh $(POST_DIR)/6_final.v $(POST_LIB) build/gls_fault_icg icg

# ---- timing after layout at every corner, parasitics x0.8 and x1.2, shortest clock period at the slow corner
#   (revision 4.3; WORK = unpacked export of one platform, LIBDIR = its Liberty folder; SKY130 slow and fast
#   libraries: tools/make_sky130_corner_libs.sh). Then flow/orfs/post/collect_pnr.py writes results/pnr.json.
post-corners:
	flow/orfs/post/post_corners.sh $(PLATFORM) $(WORK) $(LIBDIR)
	python3 flow/orfs/post/min_period.py $(PLATFORM) $(WORK) $(SLOWLIB) 1
	python3 flow/orfs/post/min_period.py $(PLATFORM) $(WORK) $(SLOWLIB) 1.2

# ---- layout of the transistor part of the array (DRC: layout/run_drc.bat in the ORFS image on the PC) --
layout:
	$(PY) layout/cell_2t2r.py
	$(PY) layout/periphery_layout.py
#   then on the PC: layout\run_drc.bat (array) and layout\run_periph_checks.bat (periphery DRC + LVS);
#   copy layout\periph_checks.log to results/periph_layout/ and run: $(PY) layout/collect_periph_checks.py

# ---- read path ----------------------------------------------------------------------------------------
sense: $(GC)/plugins/reram_stanford_ihp.so
	cd $(GC) && $(PY) exp_sense.py && $(PY) exp_sense_mc.py 200
	$(PY) model/read_disturb.py

# read path over temperature and supply; first-cut periphery (level shifter, word-line driver, column switch)
sense-env:
	cd $(GC) && $(PY) exp_sense_env.py

periphery:
	cd $(GC) && $(PY) periphery.py
	cd $(GC) && $(PY) periphery2.py
	cd $(GC) && $(PY) exp_reset_gate.py ss
	cd $(GC) && $(PY) periphery2.py --add-cs-bound

# ---- programming with device-to-device spread (assumed spreads); SkyWater SKY130 port (SKY130_FD_PR) ----
program-mc:
	$(PY) model/program_mc.py 100

sky130-port:
	$(PY) model/sky130_port.py

clean:
	rm -rf tb/build synth/build $(GC)/plugins $(GC)/tmp*.gc results/rtl_mutation*_[0-9]*_[0-9]*.json

# ---- SKY130 chip: TCIM0 + array controller, the full test bench against a line-level macro model -----------
CHIP_RTL := $(RTL) rtl/chip/tcim_actl.sv rtl/chip/tcim_chip_core.sv
tb/build_chip/tcim_chip_core.h: $(CHIP_RTL)
	mkdir -p tb/build_chip
	yosys -q -p "read_slang --top tcim_chip_core $(CHIP_RTL); hierarchy -top tcim_chip_core; proc; flatten; opt; write_cxxrtl -header -namespace cxxrtl_design tb/build_chip/tcim_chip_core.cc"

tb/build_chip/tb_chip: tb/tb_tcim.cc tb/build_chip/tcim_chip_core.h
	$(CXX) -std=c++14 -O1 -DTCIM_CHIP -I tb/build_chip -I $(CXXRTL) tb/tb_tcim.cc tb/build_chip/tcim_chip_core.cc -o $@

# three controller configurations (ts,tp,tr): shortest, default, longer
rtl-chip: tb/build_chip/tb_chip tb/vectors/net_x.txt
	mkdir -p results/sky130_chip
	TB_CFG=0,0,0 tb/build_chip/tb_chip tb/vectors | tee results/sky130_chip/rtl_chip_000.log
	TB_CFG=1,1,0 tb/build_chip/tb_chip tb/vectors | tee results/sky130_chip/rtl_chip_110.log
	TB_CFG=3,2,1 tb/build_chip/tb_chip tb/vectors | tee results/sky130_chip/rtl_chip_321.log
	grep -q "TEST PASSED" results/sky130_chip/rtl_chip_000.log && grep -q "TEST PASSED" results/sky130_chip/rtl_chip_110.log && grep -q "TEST PASSED" results/sky130_chip/rtl_chip_321.log


# next-chip cell (3T3R): the chip's logic with the Z bit line, through the line-level macro model (8 November 2026)
tb/build_chip_1of3/tcim_chip_core.h: $(CHIP_RTL)
	mkdir -p tb/build_chip_1of3
	yosys -q -p "read_slang -D TCIM_CELL_1OF3 --top tcim_chip_core $(CHIP_RTL); hierarchy -top tcim_chip_core; proc; flatten; opt; write_cxxrtl -header -namespace cxxrtl_design tb/build_chip_1of3/tcim_chip_core.cc"

tb/build_chip_1of3/tb_chip: tb/tb_tcim.cc tb/build_chip_1of3/tcim_chip_core.h
	$(CXX) -std=c++14 -O1 -DTCIM_CHIP -DTCIM_CELL_1OF3 -I tb/build_chip_1of3 -I $(CXXRTL) tb/tb_tcim.cc tb/build_chip_1of3/tcim_chip_core.cc -o $@

rtl-chip-1of3: tb/build_chip_1of3/tb_chip tb/vectors/net_x.txt
	mkdir -p results/next_chip
	TB_CFG=1,1,0 tb/build_chip_1of3/tb_chip tb/vectors | tee results/next_chip/rtl_chip_1of3_110.log

# the chip's logic: lint (all warnings) and proof that the plain-Verilog copy given to place and route equals the RTL
equiv-chip:
	VERILATOR=$(VL) bash tests/equiv/run_equiv_chip.sh

# Magic DRC (full rules, the precheck's commands) and antenna check of the whole user area (needs PDK_ROOT)
signoff:
	cd layout/sky130/periph && python3 signoff.py

# the chip's logic on Verilator (second simulator for the chip build; shim tb/verilator/tcim_chip_core.h)
rtl-chip-verilator: tb/vectors/net_x.txt
	mkdir -p results/sky130_chip
	$(VL) --cc --exe --build -j 2 -O3 --top-module tcim_chip_core -CFLAGS "-std=c++17 -O2 -DTCIM_CHIP -I$(CURDIR)/tb/verilator" \
	  -Mdir tb/build_vl_chip $(CHIP_RTL) tb/tb_tcim.cc -o tb_vl_chip
	TB_CFG=1,1,0 tb/build_vl_chip/tb_vl_chip tb/vectors | tee results/sky130_chip/rtl_chip_verilator_110.log
	grep -q "TEST PASSED" results/sky130_chip/rtl_chip_verilator_110.log
