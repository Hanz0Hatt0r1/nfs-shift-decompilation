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
    uint32_t vertex_fetch_constant_index = 95;
    // Resource descriptor selectors: X, Y, Z, W, zero, or one.
    std::array<uint32_t, 4> texture_swizzle = {2, 1, 0, 3};
};

struct CapturedShaderTranslation {
    std::string glsl;
    std::vector<uint32_t> executed_instruction_addresses;
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
