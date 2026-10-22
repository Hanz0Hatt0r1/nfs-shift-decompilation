#include "shift_vulkan_d3d9_packet_capture.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include <vector>

namespace runtime = shift::runtime;

namespace {

struct DownstreamState {
    uint32_t creates = 0;
    uint32_t updates = 0;
};

void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "packet capture adapter check failed: " << message << '\n';
        std::exit(1);
    }
}

bool downstream_create_vertex_buffer(
    void* context, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t,
    std::string&) {
    ++static_cast<DownstreamState*>(context)->creates;
    return true;
}

bool downstream_update_vertex_buffer(
    void* context, uint32_t, uint32_t, const uint8_t*, size_t, std::string&) {
    ++static_cast<DownstreamState*>(context)->updates;
    return true;
}

bool downstream_create_index_buffer(
    void* context, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t,
    std::string&) {
    ++static_cast<DownstreamState*>(context)->creates;
    return true;
}

bool downstream_update_index_buffer(
    void* context, uint32_t, uint32_t, const uint8_t*, size_t, std::string&) {
    ++static_cast<DownstreamState*>(context)->updates;
    return true;
}

std::string read_text(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    require(static_cast<bool>(input), "expected capture file exists");
    return std::string(std::istreambuf_iterator<char>(input), {});
}

std::vector<uint8_t> read_bytes(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    require(static_cast<bool>(input), "expected binary payload exists");
    return std::vector<uint8_t>(std::istreambuf_iterator<char>(input), {});
}

runtime::RecompiledGuestD3d9DrawIndexedPrimitivePacket make_packet() {
    runtime::RecompiledGuestD3d9DrawIndexedPrimitivePacket packet{};
    packet.guest_device = 0x42;
    packet.sequence = 1;
    packet.primitive_type = 4;
    packet.min_vertex_index = 0;
    packet.num_vertices = 4;
    packet.primitive_count = 2;
    packet.streams[0] = {0x10, 0, 24, 1, 96, 0, 0, 0};
    packet.guest_index_buffer = 0x20;
    packet.index_buffer_size = 12;
    packet.index_buffer_format = 101;
    packet.guest_vertex_declaration = 0x30;
    packet.vertex_declaration_elements = {
        {0x00000000, 0x00000002},  // FLOAT3 POSITION0
        {0x0000ff00, 0x00000011},  // D3DDECL_END
    };
    packet.guest_vertex_shader = 0x40;
    packet.vertex_shader_tokens = {0xfffe0300, 0x0000ffff};
    packet.guest_pixel_shader = 0x50;
    packet.pixel_shader_tokens = {0xffff0300, 0x0000ffff};
    packet.vertex_float_constants[0] = 0x3f800001;
    packet.vertex_float_constants[1] = 0x80000000;
    packet.vertex_float_constant_set_mask[0] = 1;
    packet.pixel_bool_constants[0] = 0xffffffff;
    packet.pixel_bool_constant_set_mask = 1;

    runtime::RecompiledGuestD3d9TextureBinding texture{};
    texture.stage = 0;
    texture.guest_texture = 0x60;
    texture.width = 1;
    texture.height = 1;
    texture.levels = 1;
    texture.format = 21;
    texture.pool = 1;
    texture.pitch = 4;
    texture.mip_data.push_back({1, 1, 4, {1, 2, 3, 4}});
    packet.textures.push_back(texture);

    runtime::RecompiledGuestD3d9TextureBinding render_target_texture{};
    render_target_texture.stage = 1;
    render_target_texture.guest_texture = 0x61;
    render_target_texture.width = 800;
    render_target_texture.height = 600;
    render_target_texture.levels = 1;
    render_target_texture.format = 21;
    render_target_texture.backend_owned = true;
    packet.textures.push_back(render_target_texture);

    runtime::RecompiledGuestD3d9TextureBinding dxt5_texture{};
    dxt5_texture.stage = 2;
    dxt5_texture.guest_texture = 0x62;
    dxt5_texture.width = 4;
    dxt5_texture.height = 4;
    dxt5_texture.levels = 1;
    dxt5_texture.format = 0x35545844;
    dxt5_texture.pool = 1;
    dxt5_texture.pitch = 16;
    dxt5_texture.mip_data.push_back({4, 4, 16,
        {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16}});
    packet.textures.push_back(dxt5_texture);

    packet.render_states = {
        {0x42, 7, 1}, {0x42, 14, 1}, {0x42, 23, 4}, {0x42, 27, 0},
        {0x42, 19, 1}, {0x42, 20, 2}, {0x42, 22, 1}, {0x42, 168, 15},
        {0x42, 171, 1}, {0x42, 206, 0},
    };
    packet.sampler_states = {
        {0, 1, 1}, {0, 2, 1}, {0, 5, 2}, {0, 6, 2}, {0, 7, 0}, {0, 11, 1},
    };
    packet.viewport = {0, 0, 800, 600, 0, 0x3f800000};
    packet.render_targets.push_back({0, 0x70, {21, 1, 1, 0, 0, 0, 800, 600}});
    packet.has_depth_surface = true;
    packet.depth_surface = {0, 0x71, {75, 1, 2, 0, 0, 0, 800, 600}};
    packet.last_clear_flags = 3;
    packet.last_clear_depth_bits = 0x3f800000;
    return packet;
}

}  // namespace

