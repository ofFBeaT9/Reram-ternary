#!/bin/bash
# Build the simulators this repository was verified with, into $PREFIX (default: ./tools/prefix).
# Needs: git, a C++ compiler, make, bison, flex, autoconf/automake/libtool (ngspice), cmake (Yosys).
# Versions are pinned to the ones that produced results/ (see docs/STATUS.md).
set -e
PREFIX=${PREFIX:-$(cd "$(dirname "$0")" && pwd)/prefix}
SRC=${SRC:-$(cd "$(dirname "$0")" && pwd)/src}
J=${J:-2}
mkdir -p "$PREFIX" "$SRC"; cd "$SRC"
export PATH=$PREFIX/bin:$PATH LD_LIBRARY_PATH=$PREFIX/lib:$LD_LIBRARY_PATH

# Gnucap and its Verilog-A model compiler (snapshot 2026-07-29)
[ -d gnucap ] || git clone --depth 1 --branch 20260729-dev https://github.com/gnucap/gnucap.git
(cd gnucap && ./configure --prefix="$PREFIX" && make -j$J && make install)
[ -d gnucap-modelgen-verilog ] || git clone --depth 1 --branch 20260729-dev https://github.com/gnucap/gnucap-modelgen-verilog.git
(cd gnucap-modelgen-verilog && ./configure --prefix="$PREFIX"; make -j$J && make install)

# ngspice 46
[ -d ngspice ] || git clone --depth 1 --branch ngspice-46 https://github.com/imr/ngspice.git
(cd ngspice && ./autogen.sh && mkdir -p release && cd release && ../configure --prefix="$PREFIX" --with-x=no --with-readline=no --enable-osdi --disable-debug && make -j$J && make install)

# Yosys with the slang SystemVerilog front end (commit 0605026, 6 Oct 2026). About two hours on two cores.
if [ "$WITH_YOSYS" = 1 ]; then
  [ -d yosys ] || git clone --recursive https://github.com/YosysHQ/yosys.git
  (cd yosys && git checkout 0605026 && git submodule update --init --recursive &&
   cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PREFIX" -DYOSYS_WITHOUT_TCL=ON -DYOSYS_WITHOUT_READLINE=ON \
         -DYOSYS_WITHOUT_EDITLINE=ON -DYOSYS_WITHOUT_LIBFFI=ON -DYOSYS_ENABLE_UNIT_TESTS=OFF -DBUILD_SHARED_LIBS=OFF &&
   cmake --build build -j$J && cmake --install build)
fi

# IHP open PDK and its Gnucap model plugins (PSP103 low- and high-voltage MOS). The model compile takes
# about 20 minutes per device family and prints "abrupt end of file" for PSP103_scaling.include: harmless,
# the PDK's reference tests pass (make pdk-check).
[ -d IHP-Open-PDK ] || git clone --depth 1 https://github.com/IHP-GmbH/IHP-Open-PDK.git
G=$SRC/IHP-Open-PDK/ihp-sg13g2/libs.tech/gnucap
make -C "$G/cpp"
make -C "$G/models" sg13g2_moshv_paramset sg13g2_moslv_paramset idc CXXFLAGS="-O1"

cat <<MSG

Done. Add to your shell:
  export PATH=$PREFIX/bin:\$PATH
  export LD_LIBRARY_PATH=$PREFIX/lib:\$LD_LIBRARY_PATH
  export IHP_GNUCAP=$G
  export IHP_STDCELL_LIB=$SRC/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
MSG
