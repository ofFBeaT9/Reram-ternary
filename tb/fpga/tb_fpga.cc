// tb_fpga.cc - Verilator model of rtl/fpga/tcim_fpga_top with its serial port connected to stdin/stdout, so that
// tools/fpga_host.py --sim can run the same test as on the board.
#include "Vtcim_fpga_top.h"
#include "verilated.h"
#include <poll.h>
#include <unistd.h>
#include <deque>
#include <cstdio>

static const int DIV = 16;   // 27 MHz clock cycles per bit: the design runs on 27/2 MHz and is built with DIV=8

int main(int argc, char **argv) {
    Verilated::commandArgs(argc, argv);
    Vtcim_fpga_top *m = new Vtcim_fpga_top;
    std::deque<unsigned char> in;
    m->btn_rst_n = 1; m->uart_rx = 1; m->clk27 = 0; m->eval();
    int tx_bit = -1, tx_cnt = 0; unsigned tx_sh = 0;           // host -> FPGA
    int rx_state = -1, rx_cnt = 0, rx_bits = 0; unsigned rx_sh = 0;  // FPGA -> host
    bool eof = false; unsigned long long cyc = 0;
    // Lock step with the host, so that a run is cycle-exact and repeatable: the clock stops while the host has
    // nothing to send and no answer is outstanding (the host only sends after the previous answer arrived).
    // Answer lengths follow the protocol of rtl/fpga/tcim_fpga_top.sv.
    long owed = 0; int need_args = 0; unsigned char cur = 0;
    auto answer_len = [](unsigned char c) { return c == 0x57 ? 2 : c == 0x52 ? 8 : c == 0x45 ? 2 : c == 0x50 ? 6 : 0; };
    auto arg_len = [](unsigned char c) { return c == 0x57 ? 8 : c == 0x52 ? 2 : c == 0x45 ? 1 : 0; };
    while (true) {
        bool idle = in.empty() && tx_bit < 0 && rx_state < 0 && owed == 0 && cyc > 5000;
        if (!eof && (idle || (cyc & 255) == 0)) {
            struct pollfd p = {0, POLLIN, 0};
            while (poll(&p, 1, idle ? -1 : 0) > 0) {
                unsigned char b[256]; ssize_t n = read(0, b, sizeof b);
                if (n <= 0) { eof = true; break; }
                for (ssize_t i = 0; i < n; i++) {
                    in.push_back(b[i]);
                    if (need_args > 0) { if (--need_args == 0) owed += answer_len(cur); }
                    else { cur = b[i]; need_args = arg_len(cur); if (need_args == 0) owed += answer_len(cur); }
                }
                idle = false;
                if (n < (ssize_t)sizeof b) break;
            }
        }
        if (eof && in.empty() && tx_bit < 0 && rx_state < 0) break;
        // drive the FPGA's receive line
        // bytes are sent only after the power-on reset
        if (tx_bit < 0 && !in.empty() && cyc > 5000) { tx_sh = (1u << 9) | (in.front() << 1); in.pop_front(); tx_bit = 0; tx_cnt = 0; }
        if (tx_bit >= 0) {
            m->uart_rx = (tx_sh >> tx_bit) & 1;
            if (++tx_cnt == DIV) { tx_cnt = 0; if (++tx_bit == 10) tx_bit = -1; }
        } else m->uart_rx = 1;
        m->clk27 = 1; m->eval(); m->clk27 = 0; m->eval(); cyc++;
        // sample the FPGA's transmit line in the middle of each bit
        if (rx_state < 0) { if (!m->uart_tx) { rx_state = 0; rx_cnt = DIV / 2; rx_bits = 0; rx_sh = 0; } }
        else if (--rx_cnt == 0) {
            rx_cnt = DIV;
            if (rx_bits >= 1 && rx_bits <= 8) rx_sh |= (unsigned)m->uart_tx << (rx_bits - 1);
            if (++rx_bits == 10) { unsigned char c = rx_sh & 0xff; fwrite(&c, 1, 1, stdout); fflush(stdout); rx_state = -1; owed--; }
        }
    }
    fprintf(stderr, "tb_fpga: %llu cycles\n", cyc);
    delete m;
    return 0;
}
