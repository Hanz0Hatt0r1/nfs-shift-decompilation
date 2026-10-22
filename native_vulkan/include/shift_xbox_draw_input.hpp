#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace shift::xbox {

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

struct CapturedVertexFetch {
    uint32_t guest_address;
    uint32_t endian_mode;
    uint32_t size_words;
    uint32_t byte_length;
};

struct CapturedTextureFetch {
    uint32_t guest_address;
    uint32_t format;
    uint32_t endian_mode;
    uint32_t sign_x;
    uint32_t sign_y;
    uint32_t sign_z;
    uint32_t sign_w;
    uint32_t clamp_x;
    uint32_t clamp_y;
    uint32_t clamp_z;
    uint32_t width;
    uint32_t height;
    uint32_t pitch;
    uint32_t byte_length;
    uint32_t dimension;
    uint32_t swizzle;
    uint32_t mag_filter;
    uint32_t min_filter;
    uint32_t mip_filter;
    uint32_t aniso_filter;
    bool integer_format;
    uint32_t border_color;
    bool border_size;
    bool tiled;
};

enum class TextureComponent : uint8_t {
    X,
    Y,
    Z,
    W,
    Zero,
    One,
};

enum class TextureSign : uint8_t {
    Unsigned,
    Signed,
    UnsignedBiased,
    Gamma,
};

enum class TextureClamp : uint8_t {
    Repeat,
    MirroredRepeat,
    ClampToEdge,
    MirrorClampToEdge,
    ClampToHalfway,
    MirrorClampToHalfway,
    ClampToBorder,
    MirrorClampToBorder,
};

enum class TextureFilter : uint8_t {
    Point,
    Linear,
    BaseMap,
    FetchConstant,
};

enum class TextureAnisotropy : uint8_t {
    Disabled,
    Max1To1,
    Max2To1,
    Max4To1,
    Max8To1,
    Max16To1,
    FetchConstant = 7,
};

enum class TextureBorderColor : uint8_t {
    AbgrBlack,
    AbgrWhite,
    AcbycrBlack,
    AcbcryBlack,
};

struct CapturedTextureSampling {
    std::array<TextureComponent, 4> swizzle;
    std::array<TextureSign, 4> signs;
    std::array<TextureClamp, 3> clamps;
    TextureFilter mag_filter;
    TextureFilter min_filter;
    TextureFilter mip_filter;
    TextureAnisotropy anisotropy;
    TextureBorderColor border_color;
    bool border_alpha_known;
};

// Translates only the captured PM4_DRAW_INDX form. This decodes the guest
// command into renderer inputs; it does not execute or emulate Xenos state.
bool decode_captured_draw_indx(
    const uint8_t* packet_bytes,
    size_t byte_length,
    DecodedIndexedDraw* output,
    std::string* error);

// Decodes the captured two-dword vertex-fetch descriptor. The dwords are
// numeric register values, after the ring frontend's explicit byte-order read.
bool decode_captured_vertex_fetch(
    const uint32_t descriptor_words[2],
    CapturedVertexFetch* output,
    std::string* error);

// Decodes only the captured format-6 tiled 2D texture descriptor.
bool decode_captured_texture_fetch(
    const uint32_t descriptor_words[6],
    CapturedTextureFetch* output,
    std::string* error);

// Gives the captured descriptor fields semantic names without choosing a
// Vulkan format or sampler policy. Unknown/reserved selector values fail.
bool decode_captured_texture_sampling(
    const CapturedTextureFetch& texture,
    CapturedTextureSampling* output,
    std::string* error);

// Untiles the captured 8_8_8_8, 8-in-32, tiled 2D texture into linear texel
// order while applying the captured per-dword byte swap. Other layouts fail.
bool untile_captured_texture_2d(
    const CapturedTextureFetch& texture,
    const uint8_t* guest_bytes,
    size_t byte_length,
    std::vector<uint8_t>* vulkan_bytes,
    std::string* error);

// Converts only the two guest byte orders observed on this captured draw:
// 8-in-16 indices and 8-in-32 vertex words. The output byte stream is suitable
// for the Vulkan index/vertex formats used by the captured resources.
bool normalize_captured_buffer_bytes(
    uint32_t endian_mode,
    const uint8_t* guest_bytes,
    size_t byte_length,
    std::vector<uint8_t>* vulkan_bytes,
    std::string* error);

}  // namespace shift::xbox
