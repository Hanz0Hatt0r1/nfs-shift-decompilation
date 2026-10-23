#include "shift_xbox_live_vulkan_renderer.hpp"

#include <vulkan/vulkan.h>

#include <array>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include <utility>
#include <vector>

namespace {

uint32_t validation_errors = 0;

VKAPI_ATTR VkBool32 VKAPI_CALL ValidationCallback(
    VkDebugUtilsMessageSeverityFlagBitsEXT severity,
    VkDebugUtilsMessageTypeFlagsEXT,
    const VkDebugUtilsMessengerCallbackDataEXT* data,
    void*) {
    if (severity & VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT) {
        ++validation_errors;
        std::cerr << "Vulkan validation error: " << data->pMessage << '\n';
    }
    return VK_FALSE;
}

bool has_layer(const char* name) {
    uint32_t count = 0;
    if (vkEnumerateInstanceLayerProperties(&count, nullptr) != VK_SUCCESS) return false;
    std::vector<VkLayerProperties> layers(count);
    if (vkEnumerateInstanceLayerProperties(&count, layers.data()) != VK_SUCCESS) return false;
    for (const auto& layer : layers) {
        if (std::string(layer.layerName) == name) return true;
    }
    return false;
}

bool has_extension(const char* name) {
    uint32_t count = 0;
    if (vkEnumerateInstanceExtensionProperties(nullptr, &count, nullptr) != VK_SUCCESS) return false;
    std::vector<VkExtensionProperties> extensions(count);
    if (vkEnumerateInstanceExtensionProperties(nullptr, &count, extensions.data()) != VK_SUCCESS) {
        return false;
    }
    for (const auto& extension : extensions) {
        if (std::string(extension.extensionName) == name) return true;
    }
    return false;
}

uint32_t find_memory_type(
    VkPhysicalDeviceMemoryProperties const& properties,
    uint32_t type_bits,
    VkMemoryPropertyFlags required,
    VkMemoryPropertyFlags preferred) {
    uint32_t fallback = UINT32_MAX;
    for (uint32_t i = 0; i < properties.memoryTypeCount; ++i) {
        if ((type_bits & (1u << i)) == 0) continue;
        const auto flags = properties.memoryTypes[i].propertyFlags;
        if ((flags & required) != required) continue;
        if ((flags & preferred) == preferred) return i;
        if (fallback == UINT32_MAX) fallback = i;
    }
    return fallback;
}

bool read_spirv(const char* path, std::vector<uint32_t>* output) {
    std::ifstream file(path, std::ios::binary);
    if (!file) return false;
    std::vector<char> bytes((std::istreambuf_iterator<char>(file)),
                            std::istreambuf_iterator<char>());
    if (bytes.empty() || (bytes.size() % sizeof(uint32_t)) != 0) return false;
    output->resize(bytes.size() / sizeof(uint32_t));
    std::memcpy(output->data(), bytes.data(), bytes.size());
    return output->front() == 0x07230203u;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "usage: xbox_live_vulkan_renderer_check vertex.spv fragment.spv\n";
        return 2;
    }

    VkDebugUtilsMessengerCreateInfoEXT debug_info{};
    debug_info.sType = VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT;
    debug_info.messageSeverity = VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT;
    debug_info.messageType = VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT |
                             VK_DEBUG_UTILS_MESSAGE_TYPE_VALIDATION_BIT_EXT |
                             VK_DEBUG_UTILS_MESSAGE_TYPE_PERFORMANCE_BIT_EXT;
    debug_info.pfnUserCallback = ValidationCallback;
    const bool use_validation = has_layer("VK_LAYER_KHRONOS_validation");
    const bool use_debug_utils = use_validation && has_extension(VK_EXT_DEBUG_UTILS_EXTENSION_NAME);
    const char* layer_name = "VK_LAYER_KHRONOS_validation";
    const char* extension_name = VK_EXT_DEBUG_UTILS_EXTENSION_NAME;
    VkApplicationInfo app{};
    app.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
    app.pApplicationName = "SHIFT synthetic Vulkan point-draw smoke";
    app.apiVersion = VK_API_VERSION_1_1;
    VkInstanceCreateInfo instance_info{};
    instance_info.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    instance_info.pApplicationInfo = &app;
    instance_info.enabledLayerCount = use_validation ? 1u : 0u;
    instance_info.ppEnabledLayerNames = use_validation ? &layer_name : nullptr;
    instance_info.enabledExtensionCount = use_debug_utils ? 1u : 0u;
    instance_info.ppEnabledExtensionNames = use_debug_utils ? &extension_name : nullptr;
    instance_info.pNext = use_debug_utils ? &debug_info : nullptr;
    VkInstance instance = VK_NULL_HANDLE;
    VkResult result = vkCreateInstance(&instance_info, nullptr, &instance);
    if (result != VK_SUCCESS) {
        std::cerr << "vkCreateInstance failed: " << result << '\n';
        return 1;
    }

