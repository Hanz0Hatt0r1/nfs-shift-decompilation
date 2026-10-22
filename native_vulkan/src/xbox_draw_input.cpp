#include "shift_xbox_draw_input.hpp"

#include <limits>
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

bool decode_captured_texture_fetch(
    const uint32_t descriptor_words[6],
    CapturedTextureFetch* output,
    std::string* error) {
    if (!descriptor_words || !output) {
        return fail("invalid captured texture-fetch descriptor", error);
    }

    const uint32_t fetch_type = descriptor_words[0] & 0x3u;
    const uint32_t tiled = descriptor_words[0] >> 31;
    const uint32_t format = descriptor_words[1] & 0x3Fu;
    const uint32_t endian_mode = (descriptor_words[1] >> 6) & 0x3u;
    const uint32_t stacked = (descriptor_words[1] >> 10) & 0x1u;
    const uint32_t width = (descriptor_words[2] & 0x1FFFu) + 1;
    const uint32_t height = ((descriptor_words[2] >> 13) & 0x1FFFu) + 1;
    const uint32_t stack_depth = descriptor_words[2] >> 26;
    const uint32_t mip_min = (descriptor_words[4] >> 2) & 0xFu;
    const uint32_t mip_max = (descriptor_words[4] >> 6) & 0xFu;
    const uint32_t dimension = (descriptor_words[5] >> 9) & 0x3u;

    if (fetch_type != 2 || format != 6 || endian_mode != 2 || !tiled || stacked ||
        stack_depth != 0 || dimension != 1 || mip_min != 0 || mip_max != 0) {
        return fail("unsupported captured texture-fetch descriptor", error);
    }

    const uint64_t byte_length = static_cast<uint64_t>(width) * height * 4;
    if (!width || !height || byte_length > std::numeric_limits<uint32_t>::max()) {
        return fail("captured texture dimensions are out of range", error);
    }

    *output = CapturedTextureFetch{
        ((descriptor_words[1] >> 12) & 0xFFFFFu) << 12,
        format,
        endian_mode,
        width,
        height,
        static_cast<uint32_t>(byte_length),
        dimension,
        (descriptor_words[3] >> 1) & 0xFFFu,
        (descriptor_words[3] >> 19) & 0x3u,
        (descriptor_words[3] >> 21) & 0x3u,
        (descriptor_words[3] >> 23) & 0x3u,
        (descriptor_words[3] >> 25) & 0x7u,
        tiled != 0,
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
