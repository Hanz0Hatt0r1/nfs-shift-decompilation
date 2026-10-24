#pragma once

#include "shift_xbox_draw_input.hpp"
#include "shift_xbox_shader_translate.hpp"

#include <vulkan/vulkan.h>

#include <cstdint>
#include <string>
#include <vector>

namespace shift::xbox {

struct CapturedVulkanTexture {
    uint32_t fetch_constant_index = 0;
    CapturedTextureSampling sampling{};
    uint32_t width = 0;
    uint32_t height = 0;
    std::vector<uint8_t> rgba8;
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

// Records and submits the captured game draws into the ReXGlue presenter image.
// The caller must externally synchronize the supplied graphics queue. The
// renderer uses only Vulkan 1.1 and has no window-system dependency. Set
// depth_stencil_resolve_enabled only from an affirmative provider capability
// that includes enabled Vulkan entry points and SAMPLE_ZERO support for both
// depth and stencil, not from extension enumeration alone.
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
    CapturedVulkanSamplerCapabilities sampler_capabilities = {});

}  // namespace shift::xbox
