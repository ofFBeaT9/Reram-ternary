// The test bench of roadmap revision 3, kept for comparison only (60,401 checks). The one change is that CHECK stops at
// the first failure. Used to measure how many injected faults that test bench missed:
//   TB_SRC=tb/rev3/tb_tcim_rev3.cc TB_TAG=_rev3 python3 tb/mutation_test.py && python3 tb/mutation_merge.py _rev3
// tb_tcim.cc - self-checking test bench for tcim_top, built on the CXXRTL model that Yosys generates
// from the RTL. The analog macro is replaced by a behavioural array with per-device currents,
// random switching thresholds and pulse-and-verify behaviour.
//
// Tests: register access, misaligned access, row programming with verify, read-back, digital products
// against the exact dot product, analog-mode raw counts, error paths, and inference of the ternary
// digits network (tb/vectors) whose results must equal the software reference sample by sample.
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cmath>
#include <vector>
#include <array>
#include <random>
#include <string>
#include <fstream>
#include <sstream>
#include "tcim_top.h"

using namespace std;
static const int ROWS = 72, COLS = 24, ACCW = 10;
static cxxrtl_design::p_tcim__top top;
static uint64_t cycles = 0;
static int errors = 0, checks = 0;
static mt19937 rng(12345);

#define CHECK(cond, ...) do { checks++; if (!(cond)) { errors++; printf("  FAIL: "); printf(__VA_ARGS__); printf("\nTEST FAILED\n"); fflush(stdout); exit(1); } } while (0)

// ---------------------------------------------------------------- behavioural array
struct Array {
    double ip[ROWS][COLS], in[ROWS][COLS];        // device read currents, uA at 0.2 V
    int thr_set_p[ROWS][COLS], thr_set_n[ROWS][COLS], thr_rst_p[ROWS][COLS], thr_rst_n[ROWS][COLS];
    bool stuck_p[ROWS][COLS];                     // device that never sets (for the error-path test)
    double i_mid = 25.0, i_set = 42.0, i_rst = 6.0;
    int busy = 0; bool pending = false;
    uint64_t n_read = 0, n_pulse = 0, n_sum = 0;
    normal_distribution<double> lrs{43.59, 1.55}, hrs{2.85, 1.85};
    double sample_hrs() { double v; do { v = hrs(rng); } while (v < 0.05 || v > 5.9); return v; }
    double sample_lrs() { return lrs(rng); }
    void init() {
        uniform_int_distribution<int> ts(4, 14), tr(2, 12);
        for (int r = 0; r < ROWS; r++) for (int c = 0; c < COLS; c++) {
            ip[r][c] = sample_hrs(); in[r][c] = sample_hrs();
            thr_set_p[r][c] = ts(rng); thr_set_n[r][c] = ts(rng); thr_rst_p[r][c] = tr(rng); thr_rst_n[r][c] = tr(rng);
            stuck_p[r][c] = false;
        }
    }
    void force(int r, int c, int w) { ip[r][c] = (w == 1) ? 43.6 : 2.9; in[r][c] = (w == -1) ? 43.6 : 2.9; }
};
static Array arr;

template <size_t N> static bool getbit(const cxxrtl::value<N> &v, size_t i) { return (v.data[i / 32] >> (i % 32)) & 1; }
template <size_t N> static void setbit(cxxrtl::value<N> &v, size_t i, bool b) { if (b) v.data[i / 32] |= (1u << (i % 32)); else v.data[i / 32] &= ~(1u << (i % 32)); }

static void array_eval() {       // called once per clock cycle, before the rising edge
    top.p_arr__ack.set<bool>(false);
    bool req = top.p_arr__req.get<bool>();
    if (!arr.pending) {
        if (req) { arr.pending = true; arr.busy = 2; }      // two cycles of "analog" time
        return;
    }
    if (--arr.busy > 0) return;
    arr.pending = false;
    unsigned op = top.p_arr__op.get<unsigned>();
    unsigned row = top.p_arr__row.get<unsigned>();
    unsigned amp = top.p_arr__amp.get<unsigned>();
    auto mp = top.p_arr__mask__p, mn = top.p_arr__mask__n;
    cxxrtl::value<COLS> sp, sn; cxxrtl::value<COLS * ACCW> adc;
    if (op == 0 || op == 1 || op == 2) {
        double ref = (op == 0) ? arr.i_mid : (op == 1) ? arr.i_set : arr.i_rst;
        for (int c = 0; c < COLS; c++) {
            bool bp = (op == 1) ? (arr.ip[row][c] >= ref) : (arr.ip[row][c] > ref);
            bool bn = (op == 1) ? (arr.in[row][c] >= ref) : (arr.in[row][c] > ref);
            setbit(sp, c, bp); setbit(sn, c, bn);
        }
        arr.n_read++;
    } else if (op == 3 || op == 4) {
        for (int c = 0; c < COLS; c++) {
            if (getbit(mp, c)) {
                if (op == 3) { if ((int)amp >= arr.thr_set_p[row][c] && !arr.stuck_p[row][c]) arr.ip[row][c] = arr.sample_lrs(); }
                else         { if ((int)amp >= arr.thr_rst_p[row][c]) arr.ip[row][c] = arr.sample_hrs(); }
            }
            if (getbit(mn, c)) {
                if (op == 3) { if ((int)amp >= arr.thr_set_n[row][c]) arr.in[row][c] = arr.sample_lrs(); }
                else         { if ((int)amp >= arr.thr_rst_n[row][c]) arr.in[row][c] = arr.sample_hrs(); }
            }
        }
        arr.n_pulse++;
    } else if (op == 5) {
        auto rm = top.p_arr__row__mask;
        for (int c = 0; c < COLS; c++) {
            double d = 0;
            for (int r = 0; r < ROWS; r++) if (getbit(rm, r)) d += arr.ip[r][c] - arr.in[r][c];
            long cnt = lround(4.0 * d / (43.59 - 2.85));          // four converter counts per result step
            if (cnt > 511) cnt = 511; if (cnt < -512) cnt = -512;
            for (int b = 0; b < ACCW; b++) setbit(adc, c * ACCW + b, (cnt >> b) & 1);
        }
        arr.n_sum++;
    }
    top.p_arr__sa__p = sp; top.p_arr__sa__n = sn; top.p_arr__adc = adc;
    top.p_arr__ack.set<bool>(true);
}

