#include "shift_xbox_shader_translate.hpp"

#include <algorithm>
#include <array>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
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

std::vector<uint8_t> captured_multi_interpolator_vertex_shader() {
    std::vector<uint8_t> shader(5 * 12, 0);
    const uint32_t allocate_word0 = 2u;
    const uint32_t allocate_word1 = (12u << 12) | (2u << 9);
    const uint32_t exec_word0 = 2u | (2u << 12);
    const uint32_t exec_word1 = 1u << 12;
    write_be32(shader.data(), allocate_word0);
    write_be32(shader.data() + 4,
               allocate_word1 | ((exec_word0 & 0xFFFFu) << 16));
    write_be32(shader.data() + 8,
               (exec_word0 >> 16) | (exec_word1 << 16));

    const uint32_t end_word0 = 4u | (1u << 12);
    const uint32_t end_word1 = 2u << 12;
    write_be32(shader.data() + 12, end_word0);
    write_be32(shader.data() + 16, end_word1);

    const auto write_export = [&shader](uint32_t address, uint32_t index,
                                        uint32_t mask, uint32_t source) {
        write_be32(shader.data() + address * 12,
                   (50u << 26) | index | (1u << 15) | (mask << 16));
        write_be32(shader.data() + address * 12 + 8,
                   (2u << 24) | (1u << 31) | (1u << 30) |
                       (source << 16) | (source << 8));
    };
    write_export(2, 1, 0x3u, 0);
    write_export(3, 0, 0xFu, 1);
    write_be32(shader.data() + 4 * 12, 50u << 26);
    return shader;
}

std::vector<uint8_t> captured_conditional_exec_pixel_shader() {
    std::vector<uint8_t> shader(4 * 12, 0);
    write_be32(shader.data(), 2u);
    write_be32(shader.data() + 4, 0x1002C400u);
    write_be32(shader.data() + 8, 0x46000000u);
    write_be32(shader.data() + 12, 0x00001003u);
    write_be32(shader.data() + 16, 0x00002000u);
    write_be32(shader.data() + 2 * 12, 5u << 26);
    write_be32(shader.data() + 3 * 12, 5u << 26);
    return shader;
}

std::vector<uint8_t> captured_predicated_jump_pixel_shader() {
    auto shader = captured_conditional_exec_pixel_shader();
    write_be32(shader.data(), 3u | (1u << 14));
    write_be32(shader.data() + 4, 0x1002B606u);
    return shader;
}

void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << message << '\n';
        std::exit(1);
    }
}

std::vector<uint8_t> read_shader_fixture(const char* filename) {
    const std::string path =
        std::string(SHIFT_XBOX_SHADER_TEST_FIXTURE_DIR) + "/" + filename;
    std::ifstream file(path, std::ios::binary);
    require(file.good(), "captured retail shader fixture could not be opened");
    return std::vector<uint8_t>(std::istreambuf_iterator<char>(file), {});
}

