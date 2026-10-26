#pragma once

#include "shift_xbox_draw_input.hpp"
#include "shift_xbox_shader_translate.hpp"

#include <vulkan/vulkan.h>

#include <cstddef>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace shift::xbox {

struct CapturedVulkanTexture {
    enum class Format : uint8_t {
        Rgba8,
        R8,
    };

    uint32_t fetch_constant_index = 0;
    CapturedTextureSampling sampling{};
    uint32_t width = 0;
    uint32_t height = 0;
    Format format = Format::Rgba8;
    std::vector<uint8_t> pixels;
};

struct CapturedVulkanDraw {
    CapturedRasterState raster;
    CapturedShaderConstants constants;
    CapturedTextureSampling texture_sampling;
    std::vector<uint32_t> vertex_shader_spirv;
    std::vector<uint32_t> geometry_shader_spirv;
    std::vector<uint32_t> pixel_shader_spirv;
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
    std::vector<uint32_t> vertex_shader_spirv;
    std::vector<uint32_t> pixel_shader_spirv;
    std::vector<uint32_t> single_sample_pixel_shader_spirv;
};

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
// compatible graphics pipelines, and sampler states across frames. Keep this
// object alive for one Vulkan device and clear it before destroying that
// device. Calls that share it must be externally synchronized.
class CapturedVulkanTextureCache {
 public:
    CapturedVulkanTextureCache();
    ~CapturedVulkanTextureCache();
    CapturedVulkanTextureCache(const CapturedVulkanTextureCache&) = delete;
    CapturedVulkanTextureCache& operator=(const CapturedVulkanTextureCache&) = delete;

    void clear();
    size_t size() const;
    size_t cached_pipeline_count() const;
    size_t cached_sampler_count() const;
    size_t cached_draw_buffer_count() const;

 private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
    friend struct CapturedVulkanTextureCacheAccess;
};

// Records and submits the captured game draws into the ReXGlue presenter image.
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
    std::vector<CapturedVulkanDrawVisibility>* draw_visibility = nullptr);

}  // namespace shift::xbox
