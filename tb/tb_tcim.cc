// tb_tcim.cc - self-checking test bench for tcim_top, built on the CXXRTL model that Yosys generates
// from the RTL. The analog macro is replaced by a behavioural array with per-device currents,
// random switching thresholds and pulse-and-verify behaviour.
//
// Tests: register access, misaligned access, row programming with verify (with monitors of the pulse
// protocol), read-back, digital products against the exact dot product, analog-mode raw counts, error paths,
// directed tests added in the audit (blocks 5b and 5c), and inference of the ternary digits network
// (tb/vectors) whose results must equal the software reference sample by sample.
// Set TB_FAIL_FAST=1 to stop at the first failure (used by tb/mutation_test.py).
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <cmath>
#include <vector>
#include <array>
#include <random>
#include <string>
#include <fstream>
#include <sstream>
// Built with -DTCIM_CHIP the same tests run on the digital part of the SKY130 chip (rtl/chip/tcim_chip_core.sv:
// TCIM0 + array controller); the behavioural array is then driven by the controller's line-level outputs (word
// lines, bit-line and source-line modes, reference select) instead of the arr_* requests, with electrical checks
// of every cycle (macro_eval below). Analog mode has no converter on that chip: its products must return zero.
#ifdef TCIM_CHIP
#include "tcim_chip_core.h"
#else
#include "tcim_top.h"
#endif

using namespace std;
static const int ROWS = 72, COLS = 24, ACCW = 10;
#ifdef TCIM_CHIP
static cxxrtl_design::p_tcim__chip__core top;
#else
static cxxrtl_design::p_tcim__top top;
#endif
static uint64_t cycles = 0;
static int errors = 0, checks = 0;
static mt19937 rng(12345);

static bool fail_fast = false;      // set by the environment variable TB_FAIL_FAST: stop at the first failure
#define CHECK(cond, ...) do { checks++; if (!(cond)) { errors++; if (errors < 40) { printf("  FAIL: "); printf(__VA_ARGS__); printf("\n"); } if (fail_fast) { printf("TEST FAILED\n"); fflush(stdout); exit(1); } } } while (0)

// ---------------------------------------------------------------- behavioural array
struct Array {
    double ip[ROWS][COLS], in[ROWS][COLS];        // device read currents, uA at 0.2 V
    int thr_set_p[ROWS][COLS], thr_set_n[ROWS][COLS], thr_rst_p[ROWS][COLS], thr_rst_n[ROWS][COLS];
    bool stuck_p[ROWS][COLS];                     // device that never sets (for the error-path test)
    bool stuck_rst_p[ROWS][COLS];                 // device that never resets
    double i_mid = 25.0, i_set = 42.0, i_rst = 6.0;
    int busy = 0; bool pending = false;
    int delay = 2;                                // clock cycles the macro takes per operation
    bool adc_force = false; long adc_p = 0, adc_n = 0; int sum_phase = 0;   // directed test of the analog saturation path
    uint64_t n_read = 0, n_pulse = 0, n_sum = 0, bad_row = 0;
    uint64_t n_pulse_real = 0;                    // pulses that selected at least one device (revision 4.6: empty padding pulses)
    int row_reads[ROWS] = {0}; int last_read_row = -1; uint64_t order_breaks = 0;   // reads at the mid reference, per row
    // monitor of back-to-back requests (revision 4.2): clock cycles with arr_req low between two requests
    bool gap_mon = false, seen_req = false; uint64_t low_run = 0, gaps = 0;
    // monitors of the programming protocol (armed by program_row)
    const int *tgt = nullptr; int exp_row = -1; int seq_set = 0, seq_rst = 0;
    uint64_t amp_err = 0, order_err = 0, overpulse = 0, wrong_dev = 0, empty_pulse = 0, wrong_row = 0;
    normal_distribution<double> lrs{43.59, 1.55}, hrs{2.85, 1.85};
    double sample_hrs() { double v; do { v = hrs(rng); } while (v < 0.05 || v > 5.9); return v; }
    double sample_lrs() { return lrs(rng); }
    void init() {
        uniform_int_distribution<int> ts(4, 14), tr(2, 12);
        for (int r = 0; r < ROWS; r++) for (int c = 0; c < COLS; c++) {
            ip[r][c] = sample_hrs(); in[r][c] = sample_hrs();
            thr_set_p[r][c] = ts(rng); thr_set_n[r][c] = ts(rng); thr_rst_p[r][c] = tr(rng); thr_rst_n[r][c] = tr(rng);
            stuck_p[r][c] = false; stuck_rst_p[r][c] = false;
        }
    }
    void force(int r, int c, int w) { ip[r][c] = (w == 1) ? 43.6 : 2.9; in[r][c] = (w == -1) ? 43.6 : 2.9; }
};
static Array arr;

template <size_t N> static bool getbit(const cxxrtl::value<N> &v, size_t i) { return (v.data[i / 32] >> (i % 32)) & 1; }
template <size_t N> static void setbit(cxxrtl::value<N> &v, size_t i, bool b) { if (b) v.data[i / 32] |= (1u << (i % 32)); else v.data[i / 32] &= ~(1u << (i % 32)); }

// one compare of every device of a row with the reference of op 0 (mid), 1 (set target, at or above) or 2 (reset target)
static void note_read(int row) {
    if (row >= 0 && row < ROWS) arr.row_reads[row]++;
    if (arr.last_read_row >= 0 && row != (arr.last_read_row + 1) % ROWS) arr.order_breaks++;
    arr.last_read_row = row;
}
static void sense_row(unsigned op, unsigned row, bool *bp, bool *bn) {
    double ref = (op == 0) ? arr.i_mid : (op == 1) ? arr.i_set : arr.i_rst;
    for (int c = 0; c < COLS; c++) {
        bp[c] = (op == 1) ? (arr.ip[row][c] >= ref) : (arr.ip[row][c] > ref);
        bn[c] = (op == 1) ? (arr.in[row][c] >= ref) : (arr.in[row][c] > ref);
    }
}

// one set (op 3) or reset (op 4) pulse of amplitude code amp on the devices in mp / mn of a row
static void apply_pulse(unsigned op, unsigned row, unsigned amp, const bool *mp, const bool *mn) {
    // monitors: amplitude must start at 0 in each phase and rise by one per pulse; reset pulses come before set pulses;
    // a pulse must go only to devices that have to change and that failed the verify read just before it
    if (op == 3) { if ((int)amp != arr.seq_set++) arr.amp_err++; }
    else         { if ((int)amp != arr.seq_rst++) arr.amp_err++; if (arr.seq_set > 0) arr.order_err++; }
    if (arr.exp_row >= 0 && (int)row != arr.exp_row) arr.wrong_row++;
    bool any = false;
    for (int c = 0; c < COLS; c++) {
        bool sp_ = mp[c], sn_ = mn[c]; any |= sp_ | sn_;
        if (op == 3) { if (sp_ && arr.ip[row][c] >= arr.i_set) arr.overpulse++; if (sn_ && arr.in[row][c] >= arr.i_set) arr.overpulse++; }
        else         { if (sp_ && arr.ip[row][c] <= arr.i_rst) arr.overpulse++; if (sn_ && arr.in[row][c] <= arr.i_rst) arr.overpulse++; }
        if (arr.tgt) {
            if (op == 3) { if (sp_ && arr.tgt[c] != 1) arr.wrong_dev++; if (sn_ && arr.tgt[c] != -1) arr.wrong_dev++; }
            else         { if (sp_ && arr.tgt[c] == 1) arr.wrong_dev++; if (sn_ && arr.tgt[c] == -1) arr.wrong_dev++; }
        }
    }
    if (!any) arr.empty_pulse++; else arr.n_pulse_real++;
    for (int c = 0; c < COLS; c++) {
        if (mp[c]) {
            if (op == 3) { if ((int)amp >= arr.thr_set_p[row][c] && !arr.stuck_p[row][c]) arr.ip[row][c] = arr.sample_lrs(); }
            else         { if ((int)amp >= arr.thr_rst_p[row][c] && !arr.stuck_rst_p[row][c]) arr.ip[row][c] = arr.sample_hrs(); }
        }
        if (mn[c]) {
            if (op == 3) { if ((int)amp >= arr.thr_set_n[row][c]) arr.in[row][c] = arr.sample_lrs(); }
            else         { if ((int)amp >= arr.thr_rst_n[row][c]) arr.in[row][c] = arr.sample_hrs(); }
        }
    }
    arr.n_pulse++;
}

#ifndef TCIM_CHIP
static void array_eval() {       // called once per clock cycle, before the rising edge
    top.p_arr__ack.set<bool>(false);
    bool req = top.p_arr__req.get<bool>();
    if (arr.gap_mon) {
        if (req) { if (arr.seen_req) arr.gaps += arr.low_run; arr.low_run = 0; arr.seen_req = true; }
        else if (arr.seen_req) arr.low_run++;
    }
    if (!arr.pending) {
        if (req) { arr.pending = true; arr.busy = arr.delay; }
        return;
    }
    if (--arr.busy > 0) return;
    arr.pending = false;
    unsigned op = top.p_arr__op.get<unsigned>();
    unsigned row = top.p_arr__row.get<unsigned>();
    unsigned amp = top.p_arr__amp.get<unsigned>();
    if (op != 5 && row >= (unsigned)ROWS) { arr.bad_row++; row = 0; }       // the macro must never be given a row that does not exist
    auto mp = top.p_arr__mask__p, mn = top.p_arr__mask__n;
    cxxrtl::value<COLS> sp, sn; cxxrtl::value<COLS * ACCW> adc;
    if (op == 0 || op == 1 || op == 2) {
        bool bp[COLS], bn[COLS];
        sense_row(op, row, bp, bn);
        for (int c = 0; c < COLS; c++) { setbit(sp, c, bp[c]); setbit(sn, c, bn[c]); }
        arr.n_read++;
        if (op == 0) note_read(row);
    } else if (op == 3 || op == 4) {
        bool bp[COLS], bn[COLS];
        for (int c = 0; c < COLS; c++) { bp[c] = getbit(mp, c); bn[c] = getbit(mn, c); }
        apply_pulse(op, row, amp, bp, bn);
    } else if (op == 5) {
        auto rm = top.p_arr__row__mask;
        for (int c = 0; c < COLS; c++) {
            double d = 0;
            for (int r = 0; r < ROWS; r++) if (getbit(rm, r)) d += arr.ip[r][c] - arr.in[r][c];
            long cnt = lround(4.0 * d / (43.59 - 2.85));          // four converter counts per result step
            if (arr.adc_force) cnt = (arr.sum_phase % 2 == 0) ? arr.adc_p : arr.adc_n;
            if (cnt > 511) cnt = 511; if (cnt < -512) cnt = -512;
            for (int b = 0; b < ACCW; b++) setbit(adc, c * ACCW + b, (cnt >> b) & 1);
        }
        arr.n_sum++; arr.sum_phase++;
    }
    top.p_arr__sa__p = sp; top.p_arr__sa__n = sn; top.p_arr__adc = adc;
    top.p_arr__ack.set<bool>(true);
}
#else
// ---------------------------------------------------------------- line-level model of the analog macro (chip build)
// Every cycle: reads the controller's outputs, checks them electrically, drives the raw sense outputs, and turns each
// word-line pulse back into an array operation (the same sense_row / apply_pulse as the request-level model).
struct Chip {
    unsigned ts = 1, tp = 1, tr = 0;               // configuration pins of normal runs (TB_CFG="ts,tp,tr" overrides)
    bool have_prev = false, prev_wl = false; int prev_row = -1;
    uint32_t prev_key[9] = {0};
    int stable = 0, wl_cycles = 0;
    uint64_t e_short = 0, e_multiwl = 0, e_float = 0, e_switch = 0, e_readcfg = 0, e_progcfg = 0, e_pstb = 0,
             e_tsense = 0, e_tpulse = 0, e_tsettle = 0, e_mixed = 0, e_pk = 0, e_ref = 0, e_bbm = 0, e_skew = 0;
    bool prev_flt = false;
    int line_mode[3 * COLS] = {0}, float_run[3 * COLS] = {0};   // 0 floating, 1 rail, 2 ground, 3 sense amplifier
    mt19937 noise{777};
    uint64_t total() const { return e_short + e_multiwl + e_float + e_switch + e_readcfg + e_progcfg + e_pstb + e_tsense + e_tpulse + e_tsettle + e_mixed + e_pk + e_ref + e_bbm + e_skew; }
} chip;