int main() {
    const auto root = std::filesystem::temp_directory_path() /
                      "shift-vulkan-d3d9-packet-adapter-check";
    std::filesystem::remove_all(root);

    DownstreamState downstream{};
    runtime::RecompiledGuestD3d9AdapterInfo info{};
    info.backend_context = &downstream;
    info.create_vertex_buffer = &downstream_create_vertex_buffer;
    info.update_vertex_buffer = &downstream_update_vertex_buffer;
    info.create_index_buffer = &downstream_create_index_buffer;
    info.update_index_buffer = &downstream_update_index_buffer;

    shift::vulkan::D3d9PacketCaptureAdapter adapter(root, 1);
    std::string error;
    require(adapter.install(info, error), "install adapter");
    require(info.backend_context != &downstream, "adapter owns the callback context");
    require(info.supports_dxt5_texture,
            "capture adapter enables guest-managed DXT5 packet snapshots");

    std::vector<uint8_t> vertex_bytes(96);
    for (size_t i = 0; i < vertex_bytes.size(); ++i) vertex_bytes[i] = static_cast<uint8_t>(i + 1);
    std::vector<uint8_t> index_bytes = {0, 0, 1, 0, 2, 0, 1, 0, 2, 0, 3, 0};
    const auto expected_vertex_bytes = vertex_bytes;
    const auto expected_index_bytes = index_bytes;
    require(info.create_vertex_buffer(info.backend_context, 0x10, 0x42, 96, 0, 0, 0, error),
            "forward and cache vertex buffer create");
    require(info.update_vertex_buffer(info.backend_context, 0x10, 0,
            vertex_bytes.data(), vertex_bytes.size(), error),
            "forward and copy vertex buffer update");
    require(info.create_index_buffer(info.backend_context, 0x20, 0x42, 12, 0, 101, 0, error),
            "forward and cache index buffer create");
    require(info.update_index_buffer(info.backend_context, 0x20, 0,
            index_bytes.data(), index_bytes.size(), error),
            "forward and copy index buffer update");
    require(downstream.creates == 2 && downstream.updates == 2,
            "existing resource callbacks are forwarded");

    auto packet = make_packet();
    if (!info.draw_indexed_primitive(info.backend_context, packet, error)) {
        std::cerr << "packet capture adapter detail: " << error << '\n';
        require(false, "capture typed draw packet");
    }
    require(adapter.captured_draw_count() == 1, "count captured draw");
    std::fill(vertex_bytes.begin(), vertex_bytes.end(), 0xee);
    std::fill(index_bytes.begin(), index_bytes.end(), 0xee);
    std::fill(packet.textures[0].mip_data[0].bytes.begin(),
              packet.textures[0].mip_data[0].bytes.end(), 0xee);

    const auto draw_dir = root / "draw_00000042_1";
    const std::string capture = read_text(draw_dir / "capture.jsonl");
    require(capture.find("\"guest_draw_sequence\":1") != std::string::npos,
            "packet sequence is preserved separately from event_index");
    require(capture.find("\"values_bits\":[1065353217,2147483648,0,0]") != std::string::npos,
            "float constant DWORD bits are preserved exactly");
    require(capture.find("\"pixel_bool_constants\":[4294967295") != std::string::npos,
            "BOOL payload keeps its DWORD value");
    require(capture.find("\"pixel_bool_constant_set_mask\":1") != std::string::npos,
            "BOOL set mask is preserved");
    require(capture.find("\"snapshot_status\":\"backend-owned\"") != std::string::npos,
            "backend-owned render target texture has no fabricated pixels");
    require(capture.find("\"stream_source_frequencies\":[{\"stream\":0,\"setting\":1}") != std::string::npos,
            "all stream frequency settings reach the consumer event");
    require(capture.find("\"surface_width\":800") != std::string::npos,
            "surface descriptor dimensions are serialized");

    require(read_bytes(draw_dir / "buffers/00000010_vb.bin") == expected_vertex_bytes,
            "buffer update bytes are copied before the callback returns");
    require(read_bytes(draw_dir / "buffers/00000020_ib.bin") == expected_index_bytes,
            "index update bytes are copied before the callback returns");
    const auto dds = read_bytes(draw_dir / "textures/00000060_s0.dds");
    require(dds.size() == 132 && dds[0] == 'D' && dds[1] == 'D' &&
                std::vector<uint8_t>(dds.end() - 4, dds.end()) ==
                    std::vector<uint8_t>({1, 2, 3, 4}),
            "managed A8R8G8B8 mip is copied as a DDS snapshot");
    const auto dxt5_dds = read_bytes(draw_dir / "textures/00000062_s2.dds");
    require(dxt5_dds.size() == 144 &&
                std::string(dxt5_dds.begin() + 84, dxt5_dds.begin() + 88) == "DXT5" &&
                std::vector<uint8_t>(dxt5_dds.end() - 16, dxt5_dds.end()) ==
                    std::vector<uint8_t>({1, 2, 3, 4, 5, 6, 7, 8,
                        9, 10, 11, 12, 13, 14, 15, 16}),
            "managed DXT5 mip blocks are copied without decompression");
    require(info.draw_indexed_primitive(info.backend_context, packet, error),
            "draws beyond capture limit continue downstream");
    require(adapter.captured_draw_count() == 1 &&
                !std::filesystem::exists(root / "draw_00000042_2"),
            "capture limit avoids repeated snapshots");

    error.clear();
    require(!info.update_vertex_buffer(info.backend_context, 0x10, 96,
                vertex_bytes.data(), 1, error) &&
                error.find("outside its created resource") != std::string::npos,
            "out-of-range resource update fails explicitly");

    auto incomplete_root = root.string() + "-incomplete";
    shift::vulkan::D3d9PacketCaptureAdapter incomplete_adapter(incomplete_root, 1);
    runtime::RecompiledGuestD3d9AdapterInfo incomplete_info{};
    error.clear();
    require(incomplete_adapter.install(incomplete_info, error),
            "install independent adapter for partial dynamic-buffer check");
    std::array<uint8_t, 24> partial_vertex{};
    require(incomplete_info.create_vertex_buffer(incomplete_info.backend_context,
                0x10, 0x42, 96, 0x200, 0, 0, error),
            "create dynamic guest vertex buffer");
    require(incomplete_info.update_vertex_buffer(incomplete_info.backend_context,
                0x10, 0, partial_vertex.data(), partial_vertex.size(), error),
            "retain partial dynamic update without blocking guest update");
    require(incomplete_info.create_index_buffer(incomplete_info.backend_context,
                0x20, 0x42, 12, 0, 101, 0, error),
            "create index buffer for partial dynamic-buffer check");
    require(incomplete_info.update_index_buffer(incomplete_info.backend_context,
                0x20, 0, expected_index_bytes.data(), expected_index_bytes.size(), error),
            "populate index buffer for partial dynamic-buffer check");
    auto incomplete_packet = make_packet();
    incomplete_packet.streams[0].usage = 0x200;
    error.clear();
    require(!incomplete_info.draw_indexed_primitive(
                incomplete_info.backend_context, incomplete_packet, error) &&
                error.find("partial updates without lock flags") != std::string::npos,
            "partial dynamic buffer fails closed without D3DLOCK flags");

    if (!std::getenv("SHIFT_D3D9_PACKET_CAPTURE_KEEP")) {
        std::filesystem::remove_all(root);
        std::filesystem::remove_all(incomplete_root);
    }
    return 0;
}
