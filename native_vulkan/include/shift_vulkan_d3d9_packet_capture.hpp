#pragma once

#include "shift_recompiled_pcode_module.hpp"

#include <cstdint>
#include <filesystem>
#include <map>
#include <mutex>
#include <string>
#include <vector>

namespace shift::vulkan {

// Wraps an existing D3D9 adapter table, copies guest buffer updates, and writes
// each synchronous v1 draw packet as one SHIFT.D3D9RuntimeCaptureSchema/1
// capture that the Vulkan capture-bundle builder can consume.
class D3d9PacketCaptureAdapter {
public:
    explicit D3d9PacketCaptureAdapter(
        std::filesystem::path output_root,
        uint32_t draw_limit = 1);

    // Enables managed DXT5 capture only; live Vulkan upload support is separate.
    bool install(
        runtime::RecompiledGuestD3d9AdapterInfo& adapter,
        std::string& error);

    uint32_t captured_draw_count() const;

private:
    struct BufferSnapshot {
        uint32_t guest_device = 0;
        uint32_t size = 0;
        uint32_t usage = 0;
        uint32_t format = 0;
        uint32_t fvf = 0;
        uint32_t pool = 0;
        bool has_unproven_discard_semantics = false;
        std::vector<uint8_t> bytes;
        std::vector<uint8_t> initialized;
    };

    static bool create_device_callback(
        void*, uint32_t, uint32_t,
        runtime::RecompiledGuestD3d9PresentationParameters&, std::string&);
    static bool create_texture_callback(
        void*, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t,
        uint32_t, uint32_t, std::string&);
    static void release_texture_callback(void*, uint32_t);
    static bool create_vertex_buffer_callback(
        void*, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t,
        std::string&);
    static bool update_vertex_buffer_callback(
        void*, uint32_t, uint32_t, const uint8_t*, size_t, std::string&);
    static void release_vertex_buffer_callback(void*, uint32_t);
    static bool create_index_buffer_callback(
        void*, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t,
        std::string&);
    static bool update_index_buffer_callback(
        void*, uint32_t, uint32_t, const uint8_t*, size_t, std::string&);
    static void release_index_buffer_callback(void*, uint32_t);
    static bool clear_callback(
        void*, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, std::string&);
    static bool present_callback(void*, std::string&);
    static bool draw_indexed_primitive_callback(
        void*, const runtime::RecompiledGuestD3d9DrawIndexedPrimitivePacket&,
        std::string&);

    bool create_buffer(
        uint32_t guest_buffer,
        uint32_t guest_device,
        uint32_t size,
        uint32_t usage,
        uint32_t format,
        uint32_t fvf,
        uint32_t pool,
        bool index_buffer,
        std::string& error);
    bool update_buffer(
        uint32_t guest_buffer,
        uint32_t offset,
        const uint8_t* data,
        size_t size,
        bool index_buffer,
        std::string& error);
    void release_buffer(uint32_t guest_buffer, bool index_buffer);
    bool capture_draw(
        const runtime::RecompiledGuestD3d9DrawIndexedPrimitivePacket& packet,
        std::string& error);
    bool forward_draw(
        const runtime::RecompiledGuestD3d9DrawIndexedPrimitivePacket& packet,
        std::string& error);

    std::filesystem::path output_root_;
    uint32_t draw_limit_ = 1;
    uint32_t captured_draw_count_ = 0;
    bool installed_ = false;
    runtime::RecompiledGuestD3d9AdapterInfo downstream_{};
    std::map<uint32_t, BufferSnapshot> vertex_buffers_;
    std::map<uint32_t, BufferSnapshot> index_buffers_;
    mutable std::mutex mutex_;
};

}  // namespace shift::vulkan
