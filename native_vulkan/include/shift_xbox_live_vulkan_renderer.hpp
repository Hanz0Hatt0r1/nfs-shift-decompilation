#pragma once

#include "shift_xbox_draw_input.hpp"
#include "shift_xbox_shader_translate.hpp"

#include <vulkan/vulkan.h>

#include <cstddef>
#include <cstdint>
#include <limits>
#include <memory>
#include <string>
#include <vector>

namespace shift::xbox {

struct CapturedVulkanTexture {
    enum class Format : uint8_t {
        Rgba8,
        R8,
        Rg16Float,
    };

    uint32_t fetch_constant_index = 0;
    CapturedTextureSampling sampling{};
    uint32_t width = 0;
    uint32_t height = 0;
    Format format = Format::Rgba8;
    std::vector<uint8_t> pixels;
    // Keep the guest descriptor with the decoded pixels so ordered
    // Copy/Convert results can replace a stale RAM snapshot by address/layout.
    uint32_t guest_address = 0;
    uint32_t guest_format = 0;
    uint32_t guest_endian = 0;
    uint32_t guest_pitch = 0;
    bool guest_tiled = false;
    bool guest_packed_mips = false;
    // True only when an earlier operation in the same PM4 stream produced an
    // exact-layout Vulkan image for this fetch descriptor.
    bool guest_copy_source = false;
};

struct CapturedVulkanDraw {
    CapturedRasterState raster;
    CapturedShaderConstants constants;
    CapturedTextureSampling texture_sampling;
    std::vector<uint32_t> vertex_shader_spirv;
    std::vector<uint32_t> geometry_shader_spirv;
    std::vector<uint32_t> pixel_shader_spirv;
    // Gamma render targets blend in linear light, so the frame Copy/Convert
    // path needs a fragment variant that leaves target encoding to the copy.
    std::vector<uint32_t> pixel_shader_spirv_linear_target;
    std::vector<uint8_t> vertices;
    std::vector<uint8_t> indices;
    std::vector<uint8_t> texture_rgba8;
    std::vector<CapturedVulkanTexture> textures;
    std::vector<CapturedVertexInputAttribute> vertex_input_attributes;
    uint32_t vertex_stride_bytes = 12;
    PrimitiveTopology topology = PrimitiveTopology::TriangleList;
    bool auto_index = false;
    uint32_t index_count = 0;
    uint32_t texture_width = 0;
    uint32_t texture_height = 0;
};

struct CapturedVulkanCopy {
    CapturedCopyState state{};
    uint32_t source_width = 0;
    uint32_t source_height = 0;
    uint32_t color_clear = 0;
    uint32_t color_clear_lo = 0;
    uint32_t depth_clear = 0;
    bool clear_values_ready = false;
    bool source_gamma = false;
    // Set by the ordered executor for non-presenter writes, including guest
    // format 6 copies whose destination must remain in the resource cache.
    bool retain_destination = false;
    std::vector<uint32_t> vertex_shader_spirv;
    std::vector<uint32_t> pixel_shader_spirv;
    std::vector<uint32_t> single_sample_pixel_shader_spirv;
    std::vector<uint32_t> gamma_pixel_shader_spirv;
    std::vector<uint32_t> gamma_single_sample_pixel_shader_spirv;
};

struct CapturedVulkanOperation {
    enum class Type : uint8_t {
        Draw,
        CopyConvert,
        UnresolvedDraw,
        UnresolvedCopy,
    };

    Type type = Type::Draw;
    // Draw operations reference the corresponding entry in the frame draw list.
    // UnresolvedDraw preserves a packet that could not be decoded or prepared.
    uint32_t draw_index = std::numeric_limits<uint32_t>::max();
    uint32_t packet_index = std::numeric_limits<uint32_t>::max();
    CapturedCopyState copy_state{};
    uint32_t source_width = 0;
    uint32_t source_height = 0;
    // Raw Xenos source-target registers are needed to resolve the address,
    // format, and sample layout of mode-6 Copy/Convert operations.
    uint32_t source_surface_info = 0;
    uint32_t source_color_info = 0;
    uint32_t source_depth_info = 0;
    uint32_t source_mode_control = 0;
    bool source_raster_ready = false;
    CapturedRasterState source_raster{};
    // Copy/Convert packets carry their own compiled shaders so an executor can
    // replay the PM4 stream without borrowing the final presenter copy.
    bool copy_shaders_ready = false;
    CapturedVulkanCopy copy{};
};

std::string describe_captured_vulkan_operations(
    const std::vector<CapturedVulkanOperation>& operations);

struct CapturedVulkanSamplerCapabilities {
    bool anisotropy_enabled = false;
    float max_anisotropy = 1.0f;
};

struct CapturedVulkanSourceReadback {
    enum class Status : uint8_t {
        NotRequested,
        Captured,
        Unsupported,
    };

