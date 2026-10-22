#include "shift_xbox_draw_input.hpp"

#include <array>
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

const uint8_t kCapturedPacket[] = {
    0xC0, 0x03, 0x22, 0x01,
    0x00, 0x00, 0x00, 0x00,
    0x00, 0x06, 0x00, 0x04,
    0x09, 0x75, 0xD7, 0xB0,
    0x40, 0x00, 0x00, 0x06,
};

uint32_t read_be32(const uint8_t* bytes) {
    return (static_cast<uint32_t>(bytes[0]) << 24) |
           (static_cast<uint32_t>(bytes[1]) << 16) |
           (static_cast<uint32_t>(bytes[2]) << 8) | bytes[3];
}

}  // namespace

int main() {
    shift::xbox::DecodedIndexedDraw input{};
    std::string error;
    require(shift::xbox::decode_captured_draw_indx(
                kCapturedPacket, sizeof(kCapturedPacket), &input, &error),
            "captured retail packet was rejected");
    require(input.topology == shift::xbox::PrimitiveTopology::TriangleList,
            "primitive topology changed");
    require(input.index_count == 6, "index count changed");
    require(input.index_guest_address == 0x0975D7B0u, "index base changed");
    require(input.index_type_bits == 16, "index type changed");
    require(input.index_endian_mode == 1, "index endian mode changed");
    require(input.index_byte_length == 12, "index range changed");

    const uint32_t captured_vertex_descriptor[] = {0x0975DFD3u, 0x10000032u};
    shift::xbox::CapturedVertexFetch vertex_fetch{};
    require(shift::xbox::decode_captured_vertex_fetch(
                captured_vertex_descriptor, &vertex_fetch, &error),
            "captured vertex-fetch descriptor was rejected");
    require(vertex_fetch.guest_address == 0x0975DFD0u,
            "captured vertex-fetch address changed");
    require(vertex_fetch.endian_mode == 2 && vertex_fetch.size_words == 12 &&
                vertex_fetch.byte_length == 48,
            "captured vertex-fetch shape changed");

    const uint32_t captured_texture_descriptor[] = {
        0x8800D8FEu, 0x09D57086u, 0x001FE3FFu,
        0x01280C14u, 0x00000003u, 0x00000A10u,
    };
    shift::xbox::CapturedTextureFetch texture_fetch{};
    require(shift::xbox::decode_captured_texture_fetch(
                captured_texture_descriptor, &texture_fetch, &error),
            "captured texture-fetch descriptor was rejected");
    require(texture_fetch.guest_address == 0x09D57000u && texture_fetch.format == 6 &&
                texture_fetch.endian_mode == 2,
            "captured texture resource identity changed");
    require(texture_fetch.width == 1024 && texture_fetch.height == 256 &&
                texture_fetch.pitch == 1024 &&
                texture_fetch.byte_length == 1024u * 256u * 4u && texture_fetch.tiled,
            "captured texture dimensions or layout changed");
    require(texture_fetch.dimension == 1 && texture_fetch.swizzle == 0x60Au &&
                texture_fetch.mag_filter == 1 && texture_fetch.min_filter == 1 &&
                texture_fetch.mip_filter == 2 && texture_fetch.aniso_filter == 0,
            "captured texture sampling fields changed");
    require(texture_fetch.sign_x == 3 && texture_fetch.sign_y == 3 &&
                texture_fetch.sign_z == 3 && texture_fetch.sign_w == 0 &&
                texture_fetch.clamp_x == 6 && texture_fetch.clamp_y == 6 &&
                texture_fetch.clamp_z == 0 && !texture_fetch.integer_format &&
                texture_fetch.border_color == 0 && !texture_fetch.border_size,
            "captured texture channel or clamp state changed");

    shift::xbox::CapturedTextureSampling texture_sampling{};
    require(shift::xbox::decode_captured_texture_sampling(
                texture_fetch, &texture_sampling, &error),
            "captured texture sampling state was rejected");
    require(texture_sampling.swizzle == std::array<shift::xbox::TextureComponent, 4>{
                shift::xbox::TextureComponent::Z,
                shift::xbox::TextureComponent::Y,
                shift::xbox::TextureComponent::X,
                shift::xbox::TextureComponent::W},
            "captured texture swizzle selectors changed");
    require(texture_sampling.signs == std::array<shift::xbox::TextureSign, 4>{
                shift::xbox::TextureSign::Gamma,
                shift::xbox::TextureSign::Gamma,
                shift::xbox::TextureSign::Gamma,
                shift::xbox::TextureSign::Unsigned},
            "captured texture channel encodings changed");
    require(texture_sampling.clamps == std::array<shift::xbox::TextureClamp, 3>{
                shift::xbox::TextureClamp::ClampToBorder,
                shift::xbox::TextureClamp::ClampToBorder,
                shift::xbox::TextureClamp::Repeat},
            "captured texture clamp modes changed");
    require(texture_sampling.mag_filter == shift::xbox::TextureFilter::Linear &&
                texture_sampling.min_filter == shift::xbox::TextureFilter::Linear &&
                texture_sampling.mip_filter == shift::xbox::TextureFilter::BaseMap &&
                texture_sampling.anisotropy == shift::xbox::TextureAnisotropy::Disabled &&
                texture_sampling.border_color == shift::xbox::TextureBorderColor::AbgrBlack &&
                !texture_sampling.border_alpha_known,
            "captured texture sampler interpretation changed");

    const shift::xbox::CapturedRasterRegisters captured_raster_registers{
        0x14000500u, 0x00010000u, 0x000002D0u, 0x00000004u,
        0x00700770u, 0x0000000Fu, 0x44200000u, 0x44200000u,
        0xC3B40000u, 0x43B40000u, 0x00000000u, 0x20002000u,
        0x00000000u, 0x00000000u, 0x02D00500u,
    };
    shift::xbox::CapturedRasterState raster_state{};
    require(shift::xbox::decode_captured_raster_state(
                captured_raster_registers, &raster_state, &error),
            "captured Xbox target and raster state was rejected");
    require(raster_state.width == 1280 && raster_state.height == 720 &&
                raster_state.sample_count == 1 && raster_state.color_base_tiles == 0 &&
                raster_state.color_format ==
                    shift::xbox::CapturedColorTargetFormat::Rgba8Gamma &&
                raster_state.depth_base_tiles == 720 &&
                raster_state.depth_format ==
                    shift::xbox::CapturedDepthTargetFormat::D24S8,
            "captured Xbox render target interpretation changed");
    require(raster_state.color_write_mask == 0xFu && raster_state.viewport_y_flipped &&
                !raster_state.depth_test_enabled && !raster_state.depth_write_enabled &&
                !raster_state.stencil_test_enabled,
            "captured Xbox depth or color write state changed");
    require(raster_state.scissor_x0 == 0 && raster_state.scissor_y0 == 0 &&
                raster_state.scissor_x1 == 1280 && raster_state.scissor_y1 == 720 &&
                raster_state.scissor_has_area,
            "captured Xbox scissor bounds changed");

    shift::xbox::CapturedRasterRegisters unsupported_raster = captured_raster_registers;
    unsupported_raster.window_offset = 1;
    require(!shift::xbox::decode_captured_raster_state(
                unsupported_raster, &raster_state, &error),
            "uncaptured non-zero window offset was accepted");

    shift::xbox::CapturedTextureFetch white_border_texture = texture_fetch;
    white_border_texture.border_color = 1;
    require(shift::xbox::decode_captured_texture_sampling(
                white_border_texture, &texture_sampling, &error) &&
                texture_sampling.border_color == shift::xbox::TextureBorderColor::AbgrWhite &&
                texture_sampling.border_alpha_known,
            "known opaque-white border color lost its alpha contract");
    shift::xbox::CapturedTextureFetch reserved_swizzle = texture_fetch;
    reserved_swizzle.swizzle = (reserved_swizzle.swizzle & ~0x7u) | 6u;
    require(!shift::xbox::decode_captured_texture_sampling(
                reserved_swizzle, &texture_sampling, &error),
            "reserved texture swizzle selector was accepted");
    shift::xbox::CapturedTextureFetch reserved_anisotropy = texture_fetch;
    reserved_anisotropy.aniso_filter = 6;
    require(!shift::xbox::decode_captured_texture_sampling(
                reserved_anisotropy, &texture_sampling, &error),
            "reserved texture anisotropy value was accepted");

    std::vector<uint8_t> tiled_texture(texture_fetch.byte_length);
    const size_t texture_pixels = texture_fetch.byte_length / 4;
    for (size_t pixel = 0; pixel < texture_pixels; ++pixel) {
        tiled_texture[pixel * 4] = static_cast<uint8_t>(pixel);
        tiled_texture[pixel * 4 + 1] = static_cast<uint8_t>(pixel >> 8);
        tiled_texture[pixel * 4 + 2] = static_cast<uint8_t>(pixel >> 16);
        tiled_texture[pixel * 4 + 3] = static_cast<uint8_t>(pixel >> 24);
    }
    std::vector<uint8_t> linear_texture;
    require(shift::xbox::untile_captured_texture_2d(
                texture_fetch, tiled_texture.data(), tiled_texture.size(),
                &linear_texture, &error),
            "captured tiled texture bytes were rejected");
    require(linear_texture.size() == texture_fetch.byte_length,
            "untiled texture byte length changed");

    std::vector<bool> seen_texture_pixels(texture_pixels, false);
    for (size_t pixel = 0; pixel < texture_pixels; ++pixel) {
        const uint32_t source_pixel = read_be32(linear_texture.data() + pixel * 4);
        require(source_pixel < texture_pixels && !seen_texture_pixels[source_pixel],
                "untile mapping duplicated or exceeded a source texel");
        seen_texture_pixels[source_pixel] = true;
    }
    for (bool seen : seen_texture_pixels) {
        require(seen, "untile mapping skipped a source texel");
    }
    const auto require_texture_source_pixel = [&](uint32_t x, uint32_t y,
                                                  uint32_t expected) {
        const size_t pixel = static_cast<size_t>(y) * texture_fetch.width + x;
        require(read_be32(linear_texture.data() + pixel * 4) == expected,
                "captured Xenos tiled address or 8-in-32 byte order changed");
    };
    require_texture_source_pixel(0, 0, 0);
    require_texture_source_pixel(4, 0, 8);
    require_texture_source_pixel(0, 2, 64);
    require_texture_source_pixel(0, 16, 512);
    require_texture_source_pixel(32, 0, 1024);
    require_texture_source_pixel(0, 32, 32768);
    require_texture_source_pixel(1023, 255, 262111);

    shift::xbox::CapturedTextureFetch unsupported_texture_layout = texture_fetch;
    unsupported_texture_layout.pitch -= 32;
    require(!shift::xbox::untile_captured_texture_2d(
                unsupported_texture_layout, tiled_texture.data(), tiled_texture.size(),
                &linear_texture, &error),
            "uncaptured texture pitch was accepted");
    require(!shift::xbox::untile_captured_texture_2d(
                texture_fetch, tiled_texture.data(), tiled_texture.size() - 1,
                &linear_texture, &error),
            "truncated captured texture was accepted");

    const uint8_t captured_indices[] = {
        0x00, 0x00, 0x00, 0x01, 0x00, 0x02,
        0x00, 0x02, 0x00, 0x01, 0x00, 0x03,
    };
    const std::vector<uint8_t> expected_vk_indices{
        0x00, 0x00, 0x01, 0x00, 0x02, 0x00,
        0x02, 0x00, 0x01, 0x00, 0x03, 0x00,
    };
    std::vector<uint8_t> normalized;
    require(shift::xbox::normalize_captured_buffer_bytes(
                input.index_endian_mode, captured_indices, sizeof(captured_indices),
                &normalized, &error),
            "captured 8-in-16 index bytes were rejected");
    require(normalized == expected_vk_indices,
            "captured index bytes did not normalize to Vulkan UInt16 values");

    const uint8_t captured_vertex_words[] = {
        0xBF, 0x80, 0x00, 0x00, 0xBF, 0x80, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
    };
    const std::vector<uint8_t> expected_vk_vertex_words{
        0x00, 0x00, 0x80, 0xBF, 0x00, 0x00, 0x80, 0xBF,
        0x00, 0x00, 0x00, 0x00,
    };
    require(shift::xbox::normalize_captured_buffer_bytes(
                vertex_fetch.endian_mode, captured_vertex_words,
                sizeof(captured_vertex_words),
                &normalized, &error),
            "captured 8-in-32 vertex words were rejected");
    require(normalized == expected_vk_vertex_words,
            "captured vertex words did not normalize to Vulkan float32 values");

    require(!shift::xbox::normalize_captured_buffer_bytes(
                3, captured_indices, sizeof(captured_indices), &normalized, &error),
            "uncaptured endian mode was accepted");
    require(!shift::xbox::normalize_captured_buffer_bytes(
                1, captured_indices, sizeof(captured_indices) - 1, &normalized, &error),
            "truncated 8-in-16 resource was accepted");

    uint32_t unsupported_vertex_descriptor[] = {
        captured_vertex_descriptor[0], captured_vertex_descriptor[1]};
    unsupported_vertex_descriptor[0] =
        (unsupported_vertex_descriptor[0] & 0xFFFFFFFCu) | 2u;
    require(!shift::xbox::decode_captured_vertex_fetch(
                unsupported_vertex_descriptor, &vertex_fetch, &error),
            "texture-fetch descriptor was accepted as a vertex buffer");

    uint32_t unsupported_texture_descriptor[6];
    for (size_t i = 0; i < 6; ++i) {
        unsupported_texture_descriptor[i] = captured_texture_descriptor[i];
    }
    unsupported_texture_descriptor[1] =
        (unsupported_texture_descriptor[1] & ~0x3Fu) | 5u;
    require(!shift::xbox::decode_captured_texture_fetch(
                unsupported_texture_descriptor, &texture_fetch, &error),
            "uncaptured texture format was accepted");

    uint8_t unsupported[sizeof(kCapturedPacket)];
    for (size_t i = 0; i < sizeof(kCapturedPacket); ++i) {
        unsupported[i] = kCapturedPacket[i];
    }
    unsupported[2] = 0x23;
    require(!shift::xbox::decode_captured_draw_indx(
                unsupported, sizeof(unsupported), &input, &error),
            "unsupported packet opcode was accepted");

    uint8_t disagreeing_counts[sizeof(kCapturedPacket)];
    for (size_t i = 0; i < sizeof(kCapturedPacket); ++i) {
        disagreeing_counts[i] = kCapturedPacket[i];
    }
    disagreeing_counts[9] = 0x07;
    require(!shift::xbox::decode_captured_draw_indx(
                disagreeing_counts, sizeof(disagreeing_counts), &input, &error),
            "disagreeing packet index counts were accepted");

    uint8_t unsupported_index_size[sizeof(kCapturedPacket)];
    for (size_t i = 0; i < sizeof(kCapturedPacket); ++i) {
        unsupported_index_size[i] = kCapturedPacket[i];
    }
    unsupported_index_size[10] |= 0x08;
    require(!shift::xbox::decode_captured_draw_indx(
                unsupported_index_size, sizeof(unsupported_index_size), &input, &error),
            "unsupported 32-bit index format was accepted");

    uint8_t unsupported_source[sizeof(kCapturedPacket)];
    for (size_t i = 0; i < sizeof(kCapturedPacket); ++i) {
        unsupported_source[i] = kCapturedPacket[i];
    }
    unsupported_source[11] |= 0x40;
    require(!shift::xbox::decode_captured_draw_indx(
                unsupported_source, sizeof(unsupported_source), &input, &error),
            "unsupported immediate-index source was accepted");

    uint8_t unsupported_endian[sizeof(kCapturedPacket)];
    for (size_t i = 0; i < sizeof(kCapturedPacket); ++i) {
        unsupported_endian[i] = kCapturedPacket[i];
    }
    unsupported_endian[16] = 0x80;
    require(!shift::xbox::decode_captured_draw_indx(
                unsupported_endian, sizeof(unsupported_endian), &input, &error),
            "uncaptured index endian mode was accepted");

    require(!shift::xbox::decode_captured_draw_indx(
                kCapturedPacket, sizeof(kCapturedPacket) - 4, &input, &error),
            "truncated packet was accepted");

    std::cout << "captured PM4_DRAW_INDX input check passed\n";
    return 0;
}
