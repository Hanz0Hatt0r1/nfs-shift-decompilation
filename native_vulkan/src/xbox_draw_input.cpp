#include "shift_xbox_draw_input.hpp"

#include <utility>

namespace shift::xbox {
namespace {

constexpr uint32_t kType3Header = 0xC0000000u;
constexpr uint32_t kPacketTypeMask = 0xC0000000u;
constexpr uint32_t kPacketCountMask = 0x3FFF0000u;
constexpr uint32_t kPacketOpcodeMask = 0x0000FF00u;
constexpr uint32_t kDrawIndxOpcode = 0x22u;
constexpr uint32_t kTriangleList = 4u;
constexpr uint32_t kIndexCountMask = 0x00FFFFFFu;
constexpr uint32_t kDmaSwapModeMask = 0xC0000000u;
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
    const uint32_t source_select = (draw_initiator >> 6) & 0x3u;
    const uint32_t major_mode = (draw_initiator >> 8) & 0x3u;
    const uint32_t index_size = (draw_initiator >> 11) & 0x1u;
    const uint32_t initiator_index_count = draw_initiator >> 16;
    const uint32_t index_guest_address = read_be32(packet_bytes + 12);
    const uint32_t dma_size = read_be32(packet_bytes + 16);
    const uint32_t dma_index_count = dma_size & kIndexCountMask;
    const uint32_t dma_endian_mode = (dma_size & kDmaSwapModeMask) >> 30;

    if (primitive_type != kTriangleList) {
        return fail("unsupported captured primitive type", error);
    }
    if (source_select != 0 || major_mode != 0) {
        return fail("unsupported captured draw source or major mode", error);
    }
    if (index_size != 0 || dma_endian_mode != 1) {
        return fail("unsupported captured index format or endian mode", error);
    }
    if (!initiator_index_count || initiator_index_count != dma_index_count) {
        return fail("draw packet index counts disagree", error);
    }
    if ((dma_size & 0x3F000000u) != 0) {
        return fail("unsupported captured DMA size flags", error);
    }
    *output = DecodedIndexedDraw{
        PrimitiveTopology::TriangleList,
        initiator_index_count,
        index_guest_address,
        16,
        dma_endian_mode,
        dma_index_count * 2,
    };
    if (error) {
        error->clear();
    }
    return true;
}

bool decode_captured_vertex_fetch(
    const uint32_t descriptor_words[2],
    CapturedVertexFetch* output,
    std::string* error) {
    if (!descriptor_words || !output) {
        return fail("invalid captured vertex-fetch descriptor", error);
    }

    constexpr uint32_t kVertexFetchType = 3;
    constexpr uint32_t kCapturedVertexEndianMode = 2;
    const uint32_t fetch_type = descriptor_words[0] & 0x3u;
    const uint32_t endian_mode = descriptor_words[1] & 0x3u;
    const uint32_t size_words = (descriptor_words[1] >> 2) & 0x00FFFFFFu;
    if (fetch_type != kVertexFetchType || endian_mode != kCapturedVertexEndianMode ||
        size_words == 0) {
        return fail("unsupported captured vertex-fetch descriptor", error);
    }

    *output = CapturedVertexFetch{
        descriptor_words[0] & 0xFFFFFFFCu,
        endian_mode,
        size_words,
        size_words * 4,
    };
    if (error) {
        error->clear();
    }
    return true;
}

bool normalize_captured_buffer_bytes(
    uint32_t endian_mode,
    const uint8_t* guest_bytes,
    size_t byte_length,
    std::vector<uint8_t>* vulkan_bytes,
    std::string* error) {
    if (!guest_bytes || !vulkan_bytes || byte_length == 0) {
        return fail("invalid captured resource bytes", error);
    }

    const size_t word_bytes = endian_mode == 1 ? 2 : endian_mode == 2 ? 4 : 0;
    if (word_bytes == 0) {
        return fail("unsupported captured resource endian mode", error);
    }
    if (byte_length % word_bytes != 0) {
        return fail("captured resource length is not endian-word aligned", error);
    }

    std::vector<uint8_t> normalized(byte_length);
    for (size_t offset = 0; offset < byte_length; offset += word_bytes) {
        for (size_t byte = 0; byte < word_bytes; ++byte) {
            normalized[offset + byte] = guest_bytes[offset + word_bytes - byte - 1];
        }
    }
    *vulkan_bytes = std::move(normalized);
    if (error) {
        error->clear();
    }
    return true;
}

}  // namespace shift::xbox
