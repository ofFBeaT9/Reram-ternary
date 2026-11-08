#!/bin/bash
# Compile the ReRAM Verilog-A model into a Gnucap plugin (needs gnucap, gnucap-mg-vams in PATH).
set -e
cd "$(dirname "$0")"
INC=$(gnucap-conf --includedir)
gnucap-mg-vams -I "$INC" -o plugins/reram_stanford_ihp.cc --cc ../../model/reram_stanford_ihp.va
c++ $(gnucap-conf --cppflags) -shared -fPIC $(gnucap-conf --cxxflags) -O1 plugins/reram_stanford_ihp.cc -o plugins/reram_stanford_ihp.so $(gnucap-conf --ldflags)
echo built plugins/reram_stanford_ihp.so
