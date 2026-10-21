#pragma once

#include <cstdint>
#include <vulkan/vulkan.h>

namespace shift::vulkan {

// SVTP/1 values 1-4 are legacy UNORM repeat/edge modes; 5-6 add border.
// Adding 8 selects sRGB sampling for the corresponding modes.
constexpr bool texture_sampler_mode_valid(uint32_t mode) {
    return (mode >= 1 && mode <= 6) || (mode >= 9 && mode <= 14);
}

constexpr bool texture_sampler_mode_linear(uint32_t mode) {
    return mode == 2 || mode == 4 || mode == 6 ||
           mode == 10 || mode == 12 || mode == 14;
}

constexpr bool texture_sampler_mode_srgb(uint32_t mode) {
    return mode >= 9 && mode <= 14;
}

constexpr VkSamplerAddressMode texture_sampler_address_mode(uint32_t mode) {
    if (mode == 3 || mode == 4 || mode == 11 || mode == 12) {
        return VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    }
    if (mode == 5 || mode == 6 || mode == 13 || mode == 14) {
        return VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_BORDER;
    }
    return VK_SAMPLER_ADDRESS_MODE_REPEAT;
}

constexpr VkFormat texture_sampler_format(uint32_t mode) {
    return texture_sampler_mode_srgb(mode)
        ? VK_FORMAT_R8G8B8A8_SRGB
        : VK_FORMAT_R8G8B8A8_UNORM;
}

}  // namespace shift::vulkan
