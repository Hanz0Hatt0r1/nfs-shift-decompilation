#include "shift_xbox_draw_input.hpp"

#include <cstdlib>
#include <iostream>
#include <string>

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << message << '\n';
        std::exit(1);
    }
}

const uint8_t kCapturedPacket[] = {
    0xC0, 0x03, 0x22, 0x01,
    0x00, 0x00, 0x00, 0x00,
    0x00, 0x06, 0x00, 0x04,
    0x09, 0x75, 0xD7, 0xB0,
    0x40, 0x00, 0x00, 0x06,
};

const shift::xbox::CapturedIndexBinding kCapturedBinding{
    0,  // Int16
    1,  // Captured Xbox endian mode; conversion is not performed here.
    6,
    0x0975D7B0u,
    12,
};

}  // namespace

int main() {
    shift::xbox::DecodedIndexedDraw input{};
    std::string error;
    require(shift::xbox::decode_captured_draw_indx(
                kCapturedPacket, sizeof(kCapturedPacket), kCapturedBinding, &input, &error),
            "captured retail packet was rejected");
    require(input.topology == shift::xbox::PrimitiveTopology::TriangleList,
            "primitive topology changed");
    require(input.index_count == 6, "index count changed");
    require(input.index_guest_address == 0x0975D7B0u, "index base changed");
    require(input.index_type_bits == 16, "index type changed");
    require(input.index_endian_mode == 1, "index endian mode changed");
    require(input.index_byte_length == 12, "index range changed");

    uint8_t unsupported[sizeof(kCapturedPacket)];
    for (size_t i = 0; i < sizeof(kCapturedPacket); ++i) {
        unsupported[i] = kCapturedPacket[i];
    }
    unsupported[2] = 0x23;
    require(!shift::xbox::decode_captured_draw_indx(
                unsupported, sizeof(unsupported), kCapturedBinding, &input, &error),
            "unsupported packet opcode was accepted");

    uint8_t disagreeing_counts[sizeof(kCapturedPacket)];
    for (size_t i = 0; i < sizeof(kCapturedPacket); ++i) {
        disagreeing_counts[i] = kCapturedPacket[i];
    }
    disagreeing_counts[19] = 0x07;
    require(!shift::xbox::decode_captured_draw_indx(
                disagreeing_counts, sizeof(disagreeing_counts), kCapturedBinding, &input, &error),
            "disagreeing packet index counts were accepted");

    auto mismatched = kCapturedBinding;
    mismatched.guest_address++;
    require(!shift::xbox::decode_captured_draw_indx(
                kCapturedPacket, sizeof(kCapturedPacket), mismatched, &input, &error),
            "mismatched index binding was accepted");

    require(!shift::xbox::decode_captured_draw_indx(
                kCapturedPacket, sizeof(kCapturedPacket) - 4, kCapturedBinding, &input, &error),
            "truncated packet was accepted");

    std::cout << "captured PM4_DRAW_INDX input check passed\n";
    return 0;
}
