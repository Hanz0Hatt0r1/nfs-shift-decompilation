#pragma once

#include <cstddef>
#include <cstdint>
#include <string>

namespace shift::xbox {

struct CapturedIndexBinding {
    uint32_t format;
    uint32_t endian_mode;
    uint32_t index_count;
    uint32_t guest_address;
    uint64_t byte_length;
};

enum class PrimitiveTopology : uint8_t {
    TriangleList,
};

struct DecodedIndexedDraw {
    PrimitiveTopology topology;
    uint32_t index_count;
    uint32_t index_guest_address;
    uint32_t index_type_bits;
    uint32_t index_endian_mode;
    uint32_t index_byte_length;
};

// Translates only the captured PM4_DRAW_INDX form. This decodes the guest
// command into renderer inputs; it does not execute or emulate Xenos state.
bool decode_captured_draw_indx(
    const uint8_t* packet_bytes,
    size_t byte_length,
    const CapturedIndexBinding& binding,
    DecodedIndexedDraw* output,
    std::string* error);

}  // namespace shift::xbox