bool same_translation(const shift::xbox::CapturedShaderTranslation& left,
                      const shift::xbox::CapturedShaderTranslation& right) {
    if (left.glsl != right.glsl ||
        left.executed_instruction_addresses != right.executed_instruction_addresses ||
        left.vertex_input_attributes.size() != right.vertex_input_attributes.size() ||
        left.has_vertex_fetch_constant != right.has_vertex_fetch_constant ||
        left.vertex_fetch_constant_index != right.vertex_fetch_constant_index ||
        left.uses_texture != right.uses_texture ||
        left.texture_fetch_constant_index != right.texture_fetch_constant_index ||
        left.texture_fetch_constant_indices != right.texture_fetch_constant_indices ||
        left.float_constant_registers != right.float_constant_registers ||
        left.uses_relative_float_constant_index !=
            right.uses_relative_float_constant_index) {
        return false;
    }
    for (size_t i = 0; i < left.vertex_input_attributes.size(); ++i) {
        const auto& a = left.vertex_input_attributes[i];
        const auto& b = right.vertex_input_attributes[i];
        if (a.location != b.location ||
            a.destination_register != b.destination_register ||
            a.vertex_format != b.vertex_format ||
            a.stride_dwords != b.stride_dwords ||
            a.offset_dwords != b.offset_dwords) {
            return false;
        }
    }
    return true;
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

std::vector<uint8_t> captured_repeated_sampler_pixel_shader_slice() {
    std::vector<uint8_t> shader = captured_pixel_shader_slice();
    // Extend the captured EXEC clause from fetch@4 + ALU@5 to include a
    // second fetch@6 using the same fetch constant. This reproduces the
    // duplicate GLSL local names reported by retail draw #10.
    write_be32(shader.data() + 4, 0x3004B200u);
    write_be32(shader.data() + 8, 0x12000019u);
    std::copy_n(shader.data() + 4 * 12, 12, shader.data() + 6 * 12);
    return shader;
}

void verify_pre_wait_retail_shader_exports() {
    // Exact shader-program dwords from the captured outer and nested IBs;
    // provenance and program hashes are in the matching evidence JSON.
    const auto from_words = [](const auto& words) {
        std::vector<uint8_t> bytes(words.size() * sizeof(uint32_t));
        for (size_t i = 0; i < words.size(); ++i) {
            write_be32(bytes.data() + i * sizeof(uint32_t), words[i]);
        }
        return bytes;
    };
    constexpr std::array<uint32_t, 27> outer_vertex_words = {
        0x30052003u, 0x00001200u, 0xC4000000u, 0x00001005u, 0x00001200u,
        0xC2000000u, 0x00001006u, 0x10071200u, 0x22000000u, 0x30081000u,
        0x00393A88u, 0x00000007u, 0x00080000u, 0x40263688u, 0x00000300u,
        0xC80F8000u, 0x00000000u, 0xE2000000u, 0xC80F803Eu, 0x00000000u,
        0xE2010100u, 0xC8000000u, 0x00000000u, 0xE2000000u, 0x00000000u,
        0x00000000u, 0x00000000u,
    };
    constexpr std::array<uint32_t, 24> nested_vertex_words = {
        0x00001003u, 0x00001200u, 0xC4000000u, 0x00001004u, 0x00001200u,
        0xC2000000u, 0x00001005u, 0x10061200u, 0x22000000u, 0xC8000000u,
        0x00000000u, 0xE2000000u, 0xC800C000u, 0x00000000u, 0xE2000000u,
        0xC888C03Eu, 0x00000000u, 0xE2010100u, 0xC8000000u, 0x00000000u,
        0xE2000000u, 0x00000000u, 0x00000000u, 0x00000000u,
    };
    constexpr std::array<uint32_t, 9> pixel_words = {
        0x00000000u, 0x1001C400u, 0x22000000u, 0xC80F8000u, 0x00000000u,
        0xE2000000u, 0x00000000u, 0x00000000u, 0x00000000u,
    };

    const auto translate = [](shift::xbox::CapturedShaderStage stage,
                              const std::vector<uint8_t>& bytes) {
        shift::xbox::CapturedShaderTranslation output{};
        std::string error;
        if (!shift::xbox::translate_captured_shader_glsl(
                stage, bytes.data(), bytes.size(), {}, &output, &error)) {
            std::cerr << "pre-wait retail shader did not translate: "
                      << error << '\n';
            std::exit(1);
        }
        return output;
    };

    const auto outer_vertex = translate(
        shift::xbox::CapturedShaderStage::Vertex, from_words(outer_vertex_words));
    const auto nested_vertex = translate(
        shift::xbox::CapturedShaderStage::Vertex, from_words(nested_vertex_words));
    for (const auto* vertex : {&outer_vertex, &nested_vertex}) {
        require(vertex->glsl.find("imageStore(") == std::string::npos &&
                    vertex->glsl.find("buffer ") == std::string::npos &&
                    vertex->glsl.find("atomic") == std::string::npos,
                "pre-wait retail vertex shader emitted an explicit memory store");
    }
    require(outer_vertex.glsl.find("gl_Position.x = alu_6.x") != std::string::npos &&
                outer_vertex.glsl.find("shift_interpolator0.x = alu_5.x") !=
                    std::string::npos &&
                nested_vertex.glsl.find("gl_Position.x = 0.0") != std::string::npos &&
                nested_vertex.glsl.find("shift_interpolator0.x = 0.0") !=
                    std::string::npos,
            "pre-wait vertex export did not target position/varying outputs");

    const auto pixel = translate(
        shift::xbox::CapturedShaderStage::Pixel, from_words(pixel_words));
    require(pixel.glsl.find("layout(location=0) out vec4 shift_color0") !=
                    std::string::npos &&
                pixel.glsl.find("shift_color0.x = alu_1.x") != std::string::npos &&
                pixel.glsl.find("imageStore(") == std::string::npos &&
                pixel.glsl.find("buffer ") == std::string::npos &&
                pixel.glsl.find("atomic") == std::string::npos,
            "captured pixel export stopped targeting color output or emitted a memory store");
}

void verify_retail_draw10_shader_pair() {
    const auto vertex = read_shader_fixture("retail_draw10_packet10.vert.bin");
    const auto pixel = read_shader_fixture("retail_draw10_packet10.frag.bin");
    shift::xbox::CapturedShaderTranslation translated_vertex{};
    shift::xbox::CapturedShaderTranslation translated_pixel{};
    std::string error;
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Vertex, vertex.data(),
                vertex.size(), {}, &translated_vertex, &error),
            "retail post-Bink draw #10 vertex shader did not translate");
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel, pixel.data(),
                pixel.size(), {}, &translated_pixel, &error),
            "retail post-Bink draw #10 pixel shader did not translate");
    require(vertex.size() == 156 && pixel.size() == 60 &&
                !translated_vertex.glsl.empty() && !translated_pixel.glsl.empty() &&
                translated_vertex.executed_instruction_addresses.size() == 9 &&
                translated_vertex.vertex_input_attributes.size() == 3 &&
                translated_pixel.executed_instruction_addresses.size() == 2 &&
                translated_pixel.uses_texture &&
                translated_pixel.texture_fetch_constant_indices ==
                    std::vector<uint32_t>{0},
            "retail post-Bink draw #10 shader reflection changed");
}

}  // namespace