static void macro_eval() {       // called once per clock cycle, before the rising edge
    bool slow = arr.delay >= 100;                  // the request-level tests of a slow macro: longest timing
    unsigned ts = slow ? 7 : chip.ts, tp = slow ? 7 : chip.tp, tr = slow ? 3 : chip.tr;
    top.p_cfg__ts.set<unsigned>(ts); top.p_cfg__tp.set<unsigned>(tp); top.p_cfg__tr.set<unsigned>(tr);
    // the macro's line drive (periph.spice): bit line to VPRG when prg, to its sense amplifier when bl_sen, to ground
    // when NOT (prg OR bl_sen OR flt); all source lines to VPRG when sl_prg, to ground when NOT (sl_prg OR flt)
    const uint32_t ALL = (1u << COLS) - 1;
    bool sen = top.p_bl__sen.get<bool>(), prog = top.p_wl__prog.get<bool>(), pstb = top.p_pstb.get<bool>();
    bool flt = top.p_flt.get<bool>();
    uint32_t bpp = top.p_blp__prg.get<uint32_t>(), bnp = top.p_bln__prg.get<uint32_t>();
    uint32_t bpd = (sen || flt) ? 0 : (~bpp & ALL), bnd = (sen || flt) ? 0 : (~bnp & ALL);
    uint32_t slp = top.p_sl__prg.get<bool>() ? ALL : 0, sld = (slp || flt) ? 0 : ALL;
    unsigned ref = top.p_ref__sel.get<unsigned>();
    int nwl = 0, row = -1;
    for (int r = 0; r < ROWS; r++) if (getbit(top.p_wl__on, r)) { nwl++; row = r; }
    // electrical checks
    if ((bpp & bpd) | (bnp & bnd) | (slp & sld)) chip.e_short++;                     // a rail shorted to ground
    if (sen && (bpp | bpd | bnp | bnd)) chip.e_short++;                              // a sense input driven by a driver
    if (nwl > 1) chip.e_multiwl++;
    // the ground NOR gates: prg / bl_sen / sl_prg may change only with flt high in this cycle and the one before, so that
    // a skew between them and flt cannot turn a ground switch on while a rail switch is still on
    if (chip.have_prev && (bpp != chip.prev_key[0] || bnp != chip.prev_key[2] || slp != chip.prev_key[4] || (uint32_t)sen != chip.prev_key[6])
        && !(flt && chip.prev_flt)) chip.e_skew++;
    chip.prev_flt = flt;
    // break-before-make: a line goes from one driven mode to another only through a floating cycle, and floats for
    // no more than two cycles (lines are driven at all other times, also between operations)
    for (int l = 0; l < 3 * COLS; l++) {
        int g = l / COLS, c = l % COLS;
        uint32_t p = g == 0 ? bpp : g == 1 ? bnp : slp, d = g == 0 ? bpd : g == 1 ? bnd : sld;
        int mode = ((p >> c) & 1) ? 1 : ((d >> c) & 1) ? 2 : (g < 2 && sen) ? 3 : 0;
        if (chip.have_prev && mode && chip.line_mode[l] && mode != chip.line_mode[l]) chip.e_bbm++;
        chip.float_run[l] = mode ? 0 : chip.float_run[l] + 1;
        if (chip.float_run[l] == 3) chip.e_float++;
        chip.line_mode[l] = mode;
    }
    uint32_t key[9] = {bpp, bpd, bnp, bnd, slp, sld, sen, prog, ref};
    bool changed = chip.have_prev && memcmp(key, chip.prev_key, sizeof key) != 0;
    chip.stable = changed ? 1 : chip.stable + 1;
    if ((nwl > 0 || chip.prev_wl) && changed) chip.e_switch++;                       // lines change with a word line on
    if (nwl > 0 && chip.prev_wl && row != chip.prev_row) chip.e_multiwl++;
    if (pstb != (nwl > 0 && prog)) chip.e_pstb++;
    if (sen && ref != 1 && ref != 2 && ref != 4) chip.e_ref++;                     // sense amplifiers need one reference
    cxxrtl::value<COLS> sp, sn;
    if (nwl > 0) {
        uint32_t blp_drv = sen ? ALL : (bpp | bpd), bln_drv = sen ? ALL : (bnp | bnd);
        if ((blp_drv & bln_drv & (slp | sld)) != ALL) chip.e_float++;                // a floating line under a word line
        if (!prog) { if (!sen || sld != ALL || slp) chip.e_readcfg++; }
        else if (sen) chip.e_progcfg++;
        if (!chip.prev_wl && chip.stable < (1 << (ts + 1))) chip.e_tsettle++;       // lines settled for T_SETTLE
        chip.wl_cycles++;
        if (!prog && sen && nwl == 1) {
            if (chip.wl_cycles <= 2) {                                              // still settling: anything
                for (int c = 0; c < COLS; c++) { setbit(sp, c, chip.noise() & 1); setbit(sn, c, chip.noise() & 1); }
            } else {
                unsigned op = ref == 2 ? 0 : ref == 4 ? 1 : 2;
                bool bp[COLS], bn[COLS]; sense_row(op, row, bp, bn);
                for (int c = 0; c < COLS; c++) { setbit(sp, c, bp[c]); setbit(sn, c, bn[c]); }
            }
        }
    } else if (chip.prev_wl) {                                                       // a word line has just turned off
        const uint32_t *k = chip.prev_key; int r = chip.prev_row;
        if (!k[7]) {
            if (chip.wl_cycles != (1 << (tr + 2))) chip.e_tsense++;
            arr.n_read++;
            if (k[8] == 2) note_read(r);                                            // mid reference
        } else {
            if (chip.wl_cycles != (1 << (tp + 2))) chip.e_tpulse++;
            bool mp_set[COLS], mn_set[COLS], mp_rst[COLS], mn_rst[COLS]; bool any_set = false, any_rst = false;
            for (int c = 0; c < COLS; c++) {
                int vp = (int)((k[0] >> c) & 1) - (int)((k[4] >> c) & 1);           // V(BL) - V(SL) in units of VPRG
                int vn = (int)((k[2] >> c) & 1) - (int)((k[4] >> c) & 1);
                mp_set[c] = vp > 0; mn_set[c] = vn > 0; mp_rst[c] = vp < 0; mn_rst[c] = vn < 0;
                any_set |= mp_set[c] || mn_set[c]; any_rst |= mp_rst[c] || mn_rst[c];
            }
            if (any_set && any_rst) chip.e_mixed++;
            // an empty pulse (revision 4.6) has no voltage across any device: its kind is told by the source lines
            unsigned op = any_rst ? 4 : any_set ? 3 : (k[4] ? 4 : 3);
            if (top.p_pk.get<bool>() != (op == 4)) chip.e_pk++;
            apply_pulse(op, r, top.p_pamp.get<unsigned>(), op == 3 ? mp_set : mp_rst, op == 3 ? mn_set : mn_rst);
        }
        chip.wl_cycles = 0;
    }
    top.p_sa__p = sp; top.p_sa__n = sn;
    memcpy(chip.prev_key, key, sizeof key); chip.have_prev = true; chip.prev_wl = nwl > 0; chip.prev_row = row;
}
static void array_eval() { macro_eval(); }
#endif

static void tick() {
    array_eval();                               // the macro model drives its outputs for this cycle
    top.p_clk.set<bool>(false); top.step();     // inputs settle while the clock is low, as they do before an edge on
                                                // silicon (needed by the latch of a clock-gating cell; revision 4.3)
    top.p_clk.set<bool>(true);  top.step();     // rising edge: registers take their new values
    top.p_clk.set<bool>(false); top.step();     // second evaluation: outputs now show the new register values
    cycles++;
}

// ---------------------------------------------------------------- trit code of the device under test
// The whole test bench is written in the two's complement code (+1 = 01, 0 = 00, -1 = 11, 10 illegal).
// When the RTL is built with TCIM_ENC_PNX (+1 = 10, 0 = 11, -1 = 01, 00 illegal), every data field is
// translated pair by pair on its way to and from the serial port, so the same tests run on both codes.
#ifdef TCIM_ENC_PNX
static const unsigned TO_DEV[4]   = {3, 2, 0, 1};      // 00 -> 11, 01 -> 10, 10 (illegal) -> 00 (illegal), 11 -> 01
static const unsigned FROM_DEV[4] = {2, 3, 1, 0};      // 00 (illegal) -> 10 (illegal), 01 -> 11, 10 -> 01, 11 -> 00
static const char *ENC_NAME = "BSD-PNX (+1 = 10, 0 = 11, -1 = 01, 00 illegal)";
#else
static const unsigned TO_DEV[4]   = {0, 1, 2, 3};
static const unsigned FROM_DEV[4] = {0, 1, 2, 3};
static const char *ENC_NAME = "two's complement (+1 = 01, 0 = 00, -1 = 11, 10 illegal)";
#endif
static uint64_t xcode(uint64_t v, const unsigned *m) { uint64_t r = 0; for (int i = 0; i < 24; i++) r |= (uint64_t)m[(v >> (2 * i)) & 3] << (2 * i); return r; }
static uint64_t to_dev(uint64_t v)   { return xcode(v, TO_DEV); }
static uint64_t from_dev(uint64_t v) { return xcode(v, FROM_DEV); }

