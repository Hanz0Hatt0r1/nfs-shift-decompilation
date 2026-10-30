#include "shift_xbox_shader_translate.hpp"

#include <algorithm>
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

// Minimal instruction slice from the captured retail PS: its actual CF branch
// prefix, tfetch2D@4, serialization slot@5, and color export@8. The shader
// branches exercise the exact b128/b129 path selection without storing a full
// retail shader capture in the repository.
std::vector<uint8_t> captured_pixel_shader_slice() {
    constexpr uint8_t cf[] = {
        0x00, 0x00, 0x00, 0x05, 0x20, 0x04, 0xB2, 0x00, 0x12, 0x00, 0x00, 0x09,
        0x00, 0x00, 0x00, 0x04, 0x10, 0x06, 0xB2, 0x04, 0x12, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x20, 0x06, 0x10, 0x07, 0xB0, 0x00, 0x12, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x10, 0x08, 0xC4, 0x00, 0x22, 0x00, 0x00, 0x00,
    };
    constexpr uint8_t fetch4[] = {
        0x10, 0x08, 0x00, 0x01, 0x1F, 0x1F, 0xF6, 0x88, 0x00, 0x00, 0x40, 0x00,
    };
    constexpr uint8_t alu5[] = {
        0xC8, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00,
    };
    constexpr uint8_t alu7[] = {
        0xC8, 0x0F, 0x00, 0x00, 0x00, 0x6C, 0x6C, 0x00, 0x22, 0xFF, 0xFF, 0x00,
    };
    constexpr uint8_t alu8[] = {
        0xC8, 0x0F, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0xA1, 0x00, 0x00, 0x00,
    };
    std::vector<uint8_t> shader(9 * 12, 0);
    std::copy(std::begin(cf), std::end(cf), shader.begin());
    std::copy(std::begin(fetch4), std::end(fetch4), shader.begin() + 4 * 12);
    std::copy(std::begin(alu5), std::end(alu5), shader.begin() + 5 * 12);
    std::copy(std::begin(alu7), std::end(alu7), shader.begin() + 7 * 12);
    std::copy(std::begin(alu8), std::end(alu8), shader.begin() + 8 * 12);
    return shader;
}

}  // namespace

int main() {
    const std::vector<uint8_t> shader = captured_pixel_shader_slice();
    shift::xbox::CapturedShaderTranslationOptions options{};
    options.pixel_b128 = true;
    options.pixel_b129 = false;
    shift::xbox::CapturedShaderTranslation translated{};
    std::string error;
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel, shader.data(), shader.size(),
                options, &translated, &error),
            "captured b128/b129 shader path did not translate");
    require(translated.executed_instruction_addresses ==
                std::vector<uint32_t>{4, 5, 8},
            "captured pixel branch selected the wrong instruction addresses");
    require(translated.glsl.find("shift_sampler_0") != std::string::npos &&
                translated.glsl.find("sampled_0.z, sampled_0.y, sampled_0.x, sampled_0.w") !=
                    std::string::npos &&
                translated.glsl.find("shift_color0") != std::string::npos,
            "captured sampler swizzle or color export was lost");

    options.pixel_b129 = true;
    require(!shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel, shader.data(), shader.size(),
                options, &translated, &error),
            "unsupported captured MAXS branch was silently translated");

    options.pixel_b128 = false;
    options.pixel_b129 = false;
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel, shader.data(), shader.size(),
                options, &translated, &error),
            "alternate captured pixel branch did not translate");
    require(translated.executed_instruction_addresses == std::vector<uint32_t>{7, 8} &&
                translated.glsl.find("shift_sampler_0") == std::string::npos,
            "captured b128 false branch did not skip the texture fetch");
    return 0;
}