int main() {
    verify_pre_wait_retail_shader_exports();
    verify_retail_draw10_shader_pair();

    const std::vector<uint8_t> conditional_exec_shader =
        captured_conditional_exec_pixel_shader();
    shift::xbox::CapturedShaderTranslationOptions conditional_options{};
    conditional_options.pixel_b128 = true;
    shift::xbox::CapturedShaderTranslation conditional_translation{};
    std::string conditional_error;
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel,
                conditional_exec_shader.data(), conditional_exec_shader.size(),
                conditional_options, &conditional_translation, &conditional_error) &&
                conditional_translation.executed_instruction_addresses ==
                    std::vector<uint32_t>{2},
            "true CEXECE did not execute its clause and terminate the shader");
    conditional_options.pixel_b128 = false;
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel,
                conditional_exec_shader.data(), conditional_exec_shader.size(),
                conditional_options, &conditional_translation, &conditional_error) &&
                conditional_translation.executed_instruction_addresses ==
                    std::vector<uint32_t>{3},
            "false CEXECE did not fall through to the bounded EXEC_END");

    std::vector<uint8_t> cexec_shader = conditional_exec_shader;
    write_be32(cexec_shader.data() + 8, 0x36000000u);
    conditional_options.pixel_b128 = true;
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel,
                cexec_shader.data(), cexec_shader.size(), conditional_options,
                &conditional_translation, &conditional_error) &&
                conditional_translation.executed_instruction_addresses ==
                    (std::vector<uint32_t>{2, 3}),
            "true CEXEC did not execute its clause and continue to EXEC_END");
    conditional_options.pixel_b128 = false;
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel,
                cexec_shader.data(), cexec_shader.size(), conditional_options,
                &conditional_translation, &conditional_error) &&
                conditional_translation.executed_instruction_addresses ==
                    std::vector<uint32_t>{3},
            "false CEXEC did not skip its clause and continue to EXEC_END");

    const std::vector<uint8_t> predicated_jump_shader =
        captured_predicated_jump_pixel_shader();
    require(!shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel,
                predicated_jump_shader.data(), predicated_jump_shader.size(),
                conditional_options, &conditional_translation,
                &conditional_error) &&
                conditional_error.find("instruction=0, opcode=11, address=3") !=
                    std::string::npos &&
                conditional_error.find("bool_constant=129, condition=1") !=
                    std::string::npos &&
                conditional_error.find("unconditional=0, predicated=1, direction=1") !=
                    std::string::npos,
            "unsupported retail-style CJMP rejection omitted its decoded fields");

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

    const std::vector<uint8_t> multi_interpolator_shader =
        captured_multi_interpolator_vertex_shader();
    const bool translated_multi_interpolator =
        shift::xbox::translate_captured_shader_glsl(
            shift::xbox::CapturedShaderStage::Vertex,
            multi_interpolator_shader.data(), multi_interpolator_shader.size(),
            vertex_options, &vertex_translated, &vertex_error);
    if (!translated_multi_interpolator) {
        std::cerr << "multi-interpolator translation: " << vertex_error << '\n';
    }
    require(translated_multi_interpolator &&
                vertex_translated.glsl.find(
                    "layout(location=1) out vec4 shift_interpolator1") !=
                    std::string::npos &&
                vertex_translated.glsl.find(
                    "shift_interpolator1.x = alu_2.x") != std::string::npos &&
                vertex_translated.glsl.find(
                    "shift_interpolator0.x = alu_3.x") != std::string::npos,
            "captured Xenos interpolator exports collapsed to one Vulkan varying");

    vertex_options.clip_disabled_window_coordinates = true;
    vertex_options.window_coordinate_width = 1280;
    vertex_options.window_coordinate_height = 720;
    const bool translated_window_coordinates =
        shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Vertex,
                vertex_shader.data(), vertex_shader.size(), vertex_options,
                &vertex_translated, &vertex_error);
    require(translated_window_coordinates &&
                vertex_translated.glsl.find(
                    "gl_Position = vec4(((gl_Position.x * 1.0 + 0.0 - 640.0) * 0.00156250002)") !=
                    std::string::npos &&
                vertex_translated.glsl.find(
                    "((gl_Position.y * 1.0 + 0.0 - 360.0) * 0.00277777785)") !=
                    std::string::npos &&
                vertex_translated.glsl.find("gl_Position.z, 1.0);") !=
                    std::string::npos,
            "clip-disabled Xenos window coordinates were not mapped to Vulkan clip space");
    vertex_options.window_coordinate_width = 0;
    require(!shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Vertex,
                vertex_shader.data(), vertex_shader.size(), vertex_options,
                &vertex_translated, &vertex_error),
            "invalid clip-disabled window transform was silently translated");
    vertex_options.clip_disabled_window_coordinates = false;
    vertex_options.window_coordinate_width = 1280;

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
                "previous_scalar = trunc(shift_vertex_constants.c[0].w)") !=
                std::string::npos &&
                vertex_translated.glsl.find("r[3].x = previous_scalar") !=
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

    const std::vector<uint8_t> repeated_sampler_shader =
        captured_repeated_sampler_pixel_shader_slice();
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel,
                repeated_sampler_shader.data(), repeated_sampler_shader.size(),
                options, &translated, &error) &&
                translated.executed_instruction_addresses ==
                    std::vector<uint32_t>{4, 5, 6, 8} &&
                translated.glsl.find("vec4 sampled_0_fetch_0 =") !=
                    std::string::npos &&
                translated.glsl.find("vec4 sampled_0_fetch_1 =") !=
                    std::string::npos &&
                translated.glsl.find("vec4 fetched_0_fetch_0 =") !=
                    std::string::npos &&
                translated.glsl.find("vec4 fetched_0_fetch_1 =") !=
                    std::string::npos,
            "repeated captured fetch constant reused GLSL local symbols");

    auto integer_texture_options = options;
    integer_texture_options.textures[0].integer_scale = 65535u;
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel, shader.data(),
                shader.size(), integer_texture_options, &translated, &error) &&
                translated.glsl.find("sampled_0 *= 65535.0;") !=
                    std::string::npos,
            "captured format-26 integer texture fetch was not scaled from UNORM");

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
    // GPUSIGN TextureSign::kSigned is two's complement texel data, so the
    // renderer samples it through an SNORM image view and the translator must
    // accept it without emitting a per-channel fixup.
    auto signed_texture_options = options;
    signed_texture_options.textures[0].signs = {
        shift::xbox::TextureSign::Signed,
        shift::xbox::TextureSign::Signed,
        shift::xbox::TextureSign::Signed,
        shift::xbox::TextureSign::Signed};
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel, shader.data(), shader.size(),
                signed_texture_options, &translated, &error) &&
                translated.glsl.find("shift_pwl_gamma_to_linear") ==
                    std::string::npos,
            "captured Signed texture signs were rejected or gained a gamma fixup");

    // UnsignedBiased is still outside the supported subset.
    gamma_texture_options.textures[0].signs = {
        shift::xbox::TextureSign::Signed,
        shift::xbox::TextureSign::UnsignedBiased,
        shift::xbox::TextureSign::Gamma,
        shift::xbox::TextureSign::Unsigned};
    require(!shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel, shader.data(), shader.size(),
                gamma_texture_options, &translated, &error) &&
                error ==
                    "captured texture channel sign is outside the unsigned/gamma/signed "
                    "subset fetch_constant=0 signs=[1,2,3,0]",
            "unsupported captured texture signs were silently accepted or omitted from diagnostics");

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
                translated.glsl.find(
                    "layout(location=1) in vec4 shift_interpolator1") !=
                    std::string::npos &&
                translated.glsl.find("r[1]=shift_interpolator1") !=
                    std::string::npos &&
                translated.glsl.find("r[1].xy") != std::string::npos &&
                translated.glsl.find("r[1].x = fetched_0.x") != std::string::npos,
            "captured pixel interpolator 1 was not connected to its sampled registers");

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
                translated.glsl.find("shift_color0.y = previous_scalar") !=
                    std::string::npos &&
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

    std::vector<uint8_t> retail_vector_add_shader = shader;
    write_be32(retail_vector_add_shader.data() + 7 * 12,
               (50u << 26) | (0xFu << 16));
    write_be32(retail_vector_add_shader.data() + 7 * 12 + 4,
               (1u << 31) | (1u << 29));
    write_be32(retail_vector_add_shader.data() + 7 * 12 + 8,
               (1u << 31) | (1u << 30) | (1u << 16) | (2u << 8) | 68u);
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel,
                retail_vector_add_shader.data(), retail_vector_add_shader.size(),
                options, &translated, &error) &&
                translated.glsl.find("vec4 alu_7 = (") != std::string::npos &&
                translated.glsl.find(" + ") != std::string::npos &&
                translated.glsl.find("r[0].x = alu_7.x") != std::string::npos,
            "captured Xenos vector opcode 0 ADD did not translate component-wise");

    std::vector<uint8_t> retail_vector_min_shader = retail_vector_add_shader;
    write_be32(retail_vector_min_shader.data() + 7 * 12 + 8,
               (3u << 24) | (1u << 31) | (1u << 30) |
                   (1u << 16) | (2u << 8) | 68u);
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel,
                retail_vector_min_shader.data(), retail_vector_min_shader.size(),
                options, &translated, &error) &&
                translated.glsl.find(
                    "mix(r[2].xyzw, r[1].xyzw, lessThan(r[1].xyzw, r[2].xyzw))") !=
                    std::string::npos &&
                translated.glsl.find("r[0].x = alu_7.x") != std::string::npos,
            "captured Xenos vector opcode 3 MIN did not preserve component-wise source selection");

    std::vector<uint8_t> retail_scalar_floor_shader = shader;
    write_be32(retail_scalar_floor_shader.data() + 7 * 12,
               (13u << 26) | (1u << 20));
    write_be32(retail_scalar_floor_shader.data() + 7 * 12 + 4, 0);
    write_be32(retail_scalar_floor_shader.data() + 7 * 12 + 8, 0);
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel,
                retail_scalar_floor_shader.data(), retail_scalar_floor_shader.size(),
                options, &translated, &error) &&
                translated.glsl.find("previous_scalar = floor(") != std::string::npos &&
                translated.glsl.find("r[0].x = previous_scalar") != std::string::npos,
            "captured Xenos scalar FLOOR opcode 13 was not translated");

    std::vector<uint8_t> retail_scalar_log_shader = retail_scalar_floor_shader;
    write_be32(retail_scalar_log_shader.data() + 7 * 12,
               (16u << 26) | (1u << 20));
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel,
                retail_scalar_log_shader.data(), retail_scalar_log_shader.size(),
                options, &translated, &error) &&
                translated.glsl.find(
                    "previous_scalar = log2(shift_pixel_constants.c[0].w);") !=
                    std::string::npos &&
                translated.glsl.find("r[0].x = previous_scalar") != std::string::npos,
            "captured Xenos scalar LOG_IEEE opcode 16 did not translate its selected source");

    std::vector<uint8_t> retail_scalar_muls_prev_shader = retail_scalar_floor_shader;
    write_be32(retail_scalar_muls_prev_shader.data() + 7 * 12,
               13u << 26);
    write_be32(retail_scalar_muls_prev_shader.data() + 8 * 12,
               (3u << 26) | (1u << 15) | (0xFu << 20));
    const bool retail_scalar_muls_prev_translated =
        shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel,
                retail_scalar_muls_prev_shader.data(),
                retail_scalar_muls_prev_shader.size(), options,
                &translated, &error);
    const bool retail_scalar_muls_prev_ok = retail_scalar_muls_prev_translated &&
                translated.glsl.find(
                    "previous_scalar = floor(shift_pixel_constants.c[0].w)") !=
                    std::string::npos &&
                translated.glsl.find(
                    "previous_scalar = ((r[0].w == 0.0") !=
                    std::string::npos &&
                translated.glsl.find("r[0].x = previous_scalar") ==
                    std::string::npos &&
                translated.glsl.find("shift_color0.x = previous_scalar") !=
                    std::string::npos &&
                translated.glsl.find("shift_color0.w = previous_scalar") !=
                    std::string::npos;
    require(retail_scalar_muls_prev_ok,
            "captured Xenos MULS_PREV did not consume/update scalar ps before export");

    std::vector<uint8_t> scalar_add_constant_shader = conditional_exec_shader;
    write_be32(scalar_add_constant_shader.data() + 2 * 12,
               (44u << 26) | (1u << 20));
    write_be32(scalar_add_constant_shader.data() + 2 * 12 + 4,
               1u << 24);
    write_be32(scalar_add_constant_shader.data() + 2 * 12 + 8,
               (1u << 29) | 3u);
    shift::xbox::CapturedShaderTranslationOptions scalar_add_options{};
    scalar_add_options.pixel_b128 = true;
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel,
                scalar_add_constant_shader.data(), scalar_add_constant_shader.size(),
                scalar_add_options, &translated, &error) &&
                translated.glsl.find(
                    "previous_scalar = ((-shift_pixel_constants.c[3].w) + (-r[2].x));") !=
                    std::string::npos &&
                translated.glsl.find("r[0].x = previous_scalar") !=
                    std::string::npos &&
                translated.float_constant_registers == std::vector<uint32_t>{3},
            "captured Xenos ADD_CONST_0 did not decode its constant, src3 selector, or negate");

    std::vector<uint8_t> unsupported_scalar_shader = shader;
    write_be32(unsupported_scalar_shader.data() + 7 * 12,
               (63u << 26) | (1u << 20));
    write_be32(unsupported_scalar_shader.data() + 7 * 12 + 4, 0);
    write_be32(unsupported_scalar_shader.data() + 7 * 12 + 8, 0);
    require(!shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel,
                unsupported_scalar_shader.data(), unsupported_scalar_shader.size(),
                options, &translated, &error) &&
                error.find("scalar opcode 63") != std::string::npos &&
                error.find("instruction 7") != std::string::npos,
            "unsupported captured scalar opcode diagnostic omitted opcode/address");

    shift::xbox::CapturedShaderTranslationCache translation_cache;
    shift::xbox::CapturedShaderTranslationOptions cache_options{};
    cache_options.pixel_b128 = true;
    const auto retail_pixel = captured_pixel_shader_slice();
    shift::xbox::CapturedShaderTranslation uncached{};
    shift::xbox::CapturedShaderTranslation cached{};
    require(shift::xbox::translate_captured_shader_glsl(
                shift::xbox::CapturedShaderStage::Pixel,
                retail_pixel.data(), retail_pixel.size(), cache_options,
                &uncached, &error) &&
                translation_cache.translate(
                    shift::xbox::CapturedShaderStage::Pixel,
                    retail_pixel.data(), retail_pixel.size(), cache_options,
                    &cached, &error) && same_translation(uncached, cached),
            "translation cache changed the captured retail pixel-shader result");
    require(translation_cache.translate(
                shift::xbox::CapturedShaderStage::Pixel,
                retail_pixel.data(), retail_pixel.size(), cache_options,
                &cached, &error) && same_translation(uncached, cached),
            "cached captured retail shader did not reproduce its full translation");
    auto cache_stats = translation_cache.stats();
    require(cache_stats.hits == 1 && cache_stats.misses == 1 &&
                cache_stats.entries == 1,
            "repeated retail shader translation did not hit the cache");
    const uint64_t hits_before_stage_change = cache_stats.hits;
    const bool pixel_bytes_as_vertex = translation_cache.translate(
        shift::xbox::CapturedShaderStage::Vertex,
        retail_pixel.data(), retail_pixel.size(), cache_options, &cached, &error);
    require(translation_cache.stats().hits == hits_before_stage_change &&
                (!pixel_bytes_as_vertex || !same_translation(uncached, cached)),
            "shader stage was omitted from the translation cache key");

    cache_options.pixel_b128 = false;
    require(translation_cache.translate(
                shift::xbox::CapturedShaderStage::Pixel,
                retail_pixel.data(), retail_pixel.size(), cache_options,
                &cached, &error) && cached.glsl != uncached.glsl,
            "pixel b128 was omitted from the shader translation cache key");
    cache_options.pixel_b128 = true;
    cache_options.pixel_b129 = true;
    const auto hits_before_b129 = translation_cache.stats().hits;
    require(!translation_cache.translate(
                shift::xbox::CapturedShaderStage::Pixel,
                retail_pixel.data(), retail_pixel.size(), cache_options,
                &cached, &error) &&
                translation_cache.stats().hits == hits_before_b129,
            "pixel b129 was omitted from the shader translation cache key");
    cache_options.pixel_b129 = false;
    cache_options.pixel_b128 = true;
    cache_options.textures[0].swizzle = {0, 1, 2, 3};
    require(translation_cache.translate(
                shift::xbox::CapturedShaderStage::Pixel,
                retail_pixel.data(), retail_pixel.size(), cache_options,
                &cached, &error) && cached.glsl != uncached.glsl,
            "captured texture swizzle was omitted from the cache key");
    cache_options.textures[0].swizzle = {2, 1, 0, 3};
    cache_options.textures[0].signs = {
        shift::xbox::TextureSign::Gamma, shift::xbox::TextureSign::Gamma,
        shift::xbox::TextureSign::Gamma, shift::xbox::TextureSign::Unsigned};
    require(translation_cache.translate(
                shift::xbox::CapturedShaderStage::Pixel,
                retail_pixel.data(), retail_pixel.size(), cache_options,
                &cached, &error) && cached.glsl != uncached.glsl,
            "captured texture signs were omitted from the cache key");
    cache_options.textures[0].signs = {
        shift::xbox::TextureSign::Unsigned, shift::xbox::TextureSign::Unsigned,
        shift::xbox::TextureSign::Unsigned, shift::xbox::TextureSign::Unsigned};
    cache_options.gamma_color_target = true;
    require(translation_cache.translate(
                shift::xbox::CapturedShaderStage::Pixel,
                retail_pixel.data(), retail_pixel.size(), cache_options,
                &cached, &error) && cached.glsl != uncached.glsl,
            "gamma color-target mode was omitted from the cache key");

    shift::xbox::CapturedShaderTranslationCache failed_cache;
    auto failed_options = cache_options;
    failed_options.pixel_b128 = false;
    require(!failed_cache.translate(
                shift::xbox::CapturedShaderStage::Pixel,
                unsupported_scalar_shader.data(), unsupported_scalar_shader.size(),
                failed_options, &cached, &error) &&
                !failed_cache.translate(
                    shift::xbox::CapturedShaderStage::Pixel,
                    unsupported_scalar_shader.data(), unsupported_scalar_shader.size(),
                    failed_options, &cached, &error) &&
                failed_cache.stats().entries == 0 &&
                failed_cache.stats().misses == 2,
            "failed shader translations were retained or skipped on retry");

    shift::xbox::CapturedShaderTranslationCache bounded_cache;
    shift::xbox::CapturedShaderTranslationOptions bounded_options{};
    bounded_options.clip_disabled_window_coordinates = true;
    bounded_options.window_coordinate_height = 720;
    for (uint32_t width = 1;
         width <= shift::xbox::CapturedShaderTranslationCache::kMaximumEntries + 1;
         ++width) {
        bounded_options.window_coordinate_width = width;
        require(bounded_cache.translate(
                    shift::xbox::CapturedShaderStage::Vertex,
                    vertex_shader.data(), vertex_shader.size(), bounded_options,
                    &vertex_translated, &error),
                "bounded cache rejected a valid captured vertex shader");
    }
    cache_stats = bounded_cache.stats();
    require(cache_stats.entries ==
                shift::xbox::CapturedShaderTranslationCache::kMaximumEntries &&
                cache_stats.retained_payload_bytes <=
                    shift::xbox::CapturedShaderTranslationCache::kMaximumPayloadBytes,
            "shader translation cache exceeded its entry or payload bound");
    bounded_options.window_coordinate_width = 1;
    require(bounded_cache.translate(
                shift::xbox::CapturedShaderStage::Vertex,
                vertex_shader.data(), vertex_shader.size(), bounded_options,
                &vertex_translated, &error) &&
                bounded_cache.stats().misses ==
                    shift::xbox::CapturedShaderTranslationCache::kMaximumEntries + 2,
            "oldest translation was not evicted at the cache capacity");
    bounded_cache.clear();
    cache_stats = bounded_cache.stats();
    require(cache_stats.entries == 0 && cache_stats.retained_payload_bytes == 0 &&
                cache_stats.hits == 0 && cache_stats.misses == 0,
            "clearing shader translation cache did not reset retained state");
    return 0;
}
