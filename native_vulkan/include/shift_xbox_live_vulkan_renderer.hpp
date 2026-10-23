#pragma once

#include "shift_xbox_draw_input.hpp"

#include <vulkan/vulkan.h>

#include <cstdint>
#include <string>
#include <vector>

namespace shift::xbox {

struct CapturedVulkanDraw {
    CapturedRasterState raster;
    CapturedShaderConstants constants;
    CapturedTextureSampling texture_sampling;
    std::vector<uint32_t> vertex_shader_spirv;
    std::vector<uint32_t> pixel_shader_spirv;
    std::vector<uint8_t> vertices;
    std::vector<uint8_t> indices;
    std::vector<uint8_t> texture_rgba8;
    uint32_t index_count = 0;
    uint32_t texture_width = 0;
    uint32_t texture_height = 0;
};

// Records and submits the captured game draws into the ReXGlue presenter image.
// The caller must externally synchronize the supplied graphics queue. The
// renderer uses only Vulkan 1.1 and has no window-system dependency.
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
    std::string* error);

}  // namespace shift::xbox
