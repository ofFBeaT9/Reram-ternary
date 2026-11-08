// tcim_top.h for Verilator: lets tb/tb_tcim.cc (written for the CXXRTL model) run unchanged on a Verilator model.
// It provides the few CXXRTL names the test bench uses: cxxrtl::value<N> with set/get and 32-bit chunks in .data,
// and cxxrtl_design::p_tcim__top with one value per port and step(). Inputs are copied into the model before each
// evaluation; outputs are copied out after it. Build: make rtl-verilator (second simulator).
#pragma once
#include <cstdint>
#include <cstddef>
#include "Vtcim_top.h"
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
struct p_tcim__top {
    Vtcim_top m;
    // inputs
    cxxrtl::value<1> p_clk, p_rst__n, p_sck, p_cs__n, p_mosi, p_arr__ack;
    cxxrtl::value<24> p_arr__sa__p, p_arr__sa__n;
    cxxrtl::value<240> p_arr__adc;
    // outputs
    cxxrtl::value<1> p_miso, p_irq, p_arr__req;
    cxxrtl::value<3> p_arr__op;
    cxxrtl::value<7> p_arr__row;
    cxxrtl::value<72> p_arr__row__mask;
    cxxrtl::value<24> p_arr__mask__p, p_arr__mask__n;
    cxxrtl::value<5> p_arr__amp;

    void step() {
        m.clk = p_clk.data[0] & 1; m.rst_n = p_rst__n.data[0] & 1; m.sck = p_sck.data[0] & 1;
        m.cs_n = p_cs__n.data[0] & 1; m.mosi = p_mosi.data[0] & 1; m.arr_ack = p_arr__ack.data[0] & 1;
        m.arr_sa_p = p_arr__sa__p.data[0]; m.arr_sa_n = p_arr__sa__n.data[0];
        for (size_t i = 0; i < p_arr__adc.chunks; i++) m.arr_adc[i] = p_arr__adc.data[i];
        m.eval();
        p_miso.data[0] = m.miso; p_irq.data[0] = m.irq; p_arr__req.data[0] = m.arr_req;
        p_arr__op.data[0] = m.arr_op; p_arr__row.data[0] = m.arr_row; p_arr__amp.data[0] = m.arr_amp;
        for (size_t i = 0; i < p_arr__row__mask.chunks; i++) p_arr__row__mask.data[i] = m.arr_row_mask[i];
        p_arr__mask__p.data[0] = m.arr_mask_p; p_arr__mask__n.data[0] = m.arr_mask_n;
    }
};
}  // namespace cxxrtl_design