// ---------------------------------------------------------------- serial port master
static bool last_err = false, last_irq = false;
static uint64_t spi_xfer(bool write, bool word, unsigned addr, uint64_t wdata) {
    uint8_t tx[8], rx[8] = {0};
    wdata = to_dev(wdata);
    tx[0] = (write ? 0x80 : 0) | (word ? 0x40 : 0) | (addr & 0x3f);
    for (int i = 0; i < 6; i++) tx[1 + i] = (wdata >> (8 * (5 - i))) & 0xff;
    tx[7] = 0;
    top.p_cs__n.set<bool>(false); for (int i = 0; i < 4; i++) tick();
    for (int b = 0; b < 64; b++) {
        bool bit = (tx[b / 8] >> (7 - b % 8)) & 1;
        top.p_mosi.set<bool>(bit);
        for (int i = 0; i < 3; i++) tick();
        top.p_sck.set<bool>(true);
        for (int i = 0; i < 3; i++) tick();
        if (top.p_miso.get<bool>()) rx[b / 8] |= 1 << (7 - b % 8);     // sample on the rising edge (mode 0)
        for (int i = 0; i < 3; i++) tick();
        top.p_sck.set<bool>(false);
        for (int i = 0; i < 3; i++) tick();
    }
    top.p_cs__n.set<bool>(true); for (int i = 0; i < 6; i++) tick();
    uint64_t r = 0; for (int i = 0; i < 6; i++) r = (r << 8) | rx[1 + i];
    last_err = (rx[7] >> 2) & 1; last_irq = (rx[7] >> 1) & 1;
    CHECK((rx[7] & 1) == 1, "status byte framing bit missing (0x%02x)", rx[7]);
    if (write) { CHECK(r == 0, "MISO not zero during the data bytes of a write (0x%012llx)", (unsigned long long)r); return 0; }
    return from_dev(r);
}
// raw frame of any length (for the tests of cut-short and over-long frames); returns nothing
static void spi_raw(const vector<bool> &bits) {
    top.p_cs__n.set<bool>(false); for (int i = 0; i < 4; i++) tick();
    for (bool bit : bits) {
        top.p_mosi.set<bool>(bit);
        for (int i = 0; i < 3; i++) tick();
        top.p_sck.set<bool>(true);  for (int i = 0; i < 6; i++) tick();
        top.p_sck.set<bool>(false); for (int i = 0; i < 3; i++) tick();
    }
    top.p_cs__n.set<bool>(true); for (int i = 0; i < 6; i++) tick();
}
static vector<bool> frame_bits(bool write, bool word, unsigned addr, uint64_t wdata) {
    vector<bool> v; unsigned c = (write ? 0x80 : 0) | (word ? 0x40 : 0) | (addr & 0x3f);
    wdata = to_dev(wdata);
    for (int b = 7; b >= 0; b--) v.push_back((c >> b) & 1);
    for (int b = 47; b >= 0; b--) v.push_back((wdata >> b) & 1);
    for (int b = 0; b < 8; b++) v.push_back(false);
    return v;
}
// a host that follows SPI mode 0 strictly: MOSI changes with the falling edge, MISO is sampled at the rising edge;
// half = half period of the serial clock in system clock cycles
static uint64_t spi_strict(int half, bool write, bool word, unsigned addr, uint64_t wdata, unsigned *status) {
    uint8_t tx[8], rx[8] = {0};
    wdata = to_dev(wdata);
    tx[0] = (write ? 0x80 : 0) | (word ? 0x40 : 0) | (addr & 0x3f);
    for (int i = 0; i < 6; i++) tx[1 + i] = (wdata >> (8 * (5 - i))) & 0xff;
    tx[7] = 0;
    top.p_cs__n.set<bool>(false); for (int i = 0; i < half; i++) tick();
    for (int b = 0; b < 64; b++) {
        top.p_mosi.set<bool>((tx[b / 8] >> (7 - b % 8)) & 1);
        for (int i = 0; i < half; i++) tick();
        if (top.p_miso.get<bool>()) rx[b / 8] |= 1 << (7 - b % 8);
        top.p_sck.set<bool>(true);  for (int i = 0; i < half; i++) tick();
        top.p_sck.set<bool>(false);
    }
    for (int i = 0; i < half; i++) tick();
    top.p_cs__n.set<bool>(true); for (int i = 0; i < 6; i++) tick();
    uint64_t r = 0; for (int i = 0; i < 6; i++) r = (r << 8) | rx[1 + i];
    *status = rx[7];
    return write ? r : from_dev(r);
}
static void wr_tryte(unsigned a, uint64_t d) { spi_xfer(true, false, a, d); }
static void wr_word(unsigned a, uint64_t d)  { spi_xfer(true, true, a, d); }
static uint64_t rd_tryte(unsigned a) { return spi_xfer(false, false, a, 0) & 0xfff; }
static uint64_t rd_word(unsigned a)  { return spi_xfer(false, true, a, 0); }

// ---------------------------------------------------------------- trit helpers (two's complement code)
static unsigned enc(int t) { return t > 0 ? 1u : (t < 0 ? 3u : 0u); }
static int dec(unsigned c) { return c == 1 ? 1 : (c == 3 ? -1 : 0); }
static uint64_t pack(const int *t, int n) { uint64_t v = 0; for (int i = 0; i < n; i++) v |= (uint64_t)enc(t[i]) << (2 * i); return v; }
// the same, but every 0 is sent as the illegal code 10, which the device must read as 0
static uint64_t pack_illegal(const int *t, int n) { uint64_t v = 0; for (int i = 0; i < n; i++) v |= (uint64_t)(t[i] ? enc(t[i]) : 2u) << (2 * i); return v; }
static uint64_t int_to_tryte(int v) {                  // balanced ternary, 6 trits
    int t[6];
    for (int i = 0; i < 6; i++) { int r = ((v % 3) + 3) % 3; if (r == 2) { t[i] = -1; v = (v + 1) / 3; } else { t[i] = r; v = (v - r) / 3; } }
    return pack(t, 6);
}
static int tryte_to_int(uint64_t x) { int v = 0, w = 1; for (int i = 0; i < 6; i++) { v += w * dec((x >> (2 * i)) & 3); w *= 3; } return v; }

static const int EN = 1, IE = 1 << 2, MODE = 1 << 4, GO = 1 << 6;     // '+' in trit 0, 1, 2, 3
static unsigned stat() { return (unsigned)rd_tryte(1); }
static unsigned last_stat = 0;       // status read by the last poll of wait_done (that read clears DONE)
static bool wait_done(int max_polls = 400) {
    for (int i = 0; i < max_polls; i++) { unsigned s = stat(); last_stat = s; if (!(s & 1) ) return true; }
    return false;
}

// ---- revision 4.6: SEC register (+3) and timing of commands to the cycle (the interrupt line marks DONE)
static const int ZSKIP = 1, VARPROG = 1 << 2, NOSHUF = 1 << 4, LOCK = 1 << 6;
static unsigned sec = 0;                    // what the test bench last wrote to SEC (before LOCK)
static void set_sec(unsigned v) { wr_tryte(3, v); sec = v; }
static uint64_t last_cmd_cycles = 0;       // clock cycles from the end of the command frame to the rising interrupt
static bool timed(unsigned addr, uint64_t data) {   // tryte write that starts a command; IE must be set in CTRL
    stat();                                 // DONE of an earlier command cleared, so the interrupt line is low
    spi_xfer(true, false, addr, data);
    uint64_t c0 = cycles; bool up = false;
    for (int i = 0; i < 400000 && !up; i++) { tick(); up = top.p_irq.get<bool>(); }
    last_cmd_cycles = cycles - c0;
    return up;
}

static int W[ROWS][COLS];
static uint64_t prog_cycles = 0; static int prog_timed = 0; static uint64_t prog_cycles_bad = 0;   // constant-time check
static bool program_row(int r, const int *w, int *iters = nullptr) {
    uint64_t p0 = arr.n_pulse, q0 = arr.n_pulse_real, v0 = arr.n_read;
    arr.tgt = w; arr.exp_row = r; arr.seq_set = arr.seq_rst = 0;
    arr.amp_err = arr.order_err = arr.overpulse = arr.wrong_dev = arr.empty_pulse = arr.wrong_row = 0;
    wr_tryte(40, int_to_tryte(r)); wr_word(44, pack(w, COLS));
    bool ok;
    if (!(sec & VARPROG)) {                 // constant time: every program command must last the same number of cycles
        wr_tryte(0, EN | IE);
        ok = timed(48, enc(+1));
        if (prog_timed++ == 0) prog_cycles = last_cmd_cycles;
        else if (last_cmd_cycles != prog_cycles) prog_cycles_bad++;
        wr_tryte(0, EN);
    } else { wr_tryte(48, enc(+1)); ok = wait_done(); }
    unsigned s = stat();
    int it = tryte_to_int(rd_tryte(49));
    arr.tgt = nullptr; arr.exp_row = -1;
    CHECK(it == (int)(arr.n_pulse_real - q0), "PITER %d differs from the %d device-selecting pulses the array received (row %d)", it, (int)(arr.n_pulse_real - q0), r);
    if (!(sec & VARPROG)) {
        CHECK(arr.n_pulse - p0 == 42, "constant-time programming: %d pulses instead of 21 + 21 (row %d)", (int)(arr.n_pulse - p0), r);
        CHECK(arr.n_read - v0 == 44, "constant-time programming: %d verify reads instead of 22 + 22 (row %d)", (int)(arr.n_read - v0), r);
    }
    CHECK(arr.amp_err == 0, "pulse amplitude did not start at 0 and rise by one per pulse (row %d, %d pulses out of sequence)", r, (int)arr.amp_err);
    CHECK(arr.order_err == 0, "reset pulse after a set pulse (row %d)", r);
    CHECK(arr.overpulse == 0, "pulse on a device that had already passed verify (row %d, %d times)", r, (int)arr.overpulse);
    CHECK(arr.wrong_dev == 0, "pulse on a device that must not change (row %d, %d times)", r, (int)arr.wrong_dev);
    if (sec & VARPROG) CHECK(arr.empty_pulse == 0, "pulse with no device selected (row %d)", r);
    CHECK(arr.wrong_row == 0, "pulse on another row than %d", r);
    if (iters) *iters = it;
    return ok && !((s >> 4) & 3);
}
static void product(const int *x, int *y, bool analog = false) {
    for (int k = 0; k < 3; k++) wr_word(4 + 4 * k, pack(x + 24 * k, 24));
    wr_tryte(0, EN | (analog ? MODE : 0) | GO);
    CHECK(wait_done(), "product did not finish");
    CHECK((last_stat >> 2) & 1, "DONE not set at the end of a product");      // revision 4.2: also for an all-zero input
    for (int c = 0; c < COLS; c++) y[c] = tryte_to_int(rd_tryte(16 + c));
}