    VkDebugUtilsMessengerEXT messenger = VK_NULL_HANDLE;
    if (use_debug_utils) {
        auto create_messenger = reinterpret_cast<PFN_vkCreateDebugUtilsMessengerEXT>(
            vkGetInstanceProcAddr(instance, "vkCreateDebugUtilsMessengerEXT"));
        if (create_messenger) create_messenger(instance, &debug_info, nullptr, &messenger);
    }

    uint32_t physical_count = 0;
    result = vkEnumeratePhysicalDevices(instance, &physical_count, nullptr);
    if (result != VK_SUCCESS || physical_count == 0) {
        std::cerr << "no Vulkan physical device available\n";
        if (messenger) {
            auto destroy_messenger = reinterpret_cast<PFN_vkDestroyDebugUtilsMessengerEXT>(
                vkGetInstanceProcAddr(instance, "vkDestroyDebugUtilsMessengerEXT"));
            if (destroy_messenger) destroy_messenger(instance, messenger, nullptr);
        }
        vkDestroyInstance(instance, nullptr);
        return 77;
    }
    std::vector<VkPhysicalDevice> physical_devices(physical_count);
    vkEnumeratePhysicalDevices(instance, &physical_count, physical_devices.data());
    VkPhysicalDevice physical_device = VK_NULL_HANDLE;
    uint32_t queue_family = UINT32_MAX;
    VkPhysicalDeviceProperties device_properties{};
    for (VkPhysicalDevice candidate : physical_devices) {
        uint32_t family_count = 0;
        vkGetPhysicalDeviceQueueFamilyProperties(candidate, &family_count, nullptr);
        std::vector<VkQueueFamilyProperties> families(family_count);
        vkGetPhysicalDeviceQueueFamilyProperties(candidate, &family_count, families.data());
        for (uint32_t i = 0; i < family_count; ++i) {
            if (families[i].queueCount && (families[i].queueFlags & VK_QUEUE_GRAPHICS_BIT)) {
                physical_device = candidate;
                queue_family = i;
                break;
            }
        }
        if (physical_device) break;
    }
    if (!physical_device) {
        std::cerr << "no graphics queue family available\n";
        vkDestroyInstance(instance, nullptr);
        return 77;
    }
    vkGetPhysicalDeviceProperties(physical_device, &device_properties);
    if (device_properties.apiVersion < VK_API_VERSION_1_1) {
        std::cerr << "Vulkan 1.1 device required for negative viewport support\n";
        vkDestroyInstance(instance, nullptr);
        return 77;
    }

    const float queue_priority = 1.0f;
    VkDeviceQueueCreateInfo queue_info{};
    queue_info.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
    queue_info.queueFamilyIndex = queue_family;
    queue_info.queueCount = 1;
    queue_info.pQueuePriorities = &queue_priority;
    VkDeviceCreateInfo device_info{};
    device_info.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
    device_info.queueCreateInfoCount = 1;
    device_info.pQueueCreateInfos = &queue_info;
    VkDevice device = VK_NULL_HANDLE;
    result = vkCreateDevice(physical_device, &device_info, nullptr, &device);
    if (result != VK_SUCCESS) {
        std::cerr << "vkCreateDevice failed: " << result << '\n';
        vkDestroyInstance(instance, nullptr);
        return 1;
    }
    VkQueue queue = VK_NULL_HANDLE;
    vkGetDeviceQueue(device, queue_family, 0, &queue);

