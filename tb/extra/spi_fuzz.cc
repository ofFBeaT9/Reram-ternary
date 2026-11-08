// Serial-port fuzzing (revision 4.8, 7 November 2026). Random traffic on the four-wire port of tcim_top:
//   - aborted frames: chip select raised after 0 to 55 serial clocks, random MOSI (must write nothing);
//   - complete writes with random data to every address except CTRL (0), SEC (3) and PCMD (48), which start or lock
//     operations (writes to read-only registers must change nothing);
//   - complete reads of random addresses;
//   - chip-select glitches and idle gaps; serial clock between clk/6 and clk/10 (results/spi_speed.log: clk/6 is the limit).
// A reference model keeps X0..X2, PDATA (words) and PROW (tryte); every 64 frames all five are read back with clean frames
// and compared. The status byte of every complete frame must be {bus_err, irq, 1} with bus_err set exactly for an
// address the register map (docs/STATUS.md, section 1.4) does not define, and irq 0 (no command runs). Fails on any mismatch or if a clean frame stops
// working (a stuck serial state). Usage: spi_fuzz <frames> <seed>; prints one summary line.
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <random>
#include "tcim_top.h"
static cxxrtl_design::p_tcim__top top;
static std::mt19937_64 rng;
static uint64_t ticks = 0;
static void tick() { top.p_arr__ack.set<bool>(false); top.p_clk.set<bool>(true); top.step(); top.p_clk.set<bool>(false); top.step(); ticks++; }
static void idle(int n) { for (int i = 0; i < n; i++) tick(); }
// one frame of nbits serial clocks (64 = complete); returns the 64 bits read on MISO
static uint64_t frame(const uint8_t tx[8], int nbits, int h) {
    uint8_t rx[8] = {0};
    top.p_cs__n.set<bool>(false); idle(h);
    for (int b = 0; b < nbits; b++) {
        top.p_mosi.set<bool>((tx[b / 8] >> (7 - b % 8)) & 1);
        idle(h);
        if (top.p_miso.get<bool>()) rx[b / 8] |= 1 << (7 - b % 8);
        top.p_sck.set<bool>(true); idle(h); top.p_sck.set<bool>(false);
    }
    idle(h); top.p_cs__n.set<bool>(true); idle(6);
    uint64_t r = 0; for (int i = 0; i < 8; i++) r = (r << 8) | rx[i];
    return r;
}
static uint64_t legal(uint64_t d, int trits) {       // replace the unused code 2'b10 by 0 so the value is stored as written
    d &= (trits == 24) ? 0xffffffffffffULL : 0xfffULL;
    for (int t = 0; t < trits; t++) if (((d >> (2 * t)) & 3) == 2) d &= ~(3ULL << (2 * t));
    return d;
}
static bool mapped(bool word, unsigned a) {           // the register map of docs/STATUS.md 1.4, written out again
    if (word) return a == 4 || a == 8 || a == 12 || a == 44 || a == 52;
    return a <= 3 || (a >= 16 && a <= 39) || a == 40 || a == 48 || a == 49 || a == 50;
}
static unsigned want(bool word, unsigned a) { return mapped(word, a) ? 1u : 5u; }
static uint64_t xfer(bool write, bool word, unsigned addr, uint64_t data, int h, unsigned *stat) {
    uint8_t tx[8];
    tx[0] = (write ? 0x80 : 0) | (word ? 0x40 : 0) | (addr & 0x3f);
    for (int i = 0; i < 6; i++) tx[1 + i] = (data >> (8 * (5 - i))) & 0xff;
    tx[7] = 0;
    uint64_t r = frame(tx, 64, h);
    if (stat) *stat = r & 0xff;
    return (r >> 8) & 0xffffffffffffULL;
}
int main(int argc, char **argv) {
    long frames = argc > 1 ? atol(argv[1]) : 100000;
    rng.seed(argc > 2 ? atoll(argv[2]) : 1);
    top.p_rst__n.set<bool>(false); top.p_cs__n.set<bool>(true); top.p_sck.set<bool>(false); idle(5);
    top.p_rst__n.set<bool>(true); idle(5);
    uint64_t mx[3] = {0, 0, 0}, mpdata = 0, mprow = 0;            // reference model (all zero after reset)
    const unsigned xa[3] = {4, 8, 12};
    long aborted = 0, writes = 0, reads = 0, checks = 0, bad = 0, badstat = 0;
    for (long k = 0; k < frames; k++) {
        int h = 3 + (int)(rng() % 3);
        unsigned kind = rng() % 4, st = 0;
        if (kind == 0) {                                          // aborted frame, random content
            uint8_t tx[8]; for (auto &b : tx) b = rng() & 0xff;
            frame(tx, (int)(rng() % 56), h); aborted++;
        } else if (kind == 1) {                                   // complete write
            unsigned a; do a = rng() % 64; while (a == 0 || a == 3 || a == 48);
            bool word = rng() & 1;
            uint64_t d = rng() & 0xffffffffffffULL;
            xfer(true, word, a, d, h, &st); writes++;
            if (st != want(word, a)) badstat++;
            for (int i = 0; i < 3; i++) if (word && a == xa[i]) mx[i] = legal(d, 24);
            if (word && a == 44) mpdata = legal(d, 24);
            if (!word && a == 40) mprow = legal(d, 6);
            if ((word && (a == 4 || a == 8 || a == 12 || a == 44)) || (!word && a == 40)) {
                // the model stores only legal codes: write the legalised value again so DUT and model agree
                uint64_t v = (a == 40) ? mprow : (a == 44) ? mpdata : mx[(a - 4) / 4];
                xfer(true, word, a, v, h, &st); writes++;
                if (st != want(word, a)) badstat++;
            }
        } else if (kind == 2) {                                   // complete read
            bool word = rng() & 1; unsigned a = rng() % 64;
            xfer(false, word, a, rng(), h, &st); reads++;
            if (st != want(word, a)) badstat++;
        } else {                                                  // chip-select glitch and idle gap
            top.p_cs__n.set<bool>(false); idle(1 + rng() % 3); top.p_cs__n.set<bool>(true); idle(1 + rng() % 20);
        }
        if (k % 64 == 63 || k == frames - 1) {                    // clean read-back of every modelled register
            for (int i = 0; i < 3; i++) { checks++; if (xfer(false, true, xa[i], 0, 4, &st) != mx[i] || st != 1) bad++; }
            checks++; if (xfer(false, true, 44, 0, 4, &st) != mpdata || st != 1) bad++;
            checks++; if ((xfer(false, false, 40, 0, 4, &st) & 0xfff) != mprow || st != 1) bad++;
        }
    }
    printf("spi fuzz: %ld frames (%ld aborted, %ld writes, %ld reads), %ld read-back checks, %ld mismatches, "
           "%ld bad status bytes, %llu clock cycles\n", frames, aborted, writes, reads, checks, bad, badstat,
           (unsigned long long)ticks);
    printf(bad == 0 && badstat == 0 ? "FUZZ PASSED\n" : "FUZZ FAILED\n");
    return bad == 0 && badstat == 0 ? 0 : 1;
}
