#include "shift_xbox_shader_translate.hpp"

#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

namespace {

void write_be32(uint8_t* bytes, uint32_t value) {
    bytes[0] = static_cast<uint8_t>(value >> 24);
    bytes[1] = static_cast<uint8_t>(value >> 16);
    bytes[2] = static_cast<uint8_t>(value >> 8);
    bytes[3] = static_cast<uint8_t>(value);
}

std::vector<uint8_t> captured_full_mini_vertex_shader() {
    std::vector<uint8_t> shader(5 * 12, 0);
    const uint32_t exec_word0 = 2u | (2u << 12) | (5u << 16);
    const uint32_t exec_word1 = 1u << 12;
    const uint32_t end_word0 = 4u | (1u << 12);
    const uint32_t end_word1 = 2u << 12;
    write_be32(shader.data(), exec_word0);
    write_be32(shader.data() + 4,
               exec_word1 | ((end_word0 & 0xFFFFu) << 16));
    write_be32(shader.data() + 8,
               (end_word0 >> 16) | (end_word1 << 16));

    write_be32(shader.data() + 2 * 12, (1u << 19) | (1u << 12));
    write_be32(shader.data() + 2 * 12 + 4, (57u << 16) | 2696u);
    write_be32(shader.data() + 2 * 12 + 8, 7u);
    write_be32(shader.data() + 3 * 12, 1u << 19);
    write_be32(shader.data() + 3 * 12 + 4,
               (1u << 30) | (38u << 16) | 1672u);
    write_be32(shader.data() + 3 * 12 + 8, 3u << 8);
    write_be32(shader.data() + 4 * 12, 5u << 26);
    return shader;
}

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
    const std::vector<uint8_t> vertex_shader =
        captured_full_mini_vertex_shader();
    shift::xbox::CapturedShaderTranslationOptions vertex_options{};
    shift::xbox::CapturedShaderTranslation vertex_translated{};
    std::string vertex_error;
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Vertex,
                vertex_shader.data(), vertex_shader.size(), vertex_options,
                &vertex_translated, &vertex_error),
            "captured full/mini vertex fetch pair did not translate");
    require(vertex_translated.has_vertex_fetch_constant &&
                vertex_translated.vertex_fetch_constant_index == 0 &&
                vertex_translated.vertex_input_attributes.size() == 2 &&
                vertex_translated.vertex_input_attributes[0].vertex_format == 57 &&
                vertex_translated.vertex_input_attributes[0].stride_dwords == 7 &&
                vertex_translated.vertex_input_attributes[0].offset_dwords == 0 &&
                vertex_translated.vertex_input_attributes[0].destination_register == 1 &&
                vertex_translated.vertex_input_attributes[1].vertex_format == 38 &&
                vertex_translated.vertex_input_attributes[1].stride_dwords == 7 &&
                vertex_translated.vertex_input_attributes[1].offset_dwords == 3 &&
                vertex_translated.vertex_input_attributes[1].destination_register == 0 &&
                vertex_translated.glsl.find(
                    "layout(location=0) in vec3 shift_vertex_input_0") !=
                    std::string::npos &&
                vertex_translated.glsl.find(
                    "layout(location=1) in vec4 shift_vertex_input_1") !=
                    std::string::npos &&
                vertex_translated.glsl.find("r[1].x = fetched_vertex_0.x") !=
                    std::string::npos &&
                vertex_translated.glsl.find("r[0].x = fetched_vertex_1.x") !=
                    std::string::npos,
            "full/mini fetch translation lost the captured vertex layout");

    std::vector<uint8_t> unsupported_vertex_format = vertex_shader;
    write_be32(unsupported_vertex_format.data() + 2 * 12 + 4,
               (5u << 16) | 2696u);
    require(!shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Vertex,
                unsupported_vertex_format.data(), unsupported_vertex_format.size(),
                vertex_options, &vertex_translated, &vertex_error) &&
                vertex_error.find("format=5(unknown)") != std::string::npos &&
                vertex_error.find("stride_dwords=7") != std::string::npos,
            "unsupported vertex fetch did not report its captured layout");

    std::vector<uint8_t> rgba8_vertex_format = vertex_shader;
    write_be32(rgba8_vertex_format.data() + 2 * 12 + 4,
               (6u << 16) | 2696u);
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Vertex,
                rgba8_vertex_format.data(), rgba8_vertex_format.size(),
                vertex_options, &vertex_translated, &vertex_error) &&
                vertex_translated.vertex_input_attributes[0].vertex_format == 6 &&
                vertex_translated.glsl.find(
                    "layout(location=0) in vec4 shift_vertex_input_0") !=
                    std::string::npos,
            "captured 8_8_8_8 vertex fetch did not translate to four UNORM lanes");

    std::vector<uint8_t> float2_vertex_format = vertex_shader;
    write_be32(float2_vertex_format.data() + 3 * 12 + 4,
               (1u << 30) | (37u << 16) | 1672u);
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Vertex,
                float2_vertex_format.data(), float2_vertex_format.size(),
                vertex_options, &vertex_translated, &vertex_error) &&
                vertex_translated.vertex_input_attributes[1].vertex_format == 37 &&
                vertex_translated.glsl.find(
                    "layout(location=1) in vec2 shift_vertex_input_1") !=
                    std::string::npos &&
                vertex_translated.glsl.find(
                    "vec4(shift_vertex_input_1, 0.0, 1.0)") !=
                    std::string::npos,
            "captured 32_32_FLOAT vertex fetch lost its float2 default lanes");

    std::vector<uint8_t> relative_scalar_destination = vertex_shader;
    const uint32_t relative_scalar_trunc = (12u << 26) | (3u << 8) |
                                           (1u << 14) | (1u << 20);
    write_be32(relative_scalar_destination.data() + 4 * 12,
               relative_scalar_trunc);
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Vertex,
                relative_scalar_destination.data(),
                relative_scalar_destination.size(), vertex_options,
                &vertex_translated, &vertex_error),
            "captured loop-relative scalar destination with initial aL did not translate");
    require(vertex_translated.glsl.find(
                "r[3].x = trunc(shift_vertex_constants.c[0].w)") !=
                std::string::npos,
            "initial aL=0 did not preserve the scalar destination register");

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
                translated.glsl.find("layout(set=1,binding=0)") != std::string::npos &&
                translated.glsl.find("sampled_0.z, sampled_0.y, sampled_0.x, sampled_0.w") !=
                    std::string::npos &&
                translated.glsl.find("shift_color0") != std::string::npos,
            "captured sampler swizzle or color export was lost");

    auto gamma_options = options;
    gamma_options.gamma_color_target = true;
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel, shader.data(), shader.size(),
                gamma_options, &translated, &error) &&
                translated.glsl.find(
                    "shift_color0.rgb=(trunc(linear_rgb*gamma_scale)+gamma_offset)/255.0;") !=
                    std::string::npos &&
                translated.glsl.find("shift_color0.a=") == std::string::npos,
            "captured RGBA8_GAMMA target lost its RGB-only write conversion");

    auto gamma_texture_options = options;
    gamma_texture_options.textures[0].signs = {
        shift::xbox::TextureSign::Gamma, shift::xbox::TextureSign::Gamma,
        shift::xbox::TextureSign::Gamma, shift::xbox::TextureSign::Unsigned};
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel, shader.data(), shader.size(),
                gamma_texture_options, &translated, &error) &&
                translated.glsl.find("float shift_pwl_gamma_to_linear(float gamma)") !=
                    std::string::npos &&
                translated.glsl.find("sampled_0.x=shift_pwl_gamma_to_linear(sampled_0.x)") !=
                    std::string::npos &&
                translated.glsl.find("sampled_0.w=shift_pwl_gamma_to_linear") ==
                    std::string::npos,
            "captured Gamma RGB texture signs did not preserve linear alpha");
    gamma_texture_options.textures[0].signs[0] = shift::xbox::TextureSign::Signed;
    require(!shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel, shader.data(), shader.size(),
                gamma_texture_options, &translated, &error) &&
                error == "captured texture channel sign is outside the unsigned/gamma subset",
            "uncaptured signed texture sign was silently accepted");

    std::vector<uint8_t> multiple_samplers = shader;
    write_be32(multiple_samplers.data() + 8, 0x12000005u);
    write_be32(multiple_samplers.data() + 5 * 12, 0x10180001u);
    write_be32(multiple_samplers.data() + 5 * 12 + 4, 0x1F1FF688u);
    write_be32(multiple_samplers.data() + 5 * 12 + 8, 0x00004000u);
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel,
                multiple_samplers.data(), multiple_samplers.size(), options,
                &translated, &error) &&
                translated.texture_fetch_constant_indices ==
                    std::vector<uint32_t>{0u, 1u} &&
                translated.glsl.find("layout(set=1,binding=0) uniform sampler2D shift_sampler_0") !=
                    std::string::npos &&
                translated.glsl.find("layout(set=1,binding=1) uniform sampler2D shift_sampler_1") !=
                    std::string::npos &&
                translated.glsl.find("texture(shift_sampler_1") != std::string::npos,
            "captured pixel shader with two sampler constants did not translate");

    std::vector<uint8_t> nonzero_texture_registers = shader;
    write_be32(nonzero_texture_registers.data() + 4 * 12,
               0x10080001u | (1u << 5) | (1u << 12));
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel,
                nonzero_texture_registers.data(),
                nonzero_texture_registers.size(), options, &translated, &error) &&
                translated.glsl.find("r[1].xy") != std::string::npos &&
                translated.glsl.find("r[1].x = fetched_0.x") != std::string::npos,
            "captured texture fetch did not read/write its decoded temporary registers");

    std::vector<uint8_t> unsupported_texture_swizzle = shader;
    write_be32(unsupported_texture_swizzle.data() + 4 * 12 + 4,
               0x1F1FF688u & ~7u | 6u);
    require(!shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel,
                unsupported_texture_swizzle.data(),
                unsupported_texture_swizzle.size(), options, &translated, &error),
            "unsupported texture destination swizzle was silently translated");

    std::vector<uint8_t> export_constants = shader;
    const uint32_t export_masks = (12u << 26) | (1u << 14) | (1u << 15) |
                                  (5u << 16) | (6u << 20);
    write_be32(export_constants.data() + 8 * 12, export_masks);
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel,
                export_constants.data(), export_constants.size(), options,
                &translated, &error),
            "captured relative scalar export masks did not translate");
    require(translated.glsl.find("shift_color0.x = alu_8.x") != std::string::npos &&
                translated.glsl.find("shift_color0.y = trunc(") != std::string::npos &&
                translated.glsl.find("shift_color0.z = 1.0") != std::string::npos &&
                translated.glsl.find("shift_color0.w = 0.0") != std::string::npos,
            "captured export overlap/constant masks were not preserved");

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

    std::vector<uint8_t> relative_third_constant = shader;
    write_be32(relative_third_constant.data() + 7 * 12,
               (50u << 26) | (0xFu << 16));
    write_be32(relative_third_constant.data() + 7 * 12 + 4,
               (1u << 31) | (1u << 29));
    write_be32(relative_third_constant.data() + 7 * 12 + 8,
               (17u << 24) | (1u << 31) | (1u << 30) |
                   (1u << 16) | (2u << 8) | 68u);
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel,
                relative_third_constant.data(), relative_third_constant.size(),
                options, &translated, &error) &&
                translated.glsl.find(
                    "shift_pixel_constants.c[68 + a0].xyzw") !=
                    std::string::npos,
            "captured third ALU constant lost its address-register offset");

    std::vector<uint8_t> retail_dp3_shader = shader;
    write_be32(retail_dp3_shader.data() + 7 * 12,
               (50u << 26) | (0xFu << 16));
    write_be32(retail_dp3_shader.data() + 7 * 12 + 4,
               (1u << 31) | (1u << 29));
    write_be32(retail_dp3_shader.data() + 7 * 12 + 8,
               (16u << 24) | (1u << 31) | (1u << 30) |
                   (1u << 16) | (2u << 8) | 68u);
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel,
                retail_dp3_shader.data(), retail_dp3_shader.size(), options,
                &translated, &error) &&
                translated.glsl.find(
                    "vec4(dot(r[1].xyzw.xyz, r[2].xyzw.xyz))") !=
                    std::string::npos &&
                translated.glsl.find("r[0].x = alu_7.x") !=
                    std::string::npos &&
                translated.glsl.find("r[0].y = alu_7.y") !=
                    std::string::npos,
            "captured Xenos vector opcode 16 DP3 did not replicate XYZ dot output");
    return 0;
}