static void tick() {
    array_eval();                               // the macro model drives its outputs for this cycle
    top.p_clk.set<bool>(true);  top.step();     // rising edge: registers take their new values
    top.p_clk.set<bool>(false); top.step();     // second evaluation: outputs now show the new register values
    cycles++;
}

// ---------------------------------------------------------------- serial port master
static bool last_err = false, last_irq = false;
static uint64_t spi_xfer(bool write, bool word, unsigned addr, uint64_t wdata) {
    uint8_t tx[8], rx[8] = {0};
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
    return r;
}
static void wr_tryte(unsigned a, uint64_t d) { spi_xfer(true, false, a, d); }
static void wr_word(unsigned a, uint64_t d)  { spi_xfer(true, true, a, d); }
static uint64_t rd_tryte(unsigned a) { return spi_xfer(false, false, a, 0) & 0xfff; }
static uint64_t rd_word(unsigned a)  { return spi_xfer(false, true, a, 0); }

// ---------------------------------------------------------------- trit helpers (two's complement code)
static unsigned enc(int t) { return t > 0 ? 1u : (t < 0 ? 3u : 0u); }
static int dec(unsigned c) { return c == 1 ? 1 : (c == 3 ? -1 : 0); }
static uint64_t pack(const int *t, int n) { uint64_t v = 0; for (int i = 0; i < n; i++) v |= (uint64_t)enc(t[i]) << (2 * i); return v; }
static uint64_t int_to_tryte(int v) {                  // balanced ternary, 6 trits
    int t[6];
    for (int i = 0; i < 6; i++) { int r = ((v % 3) + 3) % 3; if (r == 2) { t[i] = -1; v = (v + 1) / 3; } else { t[i] = r; v = (v - r) / 3; } }
    return pack(t, 6);
}
static int tryte_to_int(uint64_t x) { int v = 0, w = 1; for (int i = 0; i < 6; i++) { v += w * dec((x >> (2 * i)) & 3); w *= 3; } return v; }

static const int EN = 1, IE = 1 << 2, MODE = 1 << 4, GO = 1 << 6;     // '+' in trit 0, 1, 2, 3
static unsigned stat() { return (unsigned)rd_tryte(1); }
static bool wait_done(int max_polls = 400) {
    for (int i = 0; i < max_polls; i++) { unsigned s = stat(); if (!(s & 1) ) return true; }
    return false;
}

static int W[ROWS][COLS];
static bool program_row(int r, const int *w, int *iters = nullptr) {
    wr_tryte(40, int_to_tryte(r)); wr_word(44, pack(w, COLS)); wr_tryte(48, enc(+1));
    bool ok = wait_done();
    unsigned s = stat();
    if (iters) *iters = tryte_to_int(rd_tryte(49));
    return ok && !((s >> 4) & 3);
}
static void product(const int *x, int *y, bool analog = false) {
    for (int k = 0; k < 3; k++) wr_word(4 + 4 * k, pack(x + 24 * k, 24));
    wr_tryte(0, EN | (analog ? MODE : 0) | GO);
    CHECK(wait_done(), "product did not finish");
    for (int c = 0; c < COLS; c++) y[c] = tryte_to_int(rd_tryte(16 + c));
}

static vector<vector<int>> load(const string &f) {
    vector<vector<int>> m; ifstream in(f); string line;
    while (getline(in, line)) { istringstream ss(line); vector<int> row; int v; while (ss >> v) row.push_back(v); if (!row.empty()) m.push_back(row); }
    return m;
}

