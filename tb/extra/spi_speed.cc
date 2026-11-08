// How fast may the serial clock be? A host that follows SPI mode 0 drives MOSI on the falling edge and samples MISO
// on the rising edge. Sweep the half period (in system clock cycles) and the phase of the serial clock.
#include <cstdio>
#include <cstdint>
#include <random>
#include "tcim_top.h"
static cxxrtl_design::p_tcim__top top;
static void tick() { top.p_arr__ack.set<bool>(false); top.p_clk.set<bool>(true); top.step(); top.p_clk.set<bool>(false); top.step(); }
static uint64_t xfer(int hi, int lo, bool write, bool word, unsigned addr, uint64_t wdata) {
    uint8_t tx[8], rx[8] = {0};
    tx[0] = (write ? 0x80 : 0) | (word ? 0x40 : 0) | (addr & 0x3f);
    for (int i = 0; i < 6; i++) tx[1 + i] = (wdata >> (8 * (5 - i))) & 0xff;
    tx[7] = 0;
    top.p_cs__n.set<bool>(false); for (int i = 0; i < lo; i++) tick();
    for (int b = 0; b < 64; b++) {
        bool bit = (tx[b / 8] >> (7 - b % 8)) & 1;
        top.p_mosi.set<bool>(bit);                         // MOSI changes with the falling edge (or CS)
        for (int i = 0; i < lo; i++) tick();
        if (top.p_miso.get<bool>()) rx[b / 8] |= 1 << (7 - b % 8);     // sampled at the rising edge
        top.p_sck.set<bool>(true);
        for (int i = 0; i < hi; i++) tick();
        top.p_sck.set<bool>(false);
    }
    for (int i = 0; i < lo; i++) tick();
    top.p_cs__n.set<bool>(true); for (int i = 0; i < 6; i++) tick();
    uint64_t r = 0; for (int i = 0; i < 6; i++) r = (r << 8) | rx[1 + i];
    return (r << 8) | rx[7];
}
int main() {
    std::mt19937_64 rng(7);
    for (int h = 1; h <= 8; h++) {
        top.p_rst__n.set<bool>(false); top.p_cs__n.set<bool>(true); top.p_sck.set<bool>(false);
        for (int i = 0; i < 5; i++) tick();
        top.p_rst__n.set<bool>(true); for (int i = 0; i < 5; i++) tick();
        int bad = 0, n = 0;
        for (int k = 0; k < 200; k++) {
            uint64_t d = rng() & 0xffffffffffffULL;
            // keep only legal trit codes so that the value is stored as written
            for (int t = 0; t < 24; t++) if (((d >> (2 * t)) & 3) == 2) d &= ~(3ULL << (2 * t));
            unsigned a = 4 + 4 * (k % 3);
            xfer(h, h, true, true, a, d);
            uint64_t r = xfer(h, h, false, true, a, 0);
            n++; if ((r >> 8) != d || (r & 0xff) != 1) bad++;
        }
        printf("half period %d clock cycles (sck = clk/%d): %d of %d write-read pairs wrong\n", h, 2 * h, bad, n);
    }
    return 0;
}