static vector<vector<int>> load(const string &f) {
    vector<vector<int>> m; ifstream in(f); string line;
    while (getline(in, line)) { istringstream ss(line); vector<int> row; int v; while (ss >> v) row.push_back(v); if (!row.empty()) m.push_back(row); }
    return m;
}

int main(int argc, char **argv) {
    string vec = argc > 1 ? argv[1] : "tb/vectors";
    fail_fast = getenv("TB_FAIL_FAST") != nullptr;
    setvbuf(stdout, nullptr, _IOLBF, 0);
#ifdef TCIM_CHIP
    if (const char *cfg = getenv("TB_CFG")) sscanf(cfg, "%u,%u,%u", &chip.ts, &chip.tp, &chip.tr);
    printf("chip build: controller configuration ts %u tp %u tr %u\n", chip.ts, chip.tp, chip.tr);
#endif
    arr.init();
    top.p_rst__n.set<bool>(false); top.p_cs__n.set<bool>(true); top.p_sck.set<bool>(false); top.p_mosi.set<bool>(false);
    for (int i = 0; i < 5; i++) tick();
    top.p_rst__n.set<bool>(true); for (int i = 0; i < 5; i++) tick();
#ifdef TCIM_CHIP_TIES                                  // gate-level run of tcim_chip_digital: the pad-control constants
    CHECK(top.p_tie__hi.get<unsigned>() == 0x1fffu, "tie_hi = 0x%x instead of 0x1fff", top.p_tie__hi.get<unsigned>());
    CHECK(top.p_tie__lo.get<unsigned>() == 0u, "tie_lo = 0x%x instead of 0", top.p_tie__lo.get<unsigned>());
#endif

    // ---- 1. registers
    printf("trit code of the device under test: %s\n", ENC_NAME);
    printf("1. register access\n");
    {   // after reset every register holds zero trits; the whole 48-bit field is checked, so the trits a register
        // does not use must be zero trits as well (in BSD-PNX a field of 0 bits would be 24 illegal pairs)
        for (unsigned a : {0u, 1u, 2u, 3u, 40u, 49u, 50u}) CHECK(spi_xfer(false, false, a, 0) == 0, "tryte register %u not zero after reset", a);
        for (unsigned a = 16; a < 40; a++)        CHECK(spi_xfer(false, false, a, 0) == 0, "Y%u not zero after reset", a - 16);
        for (unsigned a : {4u, 8u, 12u, 44u, 52u}) CHECK(spi_xfer(false, true, a, 0) == 0, "word register %u not zero after reset", a);
        CHECK(spi_xfer(false, false, 41, 0) == 0 && last_err, "unmapped address 41: data not zero or error flag missing");
        CHECK(spi_xfer(false, false, 53, 0) == 0 && last_err, "unmapped address 53: data not zero or error flag missing");
        rd_tryte(52); CHECK(last_err, "tryte access to MARG not flagged");
        rd_word(3);   CHECK(last_err, "word access to SEC not flagged");
    }
    CHECK(rd_tryte(0) == 0, "CTRL not zero after reset");
    wr_tryte(0, EN);                   CHECK(rd_tryte(0) == (uint64_t)EN, "CTRL EN readback");
    wr_tryte(0, EN | IE);              CHECK(rd_tryte(0) == (uint64_t)(EN | IE), "CTRL IE readback");
    wr_tryte(0, EN | MODE);            CHECK(rd_tryte(0) == (uint64_t)(EN | MODE), "CTRL MODE readback");   // found missing
    wr_tryte(0, EN);                   CHECK(rd_tryte(0) == (uint64_t)EN, "CTRL MODE cleared");          // 11 Oct 2026
    uniform_int_distribution<int> tri(-1, 1);
    for (int k = 0; k < 3; k++) { int t[24]; for (auto &v : t) v = tri(rng); wr_word(4 + 4 * k, pack(t, 24)); CHECK(rd_word(4 + 4 * k) == pack(t, 24), "X%d readback", k); }
    for (int v : {0, 1, -1, 5, 71, -40, 364, -364}) { wr_tryte(40, int_to_tryte(v)); CHECK(tryte_to_int(rd_tryte(40)) == v, "PROW readback %d", v); }
    wr_tryte(2, int_to_tryte(3)); CHECK(tryte_to_int(rd_tryte(2)) == 3, "TILE readback");
    rd_word(5);  CHECK(last_err, "misaligned word read not flagged");
    rd_tryte(41); CHECK(last_err, "unmapped tryte read not flagged");
    rd_tryte(4); CHECK(last_err, "tryte access to a word register not flagged");
    rd_tryte(1); CHECK(!last_err, "valid access flagged as error");

    // ---- 2. programming with verify, and read-back
    printf("2. programming all %d rows with verify\n", ROWS);
    int max_it = 0; long sum_it = 0;
    for (int r = 0; r < ROWS; r++) {
        for (int c = 0; c < COLS; c++) W[r][c] = tri(rng);
        int it; bool ok = program_row(r, W[r], &it);
        CHECK(ok, "row %d failed to program", r);
        max_it = max(max_it, it); sum_it += it;
    }
    printf("   pulses per row: mean %.1f, max %d\n", (double)sum_it / ROWS, max_it);
    CHECK(prog_timed == ROWS && prog_cycles_bad == 0, "constant-time programming: %d of %d program commands differ from %llu cycles",
          (int)prog_cycles_bad, prog_timed, (unsigned long long)prog_cycles);
    printf("   constant time: every program command %llu cycles (21 + 21 pulse steps; pulses selecting a device as above)\n", (unsigned long long)prog_cycles);
    for (int r = 0; r < ROWS; r++) for (int c = 0; c < COLS; c++) {
        bool lp = arr.ip[r][c] >= 42.0, ln = arr.in[r][c] >= 42.0, hp = arr.ip[r][c] <= 6.0, hn = arr.in[r][c] <= 6.0;
        CHECK((W[r][c] == 1 ? lp : hp) && (W[r][c] == -1 ? ln : hn), "device state after programming r%d c%d", r, c);
    }
    for (int r = 0; r < ROWS; r++) {
        wr_tryte(40, int_to_tryte(r)); wr_word(44, 0); wr_tryte(48, enc(-1)); CHECK(wait_done(), "read-back stuck");
        uint64_t d = rd_word(44);
        CHECK(d == pack(W[r], COLS), "read-back row %d", r);
    }

    // ---- 3. digital products
    printf("3. digital products against the exact dot product\n");
    int x[ROWS], y[COLS];
    auto exact = [&](const int *xv, int c) { int s = 0; for (int r = 0; r < ROWS; r++) s += xv[r] * W[r][c]; return s; };
    // revision 4.6 default: fixed latency. Every product reads all 72 rows exactly once, in rotated order from a
    // start row that changes between products, with no idle cycle between reads, and lasts the same number of cycles
    {
        uint64_t dur0 = 0; int dur_bad = 0, starts[ROWS] = {0};
        for (int n = 0; n < 150; n++) {
            for (int r = 0; r < ROWS; r++) x[r] = (n == 0) ? 1 : (n == 1) ? -1 : (n == 2) ? 0 : (n < 20) ? ((r % (n - 1)) ? 0 : tri(rng)) : tri(rng);
            for (int k = 0; k < 3; k++) wr_word(4 + 4 * k, pack(x + 24 * k, 24));
            uint64_t r0 = arr.n_read;
            for (auto &v : arr.row_reads) v = 0;
            arr.last_read_row = -1; arr.order_breaks = 0;
            arr.gap_mon = true; arr.seen_req = false; arr.low_run = 0; arr.gaps = 0;
            uint64_t first0 = arr.n_read;
            CHECK(timed(0, EN | IE | GO), "product %d did not finish", n);
            arr.gap_mon = false;
            uint64_t d = last_cmd_cycles; if (n == 0) dur0 = d; else if (d != dur0) dur_bad++;
            CHECK((stat() >> 2) & 1, "DONE not set at the end of product %d", n);
            for (int c = 0; c < COLS; c++) y[c] = tryte_to_int(rd_tryte(16 + c));
            for (int c = 0; c < COLS; c++) CHECK(y[c] == exact(x, c), "product %d column %d: got %d expected %d", n, c, y[c], exact(x, c));
            CHECK(arr.n_read - r0 == (uint64_t)ROWS, "fixed-latency product %d: %d row reads instead of 72", n, (int)(arr.n_read - r0));
            int once = 0; for (int r = 0; r < ROWS; r++) once += (arr.row_reads[r] == 1);
            CHECK(once == ROWS, "fixed-latency product %d: %d rows not read exactly once", n, ROWS - once);
            CHECK(arr.order_breaks == 0, "fixed-latency product %d: rows not read in rotated order (%d breaks)", n, (int)arr.order_breaks);
            CHECK(arr.gaps == 0, "product %d: request line low for %d cycles between row reads", n, (int)arr.gaps);
            (void)first0;
        }
        wr_tryte(0, EN);
        CHECK(dur_bad == 0, "fixed-latency products of different length: %d of 149 differ from %llu cycles", dur_bad, (unsigned long long)dur0);
        printf("   fixed latency: 150 products of %llu cycles each (inputs 0 to 72 non-zero)\n", (unsigned long long)dur0);
    }
    {   // start rows: they must vary (rotation from the LFSR); with NOSHUF every product starts at row 0.
        // ACT (+50): parity of the dummy accumulators; it must change from product to product (they run)
        int distinct = 0; bool seen[ROWS] = {false}; int act_changes = 0; uint64_t act_prev = rd_tryte(50);
        for (int n = 0; n < 40; n++) {
            for (int r = 0; r < ROWS; r++) x[r] = tri(rng);
            arr.last_read_row = -1; arr.order_breaks = 0; for (auto &v : arr.row_reads) v = 0;
            int before[ROWS]; for (int r = 0; r < ROWS; r++) before[r] = 0;
            uint64_t r0 = arr.n_read; product(x, y); (void)r0;
            // the start row is the row after the one break, or row 0 if there is none (first read row = last row + 1)
            int start = (arr.last_read_row + 1) % ROWS;
            if (!seen[start]) { seen[start] = true; distinct++; }
            for (int c = 0; c < COLS; c++) CHECK(y[c] == exact(x, c), "shuffled product %d column %d", n, c);
            uint64_t a = rd_tryte(50); if (a != act_prev) act_changes++; act_prev = a;
            CHECK(a == 0 || a == (uint64_t)enc(+1), "ACT reads 0x%llx", (unsigned long long)a);
        }
        CHECK(distinct >= 10, "only %d different start rows in 40 products", distinct);
        CHECK(act_changes >= 5, "dummy accumulators: ACT changed only %d times in 40 products", act_changes);
        set_sec(NOSHUF);
        CHECK(rd_tryte(3) == (uint64_t)NOSHUF, "SEC NOSHUF readback");
        for (int n = 0; n < 5; n++) {
            for (int r = 0; r < ROWS; r++) x[r] = tri(rng);
            arr.last_read_row = -1; arr.order_breaks = 0;
            product(x, y);
            CHECK(arr.last_read_row == ROWS - 1 && arr.order_breaks == 0, "NOSHUF: product %d not read from row 0 in order", n);
            for (int c = 0; c < COLS; c++) CHECK(y[c] == exact(x, c), "NOSHUF product %d column %d", n, c);
        }
        set_sec(0);
        printf("   start rows: %d different in 40 products; NOSHUF: from row 0\n", distinct);
    }
    // opt-in zero-skipping (SEC.ZSKIP, revision 4.2 behaviour): exactly one read per row with a non-zero input
    set_sec(ZSKIP);
    CHECK(rd_tryte(3) == (uint64_t)ZSKIP, "SEC ZSKIP readback");
    for (int n = 0; n < 150; n++) {
        for (int r = 0; r < ROWS; r++) x[r] = (n == 0) ? 1 : (n == 1) ? -1 : (n == 2) ? 0 : tri(rng);
        uint64_t r0 = arr.n_read; int nnz = 0; for (int r = 0; r < ROWS; r++) nnz += (x[r] != 0);
        arr.gap_mon = true; arr.seen_req = false; arr.low_run = 0; arr.gaps = 0;
        product(x, y);
        arr.gap_mon = false;
        for (int c = 0; c < COLS; c++) CHECK(y[c] == exact(x, c), "product %d column %d: got %d expected %d", n, c, y[c], exact(x, c));
        // revision 4.2: exactly one read per row with a non-zero input, and no idle cycle between two reads
        CHECK(arr.n_read - r0 == (uint64_t)nnz, "product %d: %d row reads for %d non-zero inputs", n, (int)(arr.n_read - r0), nnz);
        CHECK(arr.gaps == 0, "product %d: request line low for %d cycles between row reads", n, (int)arr.gaps);
    }
    set_sec(0);
    // interrupt
    wr_tryte(0, EN | IE);
    for (int k = 0; k < 3; k++) wr_word(4 + 4 * k, pack(x + 24 * k, 24));
    wr_tryte(0, EN | IE | GO);
    // (revision 4.6: a fixed-latency product reads all 72 rows: 2,126 cycles with the slowest chip controller setting)
    for (int i = 0; i < 20000 && !top.p_irq.get<bool>(); i++) tick();
    CHECK(top.p_irq.get<bool>(), "interrupt not raised after a product");
    rd_tryte(0); CHECK(last_irq, "interrupt not reported in the serial status byte");
    stat(); for (int i = 0; i < 4; i++) tick();
    CHECK(!top.p_irq.get<bool>(), "interrupt not cleared by reading STAT");
    rd_tryte(0); CHECK(!last_irq, "serial status byte still reports an interrupt");
    wr_tryte(0, EN);

    // ---- 4. analog mode raw counts
    printf("4. analog-mode raw counts\n");
#ifdef TCIM_CHIP
    for (int n = 0; n < 10; n++) {                     // no converter on the chip: zero counts, no array access, no SAT
        for (int r = 0; r < ROWS; r++) x[r] = tri(rng);
        uint64_t p0 = arr.n_pulse, r0 = arr.n_read;
        product(x, y, true);
        for (int c = 0; c < COLS; c++) CHECK(y[c] == 0, "chip analog product %d column %d: got %d instead of 0", n, c, y[c]);
        CHECK(!((last_stat >> 4) & 0xf), "chip analog product %d: SAT or WERR set", n);
        CHECK(arr.n_pulse == p0 && arr.n_read == r0, "chip analog product %d touched the array", n);
    }
    for (int n = 0; n < 0; n++) {
#else
    for (int n = 0; n < 40; n++) {
#endif
        for (int r = 0; r < ROWS; r++) x[r] = tri(rng);
        product(x, y, true);
        for (int c = 0; c < COLS; c++) {
            double dp = 0, dn = 0;
            for (int r = 0; r < ROWS; r++) { double d = arr.ip[r][c] - arr.in[r][c]; if (x[r] > 0) dp += d; if (x[r] < 0) dn += d; }
            long e = lround(4.0 * dp / 40.74) - lround(4.0 * dn / 40.74);
            if (e > 364) e = 364; if (e < -364) e = -364;
            CHECK(y[c] == e, "analog count %d column %d: got %d expected %ld", n, c, y[c], e);
            CHECK(abs(y[c] - 4 * exact(x, c)) <= 16, "analog count far from 4 x exact: %d vs %d", y[c], 4 * exact(x, c));
        }
    }
    wr_tryte(0, EN);

    // ---- 5. error paths
    printf("5. error paths\n");
    { int w[COLS] = {0}; uint64_t p0 = arr.n_pulse, r0 = arr.n_read;
      wr_tryte(40, int_to_tryte(72)); wr_word(44, pack(w, COLS)); wr_tryte(48, enc(+1)); wait_done();
      CHECK((stat() >> 4) & 1, "row index 72 accepted"); CHECK(arr.n_pulse == p0 && arr.n_read == r0, "array accessed for row index 72");
      wr_tryte(48, enc(-1)); wait_done();
      CHECK((stat() >> 4) & 1, "read-back of row index 72 accepted"); CHECK(arr.n_read == r0, "array read for row index 72"); }
    { arr.ip[13][5] = 43.0; arr.in[13][5] = 43.0;        // read-back of a row with an invalid cell: flagged, and the trit reads 0
      wr_tryte(40, int_to_tryte(13)); wr_word(44, 0); wr_tryte(48, enc(-1)); CHECK(wait_done(), "read-back stuck");
      CHECK((stat() >> 4) & 1, "invalid cell not reported by read-back");
      int exp[COLS]; for (int c = 0; c < COLS; c++) exp[c] = W[13][c]; exp[5] = 0;
      CHECK(rd_word(44) == pack(exp, COLS), "read-back of a row with an invalid cell"); arr.force(13, 5, W[13][5]);
      wr_tryte(48, enc(-1)); CHECK(wait_done(), "read-back stuck"); CHECK(!((stat() >> 4) & 1), "WERR not cleared by the next read-back");
      CHECK(rd_word(44) == pack(W[13], COLS), "read-back row 13 after repair"); }
    { int w[COLS]; for (auto &v : w) v = 1; arr.stuck_p[5][7] = true; int it; bool ok = program_row(5, w, &it);
      CHECK(!ok, "stuck device not reported"); CHECK(it >= 21, "stuck device: too few pulses (%d)", it);
      CHECK(arr.seq_set == 21, "stuck device: %d set pulses instead of the full ladder of 21", arr.seq_set);
      arr.stuck_p[5][7] = false; ok = program_row(5, W[5], &it); CHECK(ok, "row 5 could not be re-programmed"); }
    { arr.ip[9][3] = 43.0; arr.in[9][3] = 43.0;         // invalid cell: both devices in LRS
      for (int r = 0; r < ROWS; r++) x[r] = (r == 9); product(x, y);
      CHECK((stat() >> 4) & 1, "invalid cell not reported"); CHECK(y[3] == 0, "cell with both devices in LRS not counted as 0 (got %d)", y[3]);
      arr.force(9, 3, W[9][3]); 
      product(x, y); CHECK(!((stat() >> 4) & 1), "WERR not cleared by the next GO"); CHECK(y[3] == W[9][3], "cell (9,3) after repair"); }
    { int w[COLS] = {0}; uint64_t p0 = arr.n_pulse; wr_tryte(40, int_to_tryte(-1)); wr_word(44, pack(w, COLS)); wr_tryte(48, enc(+1)); wait_done();
      CHECK((stat() >> 4) & 1, "row index -1 accepted"); CHECK(arr.n_pulse == p0, "pulses issued for row index -1"); }
    for (int mode = 0; mode < 2; mode++) {   // variable: the command ends after the reset phase; constant: the set phase
      set_sec(mode ? VARPROG : 0);           // still runs, with 21 empty pulses and no device-selecting set pulse
      int w[COLS]; for (int c = 0; c < COLS; c++) w[c] = W[6][c]; w[2] = -1;          // BL+ device of column 2 must become HRS
      arr.ip[6][2] = 43.6; arr.stuck_rst_p[6][2] = true; uint64_t q0 = arr.n_pulse_real; int it; bool ok = program_row(6, w, &it);
      CHECK(!ok, "device that never resets not reported"); CHECK(it == 21, "stuck reset: %d pulses instead of 21", it);
      if (mode) CHECK(arr.seq_rst == 21 && arr.seq_set == 0, "stuck reset: %d reset and %d set pulses instead of 21 and 0", arr.seq_rst, arr.seq_set);
      else CHECK(arr.seq_rst == 21 && arr.seq_set == 21 && arr.n_pulse_real - q0 == 21, "constant time, stuck reset: %d reset, %d set pulses, %d selecting a device (21, 21, 21 expected)", arr.seq_rst, arr.seq_set, (int)(arr.n_pulse_real - q0));
      arr.stuck_rst_p[6][2] = false; ok = program_row(6, W[6], &it); CHECK(ok, "row 6 could not be re-programmed"); }
    set_sec(0);


    // ---- 5b. directed tests added in the audit of revision 3
    printf("5b. directed tests: read reference, saturation, interrupt enable, busy and enable guards\n");
    {   // a device between the read reference (25 uA) and the set target (42 uA) must read as LRS; one below it as HRS
        int save = W[11][4];
        for (int r = 0; r < ROWS; r++) x[r] = (r == 11);
        arr.ip[11][4] = 30.0; arr.in[11][4] = 2.9; product(x, y); CHECK(y[4] == 1, "30 uA device not read as LRS (got %d)", y[4]);
        arr.ip[11][4] = 20.0; arr.in[11][4] = 2.9; product(x, y); CHECK(y[4] == 0, "20 uA device not read as HRS (got %d)", y[4]);
        arr.ip[11][4] = 2.9; arr.in[11][4] = 30.0; product(x, y); CHECK(y[4] == -1, "30 uA device on BL- not read as -1 (got %d)", y[4]);
        CHECK(!((stat() >> 4) & 1), "WERR set by a valid cell");
        arr.force(11, 4, save);
    }
    {   // a device left between the reset target (6 uA) and the read reference (25 uA) must fail the reset verify and be
        // pulsed: a reset verify against the read reference would pass it (fault found surviving on 11 October 2026)
        int w[COLS]; for (int c = 0; c < COLS; c++) w[c] = W[11][c]; w[4] = 0;
        arr.force(11, 4, 0); arr.ip[11][4] = 15.0; int it; bool ok = program_row(11, w, &it);
        CHECK(ok, "row 11 with a 15 uA device not programmed");
        CHECK(arr.ip[11][4] <= arr.i_rst, "15 uA device passed the reset verify (%.1f uA after programming)", arr.ip[11][4]);
        CHECK(it >= 1, "15 uA device: no reset pulse");
        ok = program_row(11, W[11], &it); CHECK(ok, "row 11 could not be re-programmed");
    }
#ifndef TCIM_CHIP                                      // analog converter paths: not on the chip
    {   // analog saturation: P - N beyond the tryte range must clip to +/-364 and set SAT; a normal product clears SAT
        for (int r = 0; r < ROWS; r++) x[r] = (r % 2) ? 1 : -1;
        arr.adc_force = true; arr.sum_phase = 0; arr.adc_p = 300; arr.adc_n = -300; product(x, y, true);
        for (int c = 0; c < COLS; c++) CHECK(y[c] == 364, "positive saturation column %d: %d", c, y[c]);
        CHECK((stat() >> 6) & 1, "SAT not set on positive overflow");
        arr.sum_phase = 0; arr.adc_p = -200; arr.adc_n = 200; product(x, y, true);
        for (int c = 0; c < COLS; c++) CHECK(y[c] == -364, "negative saturation column %d: %d", c, y[c]);
        CHECK((stat() >> 6) & 1, "SAT not set on negative overflow");
        arr.sum_phase = 0; arr.adc_p = 183; arr.adc_n = -182; product(x, y, true);
        for (int c = 0; c < COLS; c++) CHECK(y[c] == 364, "365 not clipped, column %d: %d", c, y[c]);
        CHECK((stat() >> 6) & 1, "SAT not set at +365");
        arr.sum_phase = 0; arr.adc_p = -183; arr.adc_n = 182; product(x, y, true);
        for (int c = 0; c < COLS; c++) CHECK(y[c] == -364, "-365 not clipped, column %d: %d", c, y[c]);
        arr.sum_phase = 0; arr.adc_p = -182; arr.adc_n = 182; product(x, y, true);
        for (int c = 0; c < COLS; c++) CHECK(y[c] == -364, "exact negative full scale column %d: %d", c, y[c]);
        CHECK(!((stat() >> 6) & 1), "SAT set at exactly -364");
        arr.sum_phase = 0; arr.adc_p = 182; arr.adc_n = -182; product(x, y, true);
        for (int c = 0; c < COLS; c++) CHECK(y[c] == 364, "exact full scale column %d: %d", c, y[c]);
        CHECK(!((stat() >> 6) & 1), "SAT set at exactly +364");
        arr.sum_phase = 0; arr.adc_p = 100; arr.adc_n = 37; product(x, y, true);
        for (int c = 0; c < COLS; c++) CHECK(y[c] == 63, "plain difference column %d: %d", c, y[c]);
        arr.adc_force = false;
        product(x, y, true); CHECK(!((stat() >> 6) & 1), "SAT not cleared by the next product");
    }
#endif
    {   // interrupt enable: with IE = 0 the interrupt line must stay low although DONE is set
        wr_tryte(0, EN);
        for (int k = 0; k < 3; k++) wr_word(4 + 4 * k, pack(x + 24 * k, 24));
        wr_tryte(0, EN | GO);
        bool seen = false; for (int i = 0; i < 3000; i++) { tick(); seen |= top.p_irq.get<bool>(); }
        CHECK(!seen, "interrupt raised with IE = 0");
        CHECK((stat() >> 2) & 1, "DONE not set after a product");
    }
    {   // guards: while a product runs, writes to X and a second GO must be ignored; BUSY must read as set
        int xa[ROWS], xb[ROWS], ya[COLS];
        for (int r = 0; r < ROWS; r++) { xa[r] = tri(rng); xb[r] = -xa[r]; }
        xa[0] = 1; xb[0] = -1;
        product(xa, ya);                                              // reference result with the normal macro speed
        arr.delay = 400;                                              // slow macro: the product now lasts ~20,000 cycles
        for (int k = 0; k < 3; k++) wr_word(4 + 4 * k, pack(xa + 24 * k, 24));
        wr_tryte(0, EN | GO);
        CHECK(stat() & 1, "BUSY not set during a product");
        for (int k = 0; k < 3; k++) wr_word(4 + 4 * k, pack(xb + 24 * k, 24));      // must be ignored
        wr_tryte(40, int_to_tryte(33));                                               // PROW write, must be ignored
        wr_tryte(0, EN | GO);                                                         // second GO, must be ignored
        wr_tryte(0, EN | MODE);                                                       // MODE must not change while busy
        CHECK(rd_tryte(0) == (uint64_t)EN, "MODE changed while BUSY");
        CHECK(stat() & 1, "product ended early or was restarted");
        CHECK(wait_done(4000), "slow product did not finish");
        arr.delay = 2;
        for (int c = 0; c < COLS; c++) CHECK(tryte_to_int(rd_tryte(16 + c)) == ya[c], "result changed by writes during BUSY, column %d", c);
        CHECK(rd_word(4) == pack(xa, 24), "X0 was overwritten during BUSY");
        CHECK(tryte_to_int(rd_tryte(40)) != 33, "PROW was overwritten during BUSY");
    }
    {   // enable: with EN = 0 neither GO nor a program command may start anything
        uint64_t p0 = arr.n_pulse, r0 = arr.n_read;
        wr_tryte(0, 0);
        int w[COLS]; for (auto &v : w) v = 1;
        wr_tryte(40, int_to_tryte(2)); wr_word(44, pack(w, COLS)); wr_tryte(48, enc(+1));
        for (int i = 0; i < 400; i++) tick();
        wr_tryte(0, GO);                                                              // GO without EN
        for (int i = 0; i < 400; i++) tick();
        wr_tryte(48, enc(-1));                                                        // read-back without EN
        for (int i = 0; i < 400; i++) tick();
        CHECK(arr.n_pulse == p0 && arr.n_read == r0, "array accessed with EN = 0");
        CHECK(!(stat() & 1), "BUSY set with EN = 0");
        wr_tryte(0, EN);
        wr_tryte(40, int_to_tryte(2)); wr_word(44, 0); wr_tryte(48, enc(-1)); CHECK(wait_done(), "read-back stuck");
        CHECK(rd_word(44) == pack(W[2], COLS), "row 2 changed while EN = 0");
    }

    // ---- 5c. second round of the audit: illegal trit code, exhaustive conversions, flags, interrupt, serial frames
    printf("5c. illegal code, exhaustive conversions, flag and interrupt behaviour, serial frame lengths\n");
    {   // the illegal code 10 must be read as 0 in X, in PDATA and in PROW
        for (int n = 0; n < 6; n++) {
            for (int r = 0; r < ROWS; r++) x[r] = tri(rng);
            for (int k = 0; k < 3; k++) wr_word(4 + 4 * k, pack_illegal(x + 24 * k, 24));
            wr_tryte(0, EN | GO); CHECK(wait_done(), "product did not finish");
            for (int c = 0; c < COLS; c++) { int v = tryte_to_int(rd_tryte(16 + c)); CHECK(v == exact(x, c), "X with code 10: column %d got %d expected %d", c, v, exact(x, c)); }
        }
        uint64_t p0 = arr.n_pulse_real;
        wr_tryte(40, int_to_tryte(20)); wr_word(44, pack_illegal(W[20], COLS)); wr_tryte(48, enc(+1)); CHECK(wait_done(), "program stuck");
        CHECK(!((stat() >> 4) & 1), "PDATA with code 10: WERR");
        CHECK(arr.n_pulse_real == p0, "PDATA with code 10: %d pulses on a row that already held these weights", (int)(arr.n_pulse_real - p0));
        for (int c = 0; c < COLS; c++) {
            bool lp = arr.ip[20][c] >= 42.0, ln = arr.in[20][c] >= 42.0, hp = arr.ip[20][c] <= 6.0, hn = arr.in[20][c] <= 6.0;
            CHECK((W[20][c] == 1 ? lp : hp) && (W[20][c] == -1 ? ln : hn), "PDATA with code 10: device state r20 c%d", c);
        }
        wr_tryte(40, enc(+1) | (2u << 2) | (2u << 10)); wr_word(44, 0); wr_tryte(48, enc(-1)); CHECK(wait_done(), "read-back stuck");
        CHECK(!((stat() >> 4) & 1), "PROW with code 10 not read as row 1");
        CHECK(rd_word(44) == pack(W[1], COLS), "PROW with code 10: wrong row read back");
    }
#ifndef TCIM_CHIP                                      // analog converter paths: not on the chip
    {   // every value a result register can hold, -364 ... +364, through the binary to balanced-ternary conversion
        arr.adc_force = true; arr.adc_n = 0;
        for (int v = -364; v <= 364; v++) {
            arr.sum_phase = 0; arr.adc_p = v;
            wr_tryte(0, EN | MODE | GO); CHECK(wait_done(), "product did not finish");
            int col = (v + 364) % COLS; int g = tryte_to_int(rd_tryte(16 + col));
            CHECK(g == v, "result value %d read as %d", v, g);
        }
        arr.adc_force = false;
    }
#endif
    {   // every row index a tryte can hold outside 0 ... 71 must be refused without touching the array
        uint64_t p0 = arr.n_pulse, r0 = arr.n_read; int bad = 0;
        for (int v = -364; v <= 364; v++) {
            if (v >= 0 && v < ROWS) continue;
            wr_tryte(40, int_to_tryte(v)); wr_tryte(48, enc(-1)); wait_done();
            if (!((stat() >> 4) & 1)) bad++;
        }
        CHECK(bad == 0, "%d row indices outside 0..71 were accepted for read-back", bad);
        for (int v : {-364, -73, -1, 72, 73, 81, 127, 128, 199, 200, 243, 364}) {
            int w[COLS]; for (auto &q : w) q = 1;
            wr_tryte(40, int_to_tryte(v)); wr_word(44, pack(w, COLS)); wr_tryte(48, enc(+1)); wait_done();
            CHECK((stat() >> 4) & 1, "row index %d accepted for programming", v);
            CHECK(tryte_to_int(rd_tryte(49)) == 0, "PITER not zero after a refused program command");
        }
        CHECK(arr.n_pulse == p0 && arr.n_read == r0, "array accessed for a row index outside 0..71");
    }
#ifndef TCIM_CHIP                                      // analog converter paths: not on the chip
    {   // SAT describes the last command: a digital product and a program command must clear it
        for (int r = 0; r < ROWS; r++) x[r] = (r % 2) ? 1 : -1;
        arr.adc_force = true; arr.sum_phase = 0; arr.adc_p = 300; arr.adc_n = -300; product(x, y, true);
        CHECK((stat() >> 6) & 1, "SAT not set");
        arr.adc_force = false;
        product(x, y); CHECK(!((stat() >> 6) & 1), "SAT not cleared by a digital product");
        for (int c = 0; c < COLS; c++) CHECK(y[c] == exact(x, c), "digital product after a saturated analog one, column %d", c);
        arr.adc_force = true; arr.sum_phase = 0; arr.adc_p = 300; arr.adc_n = -300; product(x, y, true);
        arr.adc_force = false;
        wr_tryte(40, int_to_tryte(3)); wr_word(44, 0); wr_tryte(48, enc(-1)); CHECK(wait_done(), "read-back stuck");
        CHECK(!((stat() >> 6) & 1), "SAT not cleared by a read-back command");
    }
#endif
    {   // interrupt: GO clears DONE without a STAT read; a failed command can be acknowledged by reading STAT;
        // a write to STAT is not a read
        wr_tryte(0, EN | IE);
        for (int k = 0; k < 3; k++) wr_word(4 + 4 * k, pack(x + 24 * k, 24));
        wr_tryte(0, EN | IE | GO);
        for (int i = 0; i < 3000 && !top.p_irq.get<bool>(); i++) tick();
        CHECK(top.p_irq.get<bool>(), "interrupt not raised");
        wr_tryte(1, 0x555); wr_tryte(17, 0x555); wr_tryte(49, 0x555);        // writes to read-only registers
        CHECK(top.p_irq.get<bool>(), "DONE cleared by a write to STAT");
        CHECK(!last_err, "write to a mapped read-only register flagged as a bus error");
        CHECK(tryte_to_int(rd_tryte(17)) == exact(x, 1), "Y[1] changed by a write");
        CHECK(top.p_irq.get<bool>(), "DONE cleared by reading another register");
        arr.delay = 400;
        wr_tryte(0, EN | IE | GO);                                                    // no STAT read in between
        for (int i = 0; i < 20; i++) tick();
        CHECK(!top.p_irq.get<bool>(), "DONE not cleared by GO");
        bool up = false; for (int i = 0; i < 80000 && !up; i++) { tick(); up = top.p_irq.get<bool>(); }
        CHECK(up, "interrupt not raised after the slow product");
        arr.delay = 2;
        CHECK((stat() >> 2) & 1, "DONE not readable"); for (int i = 0; i < 4; i++) tick();
        CHECK(!top.p_irq.get<bool>(), "interrupt not cleared by reading STAT");
        wr_tryte(40, int_to_tryte(72)); wr_tryte(48, enc(-1));                        // a command that fails
        for (int i = 0; i < 200 && !top.p_irq.get<bool>(); i++) tick();
        CHECK(top.p_irq.get<bool>(), "interrupt not raised after a failed command");
        unsigned s1 = stat(); for (int i = 0; i < 4; i++) tick();
        CHECK(((s1 >> 2) & 1) && ((s1 >> 4) & 1), "DONE and WERR not both reported after a failed command");
        CHECK(!top.p_irq.get<bool>(), "interrupt after a failed command not cleared by reading STAT");
        CHECK((stat() >> 4) & 1, "WERR lost after the first STAT read");
        wr_tryte(0, EN);
    }
    {   // serial frames of the wrong length
        wr_tryte(2, int_to_tryte(3));
        auto f7 = frame_bits(true, false, 2, int_to_tryte(7));
        vector<bool> cut(f7.begin(), f7.begin() + 55); spi_raw(cut);
        CHECK(tryte_to_int(rd_tryte(2)) == 3, "a frame cut short after 55 bits wrote the register");
        vector<bool> cut8(f7.begin(), f7.begin() + 9); spi_raw(cut8);
        CHECK(tryte_to_int(rd_tryte(2)) == 3, "a frame cut short after 9 bits wrote the register");
        auto f5 = frame_bits(true, false, 2, int_to_tryte(5));
        vector<bool> lng(f5); for (int i = 0; i < 64; i++) lng.push_back(false); lng.insert(lng.end(), f7.begin(), f7.end());
        spi_raw(lng);                                                                 // 192 clocks with CS low
        CHECK(tryte_to_int(rd_tryte(2)) == 5, "clocks after the 8-byte frame were decoded as another frame");
        vector<bool> two(f5); two.insert(two.end(), f7.begin(), f7.end()); spi_raw(two);        // 128 clocks
        CHECK(tryte_to_int(rd_tryte(2)) == 5, "a second frame without CS rising was executed");
        wr_tryte(2, int_to_tryte(-4)); CHECK(tryte_to_int(rd_tryte(2)) == -4, "normal frame after the over-long ones");
        wr_tryte(2, 0);
    }
    {   // serial clock speed: at clk / 8 a host that samples MISO on the rising edge must read what it wrote
        uint64_t keep[3]; for (int k = 0; k < 3; k++) keep[k] = rd_word(4 + 4 * k);
        for (int n = 0; n < 60; n++) {
            int t[24]; for (auto &v : t) v = tri(rng);
            unsigned st = 0, a = 4 + 4 * (n % 3);
            spi_strict(4, true, true, a, pack(t, 24), &st);
            uint64_t r = spi_strict(4, false, true, a, 0, &st);
            CHECK(r == pack(t, 24) && (st & 5) == 1, "serial clock at clk / 8: read-back differs or status byte 0x%02x", st);
        }
        for (int k = 0; k < 3; k++) wr_word(4 + 4 * k, keep[k]);
    }
    // ---- 5d. revision 4.6 security options
    printf("5d. security options: SEC register, margin check, LOCK\n");
    {
        for (unsigned v : {0u, (unsigned)ZSKIP, (unsigned)VARPROG, (unsigned)NOSHUF, (unsigned)(ZSKIP | VARPROG | NOSHUF)}) {
            set_sec(v); CHECK(rd_tryte(3) == v, "SEC readback 0x%x", v);
        }
        set_sec(0);
        wr_tryte(3, 2u); CHECK(rd_tryte(3) == 0, "SEC: illegal code 10 in ZSKIP read as +");
        // SEC is ignored while a command runs
        for (int r = 0; r < ROWS; r++) x[r] = tri(rng);
        arr.delay = 400;
        for (int k = 0; k < 3; k++) wr_word(4 + 4 * k, pack(x + 24 * k, 24));
        wr_tryte(0, EN | GO);
        wr_tryte(3, ZSKIP | VARPROG);
        CHECK(rd_tryte(3) == 0, "SEC written while BUSY");
        CHECK(wait_done(4000), "slow product did not finish");
        arr.delay = 2;
        for (int c = 0; c < COLS; c++) CHECK(tryte_to_int(rd_tryte(16 + c)) == exact(x, c), "slow product with SEC write, column %d", c);
    }
    {   // margin check (PCMD t0 = 0, t1 = +): three reads, no pulse; clean after programming
        const int r = 30;
        int w[COLS]; for (int c = 0; c < COLS; c++) w[c] = (c % 3 == 0) ? 1 : (c % 3 == 1) ? -1 : 0;
        CHECK(program_row(r, w), "row 30 for the margin check");
        for (int c = 0; c < COLS; c++) W[r][c] = w[c];
        auto mchk = [&](uint64_t *marg, uint64_t *pd, int *reads, int *pulses) {
            uint64_t p0 = arr.n_pulse, r0 = arr.n_read;
            wr_tryte(40, int_to_tryte(r)); wr_word(44, 0); wr_tryte(48, (uint64_t)enc(+1) << 2);
            CHECK(wait_done(), "margin check stuck");
            unsigned st = stat();
            *marg = rd_word(52); *pd = rd_word(44); *reads = (int)(arr.n_read - r0); *pulses = (int)(arr.n_pulse - p0);
            return (bool)((st >> 4) & 1);
        };
        uint64_t mg, pd; int nr, np;
        bool we = mchk(&mg, &pd, &nr, &np);
        CHECK(!we && mg == 0, "margin check of a freshly programmed row: WERR %d, MARG %llx", we, (unsigned long long)mg);
        CHECK(pd == pack(w, COLS), "margin check: PDATA is not the row read");
        CHECK(nr == 3 && np == 0, "margin check: %d reads and %d pulses instead of 3 and 0", nr, np);
        // drift: a low-resistance device of column 0 at 30 uA (above the read reference 25, below the set target 42),
        // a high-resistance device of column 4 at 10 uA (below the read reference, above the reset target 6)
        double k0 = arr.ip[r][0], k4 = arr.ip[r][4];
        arr.ip[r][0] = 30.0; arr.ip[r][4] = 10.0;
        we = mchk(&mg, &pd, &nr, &np);
        int exp[COLS] = {0}; exp[0] = 1; exp[4] = 1;
        CHECK(we, "margin check: drifted devices not reported by WERR");
        CHECK(mg == pack(exp, COLS), "margin check: MARG %llx instead of columns 0 and 4", (unsigned long long)mg);
        CHECK(pd == pack(w, COLS), "margin check: drifted devices still read correctly, PDATA wrong");
        arr.ip[r][0] = 25.5; arr.ip[r][4] = 6.5;     // just inside the read decision, outside the margins: still flagged
        we = mchk(&mg, &pd, &nr, &np); CHECK(we && mg == pack(exp, COLS), "margin check near the read reference");
        arr.in[r][1] = 26.0; arr.ip[r][1] = 2.9;     // column 1 (-1): BL- device at 26 uA
        we = mchk(&mg, &pd, &nr, &np); exp[1] = 1; CHECK(we && mg == pack(exp, COLS), "margin check of a BL- device");
        // every margin check clears MARG when it starts, also one that is refused (row 72) and so never reads
        // (found by the mutation test on 4 November 2026: the clear was otherwise hidden by the first margin read)
        wr_tryte(40, int_to_tryte(72)); wr_tryte(48, (uint64_t)enc(+1) << 2); wait_done();
        CHECK(rd_word(52) == 0, "MARG not cleared by a refused margin check: %llx", (unsigned long long)rd_word(52));
        arr.ip[r][0] = k0; arr.ip[r][4] = k4; arr.force(r, 1, -1);
        we = mchk(&mg, &pd, &nr, &np); CHECK(!we && mg == 0, "margin check after repair");
        // refused: row outside 0..71, and without EN
        uint64_t p0 = arr.n_pulse, r0 = arr.n_read;
        wr_tryte(40, int_to_tryte(72)); wr_tryte(48, (uint64_t)enc(+1) << 2); wait_done();
        CHECK((stat() >> 4) & 1, "margin check of row 72 accepted");
        wr_tryte(0, 0); wr_tryte(40, int_to_tryte(r)); wr_tryte(48, (uint64_t)enc(+1) << 2);
        for (int i = 0; i < 400; i++) tick();
        CHECK(!(stat() & 1), "margin check started without EN");
        wr_tryte(0, EN);
        CHECK(arr.n_pulse == p0 && arr.n_read == r0, "array accessed by a refused margin check");
        // t0 = 0 and t1 not + : no command
        wr_tryte(40, int_to_tryte(r)); wr_tryte(48, (uint64_t)enc(-1) << 2); for (int i = 0; i < 400; i++) tick();
        CHECK(arr.n_read == r0 && !(stat() & 1), "PCMD 0, - started a command");
    }
    {   // LOCK: set-only, clears the options, ignores later writes, hides PITER; only a reset clears it
        set_sec(ZSKIP | VARPROG | NOSHUF);
        wr_tryte(3, LOCK | ZSKIP | VARPROG);        // the options written with LOCK are cleared as well
        CHECK(rd_tryte(3) == (uint64_t)LOCK, "LOCK: SEC reads 0x%llx instead of LOCK alone", (unsigned long long)rd_tryte(3));
        wr_tryte(3, ZSKIP | VARPROG | NOSHUF); CHECK(rd_tryte(3) == (uint64_t)LOCK, "LOCK: options written after LOCK");
        wr_tryte(3, 0); CHECK(rd_tryte(3) == (uint64_t)LOCK, "LOCK cleared by a write");
        sec = 0;
        // locked: products have fixed latency, programming constant time, PITER reads 0
        for (int r = 0; r < ROWS; r++) x[r] = (r < 3) ? 1 : 0;
        uint64_t r0 = arr.n_read; product(x, y);
        CHECK(arr.n_read - r0 == (uint64_t)ROWS, "LOCK: product read %d rows instead of 72", (int)(arr.n_read - r0));
        for (int c = 0; c < COLS; c++) CHECK(y[c] == exact(x, c), "LOCK product column %d", c);
        int w[COLS]; for (int c = 0; c < COLS; c++) w[c] = -W[31][c];
        uint64_t p0 = arr.n_pulse, q0 = arr.n_pulse_real;
        wr_tryte(40, int_to_tryte(31)); wr_word(44, pack(w, COLS)); wr_tryte(48, enc(+1)); CHECK(wait_done(), "LOCK: program stuck");
        CHECK(!((stat() >> 4) & 1), "LOCK: programming failed");
        CHECK(arr.n_pulse - p0 == 42 && arr.n_pulse_real > q0, "LOCK: %d pulses (42 expected), %d selecting", (int)(arr.n_pulse - p0), (int)(arr.n_pulse_real - q0));
        CHECK(rd_tryte(49) == 0, "LOCK: PITER not hidden");
        { bool any = false; for (int n = 0; n < 6; n++) { for (int r = 0; r < ROWS; r++) x[r] = tri(rng); product(x, y); any |= rd_tryte(50) != 0; }
          CHECK(!any, "LOCK: ACT not hidden"); }
        for (int c = 0; c < COLS; c++) W[31][c] = w[c];
        // revision 4.7: under LOCK read-back is refused (WERR, no array access, PDATA kept), and a margin check runs but
        // does not write the weights into PDATA
        { int k[COLS]; for (int c = 0; c < COLS; c++) k[c] = (c % 3) - 1;
          wr_word(44, pack(k, COLS)); uint64_t rr = arr.n_read;
          wr_tryte(48, enc(-1)); CHECK(wait_done(), "LOCK: read-back command stuck");
          CHECK((stat() >> 4) & 1, "LOCK: read-back not refused (no WERR)");
          CHECK(arr.n_read == rr, "LOCK: read-back reached the array");
          CHECK(rd_word(44) == pack(k, COLS), "LOCK: read-back changed PDATA");
          wr_tryte(48, (uint64_t)enc(+1) << 2); CHECK(wait_done(), "LOCK: margin check stuck");
          CHECK(arr.n_read > rr, "LOCK: margin check did not run");
          CHECK(rd_word(44) == pack(k, COLS), "LOCK: margin check wrote the weights into PDATA");
          CHECK(rd_word(52) == 0, "LOCK: margin check flagged a freshly programmed row"); }
        // reset clears LOCK (and every register); the array keeps its weights
        top.p_rst__n.set<bool>(false); for (int i = 0; i < 5; i++) tick(); top.p_rst__n.set<bool>(true); for (int i = 0; i < 5; i++) tick();
        CHECK(rd_tryte(3) == 0, "LOCK not cleared by reset");
        CHECK(rd_word(52) == 0 && rd_tryte(49) == 0 && rd_tryte(50) == 0, "MARG, PITER or ACT not zero after reset");
        wr_tryte(0, EN);
        wr_tryte(40, int_to_tryte(31)); wr_tryte(48, enc(-1)); CHECK(wait_done(), "read-back stuck");
        CHECK(rd_word(44) == pack(W[31], COLS), "LOCK: row 31 read-back after reset");
    }
    {   // all weights still in place after the directed tests
        for (int r = 0; r < ROWS; r++) {
            wr_tryte(40, int_to_tryte(r)); wr_word(44, 0); wr_tryte(48, enc(-1)); CHECK(wait_done(), "read-back stuck");
            CHECK(!((stat() >> 4) & 1), "WERR in the final read-back of row %d", r);
            CHECK(rd_word(44) == pack(W[r], COLS), "row %d changed during the directed tests", r);
        }
    }

    // ---- 6. network inference
    printf("6. ternary digits network through the RTL\n");
    auto w1 = load(vec + "/net_w1.txt"), w2 = load(vec + "/net_w2.txt"), xs = load(vec + "/net_x.txt"), meta = load(vec + "/net_meta.txt");
    if (w1.size() == ROWS && !xs.empty()) {
        int theta = meta[0][0]; size_t ns = xs.size();
        vector<array<int, 72>> z1(ns);
        set_sec(VARPROG);                            // programming time: stop-at-verify here (constant time is covered above)
        for (int k = 0; k < 3; k++) {                    // layer 1: three tiles of 24 hidden units
            for (int r = 0; r < ROWS; r++) { int w[COLS]; for (int c = 0; c < COLS; c++) w[c] = w1[r][24 * k + c]; CHECK(program_row(r, w), "net program"); }
            for (size_t s = 0; s < ns; s++) { for (int r = 0; r < ROWS; r++) x[r] = xs[s][r]; product(x, y); for (int c = 0; c < COLS; c++) z1[s][24 * k + c] = y[c]; }
        }
        for (int r = 0; r < ROWS; r++) { int w[COLS] = {0}; for (int c = 0; c < 10; c++) w[c] = w2[r][c]; CHECK(program_row(r, w), "net program"); }
        int correct = 0, agree = 0, mism = 0;
        for (size_t s = 0; s < ns; s++) {
            int h[ROWS];
            for (int j = 0; j < ROWS; j++) {
                int e = 0; for (int r = 0; r < ROWS; r++) e += xs[s][r] * w1[r][j];
                if (z1[s][j] != e) mism++;
                h[j] = z1[s][j] > theta ? 1 : (z1[s][j] < -theta ? -1 : 0);
            }
            h[0] = 1;
            product(h, y);
            int best = 0; for (int c = 1; c < 10; c++) if (y[c] > y[best]) best = c;
            if (best == xs[s][72]) correct++;
            if (best == xs[s][73]) agree++;
        }
        printf("   %zu samples: RTL correct %d, software correct %d, same class as software %d, layer-1 mismatches %d\n", ns, correct, meta[0][2], agree, mism);
        CHECK(mism == 0, "layer-1 results differ from the exact values (%d)", mism);
        CHECK(agree == (int)ns, "RTL class differs from software for %zu samples", ns - agree);
        CHECK(correct == meta[0][2], "accuracy differs from software");
        set_sec(0);
    } else printf("   vectors not found in %s, skipped\n", vec.c_str());

#ifdef TCIM_CHIP
    printf("chip (cfg ts %u tp %u tr %u): electrical violations: short %llu, two word lines %llu, floating %llu, switching under a word line %llu,\n"
           "   read setup %llu, program setup %llu, strobe %llu, reference %llu, sense time %llu, pulse time %llu, settle time %llu, mixed pulse %llu, pk %llu, break-before-make %llu, flt order %llu\n",
           chip.ts, chip.tp, chip.tr, (unsigned long long)chip.e_short, (unsigned long long)chip.e_multiwl, (unsigned long long)chip.e_float,
           (unsigned long long)chip.e_switch, (unsigned long long)chip.e_readcfg, (unsigned long long)chip.e_progcfg, (unsigned long long)chip.e_pstb,
           (unsigned long long)chip.e_ref, (unsigned long long)chip.e_tsense, (unsigned long long)chip.e_tpulse, (unsigned long long)chip.e_tsettle,
           (unsigned long long)chip.e_mixed, (unsigned long long)chip.e_pk, (unsigned long long)chip.e_bbm, (unsigned long long)chip.e_skew);
    CHECK(chip.total() == 0, "%llu electrical or timing violations at the macro interface", (unsigned long long)chip.total());
#endif
    CHECK(arr.bad_row == 0, "the array was given a row index outside 0..71 (%llu times)", (unsigned long long)arr.bad_row);
    CHECK(prog_cycles_bad == 0, "constant-time programming: %d program commands of another length (all %d timed)", (int)prog_cycles_bad, prog_timed);
    printf("array operations: %llu reads, %llu pulses, %llu sums; %llu clock cycles\n", (unsigned long long)arr.n_read, (unsigned long long)arr.n_pulse, (unsigned long long)arr.n_sum, (unsigned long long)cycles);
    printf("%d checks, %d failures\n%s\n", checks, errors, errors ? "TEST FAILED" : "TEST PASSED");
    return errors ? 1 : 0;
}