int main(int argc, char **argv) {
    string vec = argc > 1 ? argv[1] : "tb/vectors";
    setvbuf(stdout, nullptr, _IOLBF, 0);
    arr.init();
    top.p_rst__n.set<bool>(false); top.p_cs__n.set<bool>(true); top.p_sck.set<bool>(false); top.p_mosi.set<bool>(false);
    for (int i = 0; i < 5; i++) tick();
    top.p_rst__n.set<bool>(true); for (int i = 0; i < 5; i++) tick();

    // ---- 1. registers
    printf("1. register access\n");
    CHECK(rd_tryte(0) == 0, "CTRL not zero after reset");
    wr_tryte(0, EN);                   CHECK(rd_tryte(0) == (uint64_t)EN, "CTRL EN readback");
    wr_tryte(0, EN | IE);              CHECK(rd_tryte(0) == (uint64_t)(EN | IE), "CTRL IE readback");
    wr_tryte(0, EN);
    uniform_int_distribution<int> tri(-1, 1);
    for (int k = 0; k < 3; k++) { int t[24]; for (auto &v : t) v = tri(rng); wr_word(4 + 4 * k, pack(t, 24)); CHECK(rd_word(4 + 4 * k) == pack(t, 24), "X%d readback", k); }
    for (int v : {0, 1, -1, 5, 71, -40, 364, -364}) { wr_tryte(40, int_to_tryte(v)); CHECK(tryte_to_int(rd_tryte(40)) == v, "PROW readback %d", v); }
    wr_tryte(2, int_to_tryte(3)); CHECK(tryte_to_int(rd_tryte(2)) == 3, "TILE readback");
    rd_word(5);  CHECK(last_err, "misaligned word read not flagged");
    rd_tryte(3); CHECK(last_err, "unmapped tryte read not flagged");
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
    for (int n = 0; n < 150; n++) {
        for (int r = 0; r < ROWS; r++) x[r] = (n == 0) ? 1 : (n == 1) ? -1 : (n == 2) ? 0 : tri(rng);
        uint64_t c0 = cycles; product(x, y);
        for (int c = 0; c < COLS; c++) CHECK(y[c] == exact(x, c), "product %d column %d: got %d expected %d", n, c, y[c], exact(x, c));
        (void)c0;
    }
    // interrupt
    wr_tryte(0, EN | IE);
    for (int k = 0; k < 3; k++) wr_word(4 + 4 * k, pack(x + 24 * k, 24));
    wr_tryte(0, EN | IE | GO);
    for (int i = 0; i < 2000 && !top.p_irq.get<bool>(); i++) tick();
    CHECK(top.p_irq.get<bool>(), "interrupt not raised after a product");
    stat(); for (int i = 0; i < 4; i++) tick();
    CHECK(!top.p_irq.get<bool>(), "interrupt not cleared by reading STAT");
    wr_tryte(0, EN);

    // ---- 4. analog mode raw counts
    printf("4. analog-mode raw counts\n");
    for (int n = 0; n < 40; n++) {
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
    { int w[COLS] = {0}; wr_tryte(40, int_to_tryte(72)); wr_word(44, pack(w, COLS)); wr_tryte(48, enc(+1)); wait_done();
      CHECK((stat() >> 4) & 1, "row index 72 accepted"); }
    { int w[COLS]; for (auto &v : w) v = 1; arr.stuck_p[5][7] = true; int it; bool ok = program_row(5, w, &it);
      CHECK(!ok, "stuck device not reported"); CHECK(it >= 21, "stuck device: too few pulses (%d)", it);
      arr.stuck_p[5][7] = false; ok = program_row(5, W[5], &it); CHECK(ok, "row 5 could not be re-programmed"); }
    { arr.ip[9][3] = 43.0; arr.in[9][3] = 43.0;         // invalid cell: both devices in LRS
      for (int r = 0; r < ROWS; r++) x[r] = (r == 9); product(x, y);
      CHECK((stat() >> 4) & 1, "invalid cell not reported"); arr.force(9, 3, W[9][3]); }

    // ---- 6. network inference
    printf("6. ternary digits network through the RTL\n");
    auto w1 = load(vec + "/net_w1.txt"), w2 = load(vec + "/net_w2.txt"), xs = load(vec + "/net_x.txt"), meta = load(vec + "/net_meta.txt");
    if (w1.size() == ROWS && !xs.empty()) {
        int theta = meta[0][0]; size_t ns = xs.size();
        vector<array<int, 72>> z1(ns);
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
    } else printf("   vectors not found in %s, skipped\n", vec.c_str());

    printf("array operations: %llu reads, %llu pulses, %llu sums; %llu clock cycles\n", (unsigned long long)arr.n_read, (unsigned long long)arr.n_pulse, (unsigned long long)arr.n_sum, (unsigned long long)cycles);
    printf("%d checks, %d failures\n%s\n", checks, errors, errors ? "TEST FAILED" : "TEST PASSED");
    return errors ? 1 : 0;
}