    VkPhysicalDeviceMemoryProperties memory_properties{};
    vkGetPhysicalDeviceMemoryProperties(physical_device, &memory_properties);
    VkImage output_image = VK_NULL_HANDLE;
    VkDeviceMemory output_memory = VK_NULL_HANDLE;
    VkImageView output_view = VK_NULL_HANDLE;
    VkImageCreateInfo image_info{};
    image_info.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
    image_info.imageType = VK_IMAGE_TYPE_2D;
    image_info.format = VK_FORMAT_A2B10G10R10_UNORM_PACK32;
    image_info.extent = {64, 64, 1};
    image_info.mipLevels = 1;
    image_info.arrayLayers = 1;
    image_info.samples = VK_SAMPLE_COUNT_1_BIT;
    image_info.tiling = VK_IMAGE_TILING_OPTIMAL;
    image_info.usage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_SAMPLED_BIT |
                       VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
    image_info.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    if (vkCreateImage(device, &image_info, nullptr, &output_image) != VK_SUCCESS) {
        std::cerr << "vkCreateImage failed\n";
        return 1;
    }
    VkMemoryRequirements image_requirements{};
    vkGetImageMemoryRequirements(device, output_image, &image_requirements);
    const uint32_t image_memory_type = find_memory_type(
        memory_properties, image_requirements.memoryTypeBits, 0,
        VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    VkMemoryAllocateInfo image_allocate{};
    image_allocate.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    image_allocate.allocationSize = image_requirements.size;
    image_allocate.memoryTypeIndex = image_memory_type;
    if (image_memory_type == UINT32_MAX ||
        vkAllocateMemory(device, &image_allocate, nullptr, &output_memory) != VK_SUCCESS ||
        vkBindImageMemory(device, output_image, output_memory, 0) != VK_SUCCESS) {
        std::cerr << "output image memory allocation failed\n";
        return 1;
    }
    VkImageViewCreateInfo view_info{};
    view_info.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
    view_info.image = output_image;
    view_info.viewType = VK_IMAGE_VIEW_TYPE_2D;
    view_info.format = VK_FORMAT_A2B10G10R10_UNORM_PACK32;
    view_info.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    view_info.subresourceRange.levelCount = 1;
    view_info.subresourceRange.layerCount = 1;
    result = vkCreateImageView(device, &view_info, nullptr, &output_view);
    if (result != VK_SUCCESS) {
        std::cerr << "vkCreateImageView failed: " << result << '\n';
        return 1;
    }

    shift::xbox::CapturedVulkanDraw draw{};
    if (!read_spirv(argv[1], &draw.vertex_shader_spirv) ||
        !read_spirv(argv[2], &draw.pixel_shader_spirv)) {
        std::cerr << "could not read valid Vulkan 1.1 SPIR-V smoke shaders\n";
        return 1;
    }
    draw.texture_rgba8 = {255, 0, 0, 255};
    draw.vertex_stride_bytes = 0;
    // Mirror the captured retail point path: one AutoIndex point, 4x MSAA,
    // D24S8 with ALWAYS comparisons, a Y-flipped full-screen viewport/scissor,
    // and blending disabled. The synthetic shader keeps this a renderer test.
    draw.index_count = 1;
    draw.auto_index = true;
    draw.topology = shift::xbox::PrimitiveTopology::PointList;
    draw.texture_width = 1;
    draw.texture_height = 1;
    draw.raster.width = 1280;
    draw.raster.height = 720;
    draw.raster.sample_count = 4;
    draw.raster.color_write_mask = 0xFu;
    draw.raster.depth_test_enabled = true;
    draw.raster.depth_write_enabled = true;
    draw.raster.stencil_test_enabled = true;
    draw.raster.depth_control = 0x00008777u;
    draw.raster.viewport_y_flipped = true;
    draw.raster.scissor_x0 = 0;
    draw.raster.scissor_y0 = 0;
    draw.raster.scissor_x1 = 1280;
    draw.raster.scissor_y1 = 720;
    draw.raster.scissor_has_area = true;
    draw.raster.blend_control_0 = 0x00010001u;
    draw.texture_sampling.swizzle = {shift::xbox::TextureComponent::X,
                                     shift::xbox::TextureComponent::Y,
                                     shift::xbox::TextureComponent::Z,
                                     shift::xbox::TextureComponent::W};
    draw.texture_sampling.clamps = {shift::xbox::TextureClamp::ClampToBorder,
                                    shift::xbox::TextureClamp::ClampToBorder,
                                    shift::xbox::TextureClamp::Repeat};
    draw.texture_sampling.mag_filter = shift::xbox::TextureFilter::Linear;
    draw.texture_sampling.min_filter = shift::xbox::TextureFilter::Linear;
    draw.texture_sampling.mip_filter = shift::xbox::TextureFilter::BaseMap;
    draw.texture_sampling.anisotropy = shift::xbox::TextureAnisotropy::Disabled;
    draw.texture_sampling.border_color = shift::xbox::TextureBorderColor::AbgrBlack;

    std::string error;
    std::vector<uint32_t> output_readback;
    const bool submitted = shift::xbox::submit_captured_vulkan_frame(
        physical_device, device, queue, queue_family, output_image, output_view, false,
        64, 64, std::vector<shift::xbox::CapturedVulkanDraw>{std::move(draw)}, &error,
        &output_readback);
    if (!submitted) {
        std::cerr << "captured Vulkan draw submission failed: " << error << '\n';
        return 1;
    }

    bool has_color = false;
    for (const uint32_t pixel : output_readback) {
        if (pixel & 0x3FFFFFFFu) {
            has_color = true;
            break;
        }
    }
    vkDestroyImageView(device, output_view, nullptr);
    vkDestroyImage(device, output_image, nullptr);
    vkFreeMemory(device, output_memory, nullptr);
    vkDestroyDevice(device, nullptr);
    if (messenger) {
        auto destroy_messenger = reinterpret_cast<PFN_vkDestroyDebugUtilsMessengerEXT>(
            vkGetInstanceProcAddr(instance, "vkDestroyDebugUtilsMessengerEXT"));
        if (destroy_messenger) destroy_messenger(instance, messenger, nullptr);
    }
    vkDestroyInstance(instance, nullptr);

    if (!has_color) {
        std::cerr << "Vulkan draw submission produced no non-black pixels\n";
        return 1;
    }
    if (validation_errors != 0) {
        std::cerr << validation_errors << " Vulkan validation errors\n";
        return 1;
    }
    if (output_readback.size() != 64u * 64u) {
        std::cerr << "Vulkan output readback has the wrong pixel count\n";
        return 1;
    }
    std::cout << "synthetic offscreen Vulkan 1.1 AutoIndex point draw and output readback "
              << "passed on "
              << device_properties.deviceName
              << (use_validation ? " with validation enabled\n" : "\n");
    return 0;
}
