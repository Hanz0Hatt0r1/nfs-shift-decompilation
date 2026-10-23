#pragma once

#include "shift_xbox_draw_input.hpp"

#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace shift::xbox {

enum class CapturedShaderStage : uint8_t {
    Vertex,
    Pixel,
};

struct CapturedShaderTranslationOptions {
    bool pixel_b128 = false;
    bool pixel_b129 = false;
    // Resource descriptor selectors: X, Y, Z, W, zero, or one.
    std::array<uint32_t, 4> texture_swizzle = {2, 1, 0, 3};
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

}  // namespace shift::xbox
