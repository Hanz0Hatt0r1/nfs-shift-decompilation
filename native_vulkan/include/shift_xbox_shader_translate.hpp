#pragma once

#include "shift_xbox_draw_input.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <string>
#include <unordered_map>
#include <vector>

namespace shift::xbox {

enum class CapturedShaderStage : uint8_t {
    Vertex,
    Pixel,
};

struct CapturedShaderTextureOptions {
    // Resource descriptor selectors: X, Y, Z, W, zero, or one.
    std::array<uint32_t, 4> swizzle = {2, 1, 0, 3};
    std::array<TextureSign, 4> signs = {
        TextureSign::Unsigned, TextureSign::Unsigned,
        TextureSign::Unsigned, TextureSign::Unsigned};
    // Scale UNORM-backed integer texture fetches back to their guest range.
    uint32_t integer_scale = 0;
};

struct CapturedShaderTranslationOptions {
    bool pixel_b128 = false;
    bool pixel_b129 = false;
    bool gamma_color_target = false;
    bool clip_disabled_window_coordinates = false;
    uint32_t window_coordinate_width = 0;
    uint32_t window_coordinate_height = 0;
    float window_coordinate_x_scale = 1.0f;
    float window_coordinate_y_scale = 1.0f;
    float window_coordinate_x_offset = 0.0f;
    float window_coordinate_y_offset = 0.0f;
    std::array<CapturedShaderTextureOptions, 32> textures{};
};

struct CapturedVertexInputAttribute {
    uint32_t location;
    uint32_t destination_register;
    uint32_t vertex_format;
    uint32_t stride_dwords;
    int32_t offset_dwords;
};

struct CapturedShaderTranslation {
    std::string glsl;
    std::vector<uint32_t> executed_instruction_addresses;
    std::vector<CapturedVertexInputAttribute> vertex_input_attributes;
    bool has_vertex_fetch_constant = false;
    uint32_t vertex_fetch_constant_index = 0;
    bool uses_texture = false;
    uint32_t texture_fetch_constant_index = 0;
    std::vector<uint32_t> texture_fetch_constant_indices;
    std::vector<uint32_t> float_constant_registers;
    bool uses_relative_float_constant_index = false;
};

// Emits project-owned Vulkan GLSL for the captured shader subset. It is a
// bounded translator, not a general Xenos emulator: unsupported control flow,
// fetches, operands, and opcodes fail closed.
bool translate_captured_shader_glsl(
    CapturedShaderStage stage,
    const uint8_t* shader_bytes,
    size_t byte_length,
    const CapturedShaderTranslationOptions& options,
    CapturedShaderTranslation* output,
    std::string* error);

class CapturedShaderTranslationCache {
public:
    struct Stats {
        uint64_t hits = 0;
        uint64_t misses = 0;
        size_t entries = 0;
        size_t retained_payload_bytes = 0;
    };

    static constexpr size_t kMaximumEntries = 128;
    static constexpr size_t kMaximumPayloadBytes = 4u * 1024u * 1024u;

    // The renderer owns this cache on its single guest-ring worker thread.
    bool translate(CapturedShaderStage stage, const uint8_t* shader_bytes,
                   size_t byte_length,
                   const CapturedShaderTranslationOptions& options,
                   CapturedShaderTranslation* output, std::string* error);
    void clear();
    Stats stats() const;

private:
    struct Entry {
        CapturedShaderTranslation translation;
        size_t payload_bytes = 0;
    };

    static std::string make_key(
        CapturedShaderStage stage, const uint8_t* shader_bytes,
        size_t byte_length,
        const CapturedShaderTranslationOptions& options);
    static size_t translation_payload_bytes(
        const CapturedShaderTranslation& translation);

    std::unordered_map<std::string, Entry> entries_;
    std::deque<std::string> insertion_order_;
    size_t retained_payload_bytes_ = 0;
    uint64_t hits_ = 0;
    uint64_t misses_ = 0;
};

}  // namespace shift::xbox
