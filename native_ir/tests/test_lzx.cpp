#include "shift_lzx.h"
#include <cassert>
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>

static std::vector<std::uint8_t> read_file(const char* path) {
    std::ifstream f(path, std::ios::binary);
    return {std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>()};
}

int main(int argc, char** argv) {
    if (argc != 3) return 2;
    auto packed = read_file(argv[1]);
    auto expected = read_file(argv[2]);
    std::vector<std::uint8_t> out(expected.size());
    const int rc = shift_xmem_decompress(packed.data(), packed.size(), out.data(), out.size(), expected.size());
    assert(rc == 0);
    assert(out == expected);
    std::cout << "XMem native OK packed=" << packed.size() << " decoded=" << out.size() << "\n";
    return 0;
}
