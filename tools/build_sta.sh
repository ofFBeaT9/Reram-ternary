#!/bin/bash
# builds Tcl, SWIG, CUDD and OpenSTA from source into the sandbox tool prefix (no root, no apt)
set -x
# usage: tools/build_sta.sh [work folder]     (default $HOME/reram-tools; the same prefix as tools/build_tools.sh)
# Versions that worked on 7 October 2026: Tcl core-8-6-branch, SWIG v4.2.1, Eigen 3.3.90 (the GitHub mirror; gitlab.com was not reachable), CUDD (ivmai, head),
# OpenSTA 3.1.0 at b7d866f. Needs git, cmake, a C++17 compiler, bison, flex, autoconf, automake, libtool, zlib.
S=${1:-$HOME/reram-tools}
P=$S/prefix
mkdir -p $S/ext $P
export PATH=$P/bin:$PATH LD_LIBRARY_PATH=$P/lib:$LD_LIBRARY_PATH
cd $S/ext
[ -d OpenSTA ] || timeout 300 git clone https://github.com/parallaxsw/OpenSTA || exit 10
[ -d cudd ] || timeout 300 git clone --depth 1 https://github.com/ivmai/cudd || exit 10
[ -d tcl ] || timeout 300 git clone --depth 1 -b core-8-6-branch https://github.com/tcltk/tcl || exit 11
[ -f $P/lib/libtcl8.6.so ] || (cd tcl/unix && ./configure --prefix=$P >/dev/null && make -j2 >/dev/null 2>&1 && make install >/dev/null 2>&1) || exit 12
[ -d swig ] || timeout 300 git clone --depth 1 -b v4.2.1 https://github.com/swig/swig || exit 13
[ -x $P/bin/swig ] || (cd swig && ./autogen.sh >/dev/null 2>&1 && ./configure --prefix=$P --without-pcre >/dev/null && make -j2 >/dev/null 2>&1 && make install >/dev/null 2>&1) || exit 14
[ -e $P/bin/tclsh ] || ln -s tclsh8.6 $P/bin/tclsh       # OpenSTA's build calls "tclsh"
[ -d eigen ] || timeout 300 git clone --depth 1 -b 3.4.0 https://gitlab.com/libeigen/eigen.git || timeout 300 git clone --depth 1 https://github.com/eigenteam/eigen-git-mirror eigen || exit 15
[ -f $P/share/eigen3/cmake/Eigen3Config.cmake ] || (cmake -S eigen -B eigen/build -DCMAKE_INSTALL_PREFIX=$P -DBUILD_TESTING=OFF -DEIGEN_BUILD_DOC=OFF >/dev/null && cmake --install eigen/build >/dev/null) || exit 15
[ -f $P/lib/libcudd.a ] || (cd cudd && autoreconf -fi >/dev/null 2>&1 && ./configure --prefix=$P --disable-dependency-tracking >/dev/null && make -j2 >/dev/null 2>&1 && make install >/dev/null 2>&1) || exit 16
mkdir -p OpenSTA/build && cd OpenSTA/build
cmake .. -DCMAKE_INSTALL_PREFIX=$P -DCMAKE_BUILD_TYPE=Release -DCUDD_DIR=$P -DTCL_LIBRARY=$P/lib/libtcl8.6.so -DTCL_HEADER=$P/include/tcl.h -DCMAKE_PREFIX_PATH="$P" -DUSE_TCL_READLINE=OFF || exit 17
make -j2 || exit 18
make install || exit 19
echo BUILD_STA_DONE
