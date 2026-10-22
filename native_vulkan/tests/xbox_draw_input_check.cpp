#include "shift_xbox_draw_input.hpp"

#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

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

}  // namespace

int main() {
    shift::xbox::DecodedIndexedDraw input{};
    std::string error;
    require(shift::xbox::decode_captured_draw_indx(
                kCapturedPacket, sizeof(kCapturedPacket), &input, &error),
            "captured retail packet was rejected");
    require(input.topology == shift::xbox::PrimitiveTopology::TriangleList,
            "primitive topology changed");
    require(input.index_count == 6, "index count changed");
    require(input.index_guest_address == 0x0975D7B0u, "index base changed");
    require(input.index_type_bits == 16, "index type changed");
    require(input.index_endian_mode == 1, "index endian mode changed");
    require(input.index_byte_length == 12, "index range changed");

    const uint32_t captured_vertex_descriptor[] = {0x0975DFD3u, 0x10000032u};
    shift::xbox::CapturedVertexFetch vertex_fetch{};
    require(shift::xbox::decode_captured_vertex_fetch(
                captured_vertex_descriptor, &vertex_fetch, &error),
            "captured vertex-fetch descriptor was rejected");
    require(vertex_fetch.guest_address == 0x0975DFD0u,
            "captured vertex-fetch address changed");
    require(vertex_fetch.endian_mode == 2 && vertex_fetch.size_words == 12 &&
                vertex_fetch.byte_length == 48,
            "captured vertex-fetch shape changed");

    const uint8_t captured_indices[] = {
        0x00, 0x00, 0x00, 0x01, 0x00, 0x02,
        0x00, 0x02, 0x00, 0x01, 0x00, 0x03,
    };
    const std::vector<uint8_t> expected_vk_indices{
        0x00, 0x00, 0x01, 0x00, 0x02, 0x00,
        0x02, 0x00, 0x01, 0x00, 0x03, 0x00,
    };
    std::vector<uint8_t> normalized;
    require(shift::xbox::normalize_captured_buffer_bytes(
                input.index_endian_mode, captured_indices, sizeof(captured_indices),
                &normalized, &error),
            "captured 8-in-16 index bytes were rejected");
    require(normalized == expected_vk_indices,
            "captured index bytes did not normalize to Vulkan UInt16 values");

    const uint8_t captured_vertex_words[] = {
        0xBF, 0x80, 0x00, 0x00, 0xBF, 0x80, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
    };
    const std::vector<uint8_t> expected_vk_vertex_words{
        0x00, 0x00, 0x80, 0xBF, 0x00, 0x00, 0x80, 0xBF,
        0x00, 0x00, 0x00, 0x00,
    };
    require(shift::xbox::normalize_captured_buffer_bytes(
                vertex_fetch.endian_mode, captured_vertex_words,
                sizeof(captured_vertex_words),
                &normalized, &error),
            "captured 8-in-32 vertex words were rejected");
    require(normalized == expected_vk_vertex_words,
            "captured vertex words did not normalize to Vulkan float32 values");

    require(!shift::xbox::normalize_captured_buffer_bytes(
                3, captured_indices, sizeof(captured_indices), &normalized, &error),
            "uncaptured endian mode was accepted");
    require(!shift::xbox::normalize_captured_buffer_bytes(
                1, captured_indices, sizeof(captured_indices) - 1, &normalized, &error),
            "truncated 8-in-16 resource was accepted");

    uint32_t unsupported_vertex_descriptor[] = {
        captured_vertex_descriptor[0], captured_vertex_descriptor[1]};
    unsupported_vertex_descriptor[0] =
        (unsupported_vertex_descriptor[0] & 0xFFFFFFFCu) | 2u;
    require(!shift::xbox::decode_captured_vertex_fetch(
                unsupported_vertex_descriptor, &vertex_fetch, &error),
            "texture-fetch descriptor was accepted as a vertex buffer");

    uint8_t unsupported[sizeof(kCapturedPacket)];
    for (size_t i = 0; i < sizeof(kCapturedPacket); ++i) {
        unsupported[i] = kCapturedPacket[i];
    }
    unsupported[2] = 0x23;
    require(!shift::xbox::decode_captured_draw_indx(
                unsupported, sizeof(unsupported), &input, &error),
            "unsupported packet opcode was accepted");

    uint8_t disagreeing_counts[sizeof(kCapturedPacket)];
    for (size_t i = 0; i < sizeof(kCapturedPacket); ++i) {
        disagreeing_counts[i] = kCapturedPacket[i];
    }
    disagreeing_counts[9] = 0x07;
    require(!shift::xbox::decode_captured_draw_indx(
                disagreeing_counts, sizeof(disagreeing_counts), &input, &error),
            "disagreeing packet index counts were accepted");

    uint8_t unsupported_index_size[sizeof(kCapturedPacket)];
    for (size_t i = 0; i < sizeof(kCapturedPacket); ++i) {
        unsupported_index_size[i] = kCapturedPacket[i];
    }
    unsupported_index_size[10] |= 0x08;
    require(!shift::xbox::decode_captured_draw_indx(
                unsupported_index_size, sizeof(unsupported_index_size), &input, &error),
            "unsupported 32-bit index format was accepted");

    uint8_t unsupported_source[sizeof(kCapturedPacket)];
    for (size_t i = 0; i < sizeof(kCapturedPacket); ++i) {
        unsupported_source[i] = kCapturedPacket[i];
    }
    unsupported_source[11] |= 0x40;
    require(!shift::xbox::decode_captured_draw_indx(
                unsupported_source, sizeof(unsupported_source), &input, &error),
            "unsupported immediate-index source was accepted");

    uint8_t unsupported_endian[sizeof(kCapturedPacket)];
    for (size_t i = 0; i < sizeof(kCapturedPacket); ++i) {
        unsupported_endian[i] = kCapturedPacket[i];
    }
    unsupported_endian[16] = 0x80;
    require(!shift::xbox::decode_captured_draw_indx(
                unsupported_endian, sizeof(unsupported_endian), &input, &error),
            "uncaptured index endian mode was accepted");

    require(!shift::xbox::decode_captured_draw_indx(
                kCapturedPacket, sizeof(kCapturedPacket) - 4, &input, &error),
            "truncated packet was accepted");

    std::cout << "captured PM4_DRAW_INDX input check passed\n";
    return 0;
}