    Status status = Status::NotRequested;
    uint32_t width = 0;
    uint32_t height = 0;
    VkFormat format = VK_FORMAT_UNDEFINED;
    uint32_t sample_count = 0;
    bool multisample_average_resolve = false;
    std::string reason;
    std::vector<uint8_t> bytes;
};

struct CapturedVulkanDrawVisibility {
    bool available = false;
    // Vulkan 1.1 guarantees non-precise occlusion queries; this reports only
    // whether any samples passed, not an exact sample count or color write.
    bool any_samples_passed = false;
};

// Reuses live R8 planes, per-draw vertex/index/uniform upload buffers,
// compatible graphics pipelines, sampler states, and compatible descriptor
// layouts across frames. Keep this object alive for one Vulkan device and
// clear it before destroying that device. Calls that share it must be
// externally synchronized.
class CapturedVulkanTextureCache {
 public:
    CapturedVulkanTextureCache();
    ~CapturedVulkanTextureCache();
    CapturedVulkanTextureCache(const CapturedVulkanTextureCache&) = delete;
    CapturedVulkanTextureCache& operator=(const CapturedVulkanTextureCache&) = delete;

    // Waits for every submitted frame that may still read guest-uploaded data.
    // Guest memory is copied into renderer-owned upload buffers on each draw.
    bool wait_for_guest_memory_coherency(std::string* error);
    // Safe to query off the Vulkan thread; false means a coherency drain can
    // return without dispatching to the thread that owns the cache.
    bool has_in_flight_frames() const noexcept;
    void clear();
    size_t size() const;
    size_t cached_pipeline_count() const;
    size_t cached_sampler_count() const;
    size_t cached_draw_buffer_count() const;
    size_t cached_descriptor_layout_count() const;
    size_t descriptor_layout_cache_hits() const;
    // GPU-resident intermediate Copy/Convert destinations keyed by guest
    // address and the complete captured destination layout.
    size_t cached_guest_copy_image_count() const;
    // GPU-resident Xenos render targets retained between copy segments and
    // guest frames, keyed by the complete captured raster layout.
    size_t cached_guest_edram_target_count() const;

 private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
    friend struct CapturedVulkanTextureCacheAccess;
};

// Records and submits captured draws for one Xenos color/depth target into the
// ReXGlue presenter image. The caller must split ordered target switches into
// separate submissions; this function does not emulate Xenos EDRAM aliasing.
//
// With a texture cache and no readback request, frame resources remain owned by
// that cache until their Vulkan fences signal; without a cache, or with a
// readback request, the call waits for completion. The caller must externally
// synchronize the supplied graphics queue. The optional pipeline cache must
// belong to device and be externally synchronized across calls; its lifetime
// remains owned by the caller. The renderer uses only Vulkan 1.1 and has no
// window-system dependency. Set
// depth_stencil_resolve_enabled only from an affirmative provider capability
// that includes enabled Vulkan entry points and SAMPLE_ZERO support for both
// depth and stencil, not from extension enumeration alone.
// When draw_visibility is supplied, the renderer waits for completion and
// returns one optional non-precise occlusion result per submitted draw.
// The optional operation stream preserves packet order for validation and
// failure diagnostics. This single-frame function does not execute it.
bool submit_captured_vulkan_frame(
    VkPhysicalDevice physical_device,
    VkDevice device,
    VkQueue queue,
    uint32_t queue_family_index,
    VkImage output_image,
    VkImageView output_view,
    bool output_written_before,
    uint32_t output_width,
    uint32_t output_height,
    const std::vector<CapturedVulkanDraw>& draws,
    std::string* error,
    std::vector<uint32_t>* output_readback = nullptr,
    bool geometry_shader_enabled = false,
    const CapturedVulkanCopy* copy = nullptr,
    bool depth_stencil_resolve_enabled = false,
    CapturedVulkanSamplerCapabilities sampler_capabilities = {},
    VkPipelineCache pipeline_cache = VK_NULL_HANDLE,
    CapturedVulkanTextureCache* texture_cache = nullptr,
    CapturedVulkanSourceReadback* source_readback = nullptr,
    std::vector<CapturedVulkanDrawVisibility>* draw_visibility = nullptr,
    const std::vector<CapturedVulkanOperation>* operations = nullptr,
    bool preserve_edram_target = false);

// Executes compatible Draw segments and their following Copy/Convert packets
// in PM4 order. Intermediate copy images and same-layout color/depth targets
// remain GPU-resident in texture_cache. Xenos EDRAM alias reinterpretation and
// reuse of cached images as guest textures are still unsupported.
bool submit_captured_vulkan_operation_stream(
    VkPhysicalDevice physical_device,
    VkDevice device,
    VkQueue queue,
    uint32_t queue_family_index,
    VkImage output_image,
    VkImageView output_view,
    bool output_written_before,
    uint32_t output_width,
    uint32_t output_height,
    const std::vector<CapturedVulkanDraw>& draws,
    const std::vector<CapturedVulkanOperation>& operations,
    std::string* error,
    std::vector<uint32_t>* output_readback = nullptr,
    bool geometry_shader_enabled = false,
    const CapturedVulkanCopy* presenter_copy = nullptr,
    bool depth_stencil_resolve_enabled = false,
    CapturedVulkanSamplerCapabilities sampler_capabilities = {},
    VkPipelineCache pipeline_cache = VK_NULL_HANDLE,
    CapturedVulkanTextureCache* texture_cache = nullptr,
    CapturedVulkanSourceReadback* source_readback = nullptr,
    std::vector<CapturedVulkanDrawVisibility>* draw_visibility = nullptr);

}  // namespace shift::xbox
