#include "shift_xbox_draw_input.hpp"

#include <limits>

namespace shift::xbox {
namespace {

constexpr uint32_t kType3Header = 0xC0000000u;
constexpr uint32_t kPacketTypeMask = 0xC0000000u;
constexpr uint32_t kPacketCountMask = 0x3FFF0000u;
constexpr uint32_t kPacketOpcodeMask = 0x0000FF00u;
constexpr uint32_t kDrawIndxOpcode = 0x22u;
constexpr uint32_t kTriangleList = 4u;
constexpr uint32_t kIndexCountMask = 0x00FFFFFFu;
constexpr size_t kCapturedPacketBytes = 20;

uint32_t read_be32(const uint8_t* bytes) {
    return (static_cast<uint32_t>(bytes[0]) << 24) |
           (static_cast<uint32_t>(bytes[1]) << 16) |
           (static_cast<uint32_t>(bytes[2]) << 8) |
           static_cast<uint32_t>(bytes[3]);
}

bool fail(const char* message, std::string* error) {
    if (error) {
        *error = message;
    }
    return false;
}

}  // namespace

bool decode_captured_draw_indx(
    const uint8_t* packet_bytes,
    size_t byte_length,
    const CapturedIndexBinding& binding,
    DecodedIndexedDraw* output,
    std::string* error) {
    if (!packet_bytes || !output || byte_length < kCapturedPacketBytes) {
        return fail("truncated PM4_DRAW_INDX packet", error);
    }

    const uint32_t header = read_be32(packet_bytes);
    if ((header & kPacketTypeMask) != kType3Header ||
        ((header & kPacketOpcodeMask) >> 8) != kDrawIndxOpcode) {
        return fail("unsupported guest draw packet", error);
    }

    // The captured packet header encodes four payload dwords.
    const uint32_t payload_count = ((header & kPacketCountMask) >> 16) + 1;
    if (payload_count != 4 || byte_length != kCapturedPacketBytes) {
        return fail("unsupported PM4_DRAW_INDX payload length", error);
    }

    const uint32_t draw_initiator = read_be32(packet_bytes + 8);
    const uint32_t primitive_type = draw_initiator & 0x3Fu;
    const uint32_t initiator_index_count = draw_initiator >> 16;
    const uint32_t index_guest_address = read_be32(packet_bytes + 12);
    const uint32_t dma_size = read_be32(packet_bytes + 16);
    const uint32_t dma_index_count = dma_size & kIndexCountMask;

    if (primitive_type != kTriangleList) {
        return fail("unsupported captured primitive type", error);
    }
    if (!initiator_index_count || initiator_index_count != dma_index_count) {
        return fail("draw packet index counts disagree", error);
    }
    if (binding.format != 0 || binding.endian_mode != 1) {
        return fail("unsupported captured index format or endian mode", error);
    }
    if (binding.index_count != initiator_index_count ||
        binding.guest_address != index_guest_address) {
        return fail("draw packet does not match captured index binding", error);
    }
    if (binding.index_count > std::numeric_limits<uint32_t>::max() / 2 ||
        binding.byte_length != static_cast<uint64_t>(binding.index_count) * 2) {
        return fail("captured 16-bit index range has invalid byte length", error);
    }

    *output = DecodedIndexedDraw{
        PrimitiveTopology::TriangleList,
        initiator_index_count,
        index_guest_address,
        16,
        binding.endian_mode,
        static_cast<uint32_t>(binding.byte_length),
    };
    if (error) {
        error->clear();
    }
    return true;
}

}  // namespace shift::xbox
