// tcim_chip_core.h for Verilator: lets tb/tb_tcim.cc built with -DTCIM_CHIP (written for the CXXRTL model) run on a
// Verilator model of the chip's digital part (gate-level run of the routed tcim_chip_digital, flow/orfs/post/gls_chip.sh,
// 11 October 2026). Same scheme as tcim_top.h: one cxxrtl::value<N> per port; inputs are copied into the model before
// each evaluation, outputs out of it after. The Verilator top module must be called tcim_chip_core.
#pragma once
#include <cstdint>
#include <cstddef>
#include "Vtcim_chip_core.h"
#include "verilated.h"

namespace cxxrtl {
template <size_t N> struct value {
    static constexpr size_t chunks = (N + 31) / 32;
    uint32_t data[chunks] = {};
    template <class T> void set(T v) {
        uint64_t x = (uint64_t)v;
        data[0] = (uint32_t)x;
        if (chunks > 1) data[1] = (uint32_t)(x >> 32);
    }
    template <class T> T get() const {
        uint64_t x = data[0];
        if (chunks > 1) x |= (uint64_t)data[1] << 32;
        return (T)x;
    }
};
}  // namespace cxxrtl

namespace cxxrtl_design {
struct p_tcim__chip__core {
    Vtcim_chip_core m;
    // inputs
    cxxrtl::value<1> p_clk, p_rst__n, p_sck, p_cs__n, p_mosi;
    cxxrtl::value<3> p_cfg__ts, p_cfg__tp;
    cxxrtl::value<2> p_cfg__tr;
    cxxrtl::value<24> p_sa__p, p_sa__n;
    // outputs
    cxxrtl::value<1> p_miso, p_irq, p_wl__prog, p_bl__sen, p_sl__prg, p_flt, p_pk, p_pstb;
    cxxrtl::value<72> p_wl__on;
    cxxrtl::value<24> p_blp__prg, p_bln__prg;
    cxxrtl::value<3> p_ref__sel;
    cxxrtl::value<5> p_pamp;
    cxxrtl::value<13> p_tie__hi;
    cxxrtl::value<22> p_tie__lo;

    void step() {
        m.clk = p_clk.data[0] & 1; m.rst_n = p_rst__n.data[0] & 1; m.sck = p_sck.data[0] & 1;
        m.cs_n = p_cs__n.data[0] & 1; m.mosi = p_mosi.data[0] & 1;
        m.cfg_ts = p_cfg__ts.data[0] & 7; m.cfg_tp = p_cfg__tp.data[0] & 7; m.cfg_tr = p_cfg__tr.data[0] & 3;
        m.sa_p = p_sa__p.data[0]; m.sa_n = p_sa__n.data[0];
        m.eval();
        p_miso.data[0] = m.miso; p_irq.data[0] = m.irq; p_wl__prog.data[0] = m.wl_prog; p_bl__sen.data[0] = m.bl_sen;
        p_sl__prg.data[0] = m.sl_prg; p_flt.data[0] = m.flt; p_pk.data[0] = m.pk; p_pstb.data[0] = m.pstb;
        for (size_t i = 0; i < p_wl__on.chunks; i++) p_wl__on.data[i] = m.wl_on[i];
        p_blp__prg.data[0] = m.blp_prg; p_bln__prg.data[0] = m.bln_prg; p_ref__sel.data[0] = m.ref_sel;
        p_pamp.data[0] = m.pamp;
#ifdef TCIM_CHIP_TIES                  // the gate-level netlist (tcim_chip_digital) also has the pad-control ties
        p_tie__hi.data[0] = m.tie_hi; p_tie__lo.data[0] = m.tie_lo;
#endif
    }
};
}  // namespace cxxrtl_design
