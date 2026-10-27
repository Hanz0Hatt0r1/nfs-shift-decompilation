#include "shift_xbox_live_vulkan_renderer.hpp"

#include <vulkan/vulkan.h>

#include <algorithm>
#include <array>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <iterator>
#include <sstream>
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

bool has_device_extension(VkPhysicalDevice physical_device, const char* name) {
    uint32_t count = 0;
    if (vkEnumerateDeviceExtensionProperties(physical_device, nullptr, &count, nullptr) !=
        VK_SUCCESS) {
        return false;
    }
    std::vector<VkExtensionProperties> extensions(count);
    if (vkEnumerateDeviceExtensionProperties(physical_device, nullptr, &count,
                                              extensions.data()) != VK_SUCCESS) {
        return false;
    }
    return std::any_of(extensions.begin(), extensions.end(), [name](const auto& extension) {
        return std::string(extension.extensionName) == name;
    });
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

struct TestColorImage {
    VkImage image = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
    VkImageView view = VK_NULL_HANDLE;
};

bool create_test_color_image(
    VkDevice device,
    const VkPhysicalDeviceMemoryProperties& memory_properties,
    VkFormat format,
    uint32_t width,
    uint32_t height,
    TestColorImage* output) {
    if (!output || !width || !height) return false;
    *output = {};
    VkImageCreateInfo image_info{};
    image_info.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
    image_info.imageType = VK_IMAGE_TYPE_2D;
    image_info.format = format;
    image_info.extent = {width, height, 1};
    image_info.mipLevels = 1;
    image_info.arrayLayers = 1;
    image_info.samples = VK_SAMPLE_COUNT_1_BIT;
    image_info.tiling = VK_IMAGE_TILING_OPTIMAL;
    image_info.usage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT |
                       VK_IMAGE_USAGE_SAMPLED_BIT |
                       VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
    image_info.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    if (vkCreateImage(device, &image_info, nullptr, &output->image) != VK_SUCCESS) {
        return false;
    }
    VkMemoryRequirements requirements{};
    vkGetImageMemoryRequirements(device, output->image, &requirements);
    const uint32_t memory_type = find_memory_type(
        memory_properties, requirements.memoryTypeBits, 0,
        VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    if (memory_type == UINT32_MAX) return false;
    VkMemoryAllocateInfo allocation{};
    allocation.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    allocation.allocationSize = requirements.size;
    allocation.memoryTypeIndex = memory_type;
    if (vkAllocateMemory(device, &allocation, nullptr, &output->memory) != VK_SUCCESS ||
        vkBindImageMemory(device, output->image, output->memory, 0) != VK_SUCCESS) {
        return false;
    }
    VkImageViewCreateInfo view_info{};
    view_info.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
    view_info.image = output->image;
    view_info.viewType = VK_IMAGE_VIEW_TYPE_2D;
    view_info.format = format;
    view_info.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    view_info.subresourceRange.levelCount = 1;
    view_info.subresourceRange.layerCount = 1;
    return vkCreateImageView(device, &view_info, nullptr, &output->view) == VK_SUCCESS;
}

void destroy_test_color_image(VkDevice device, TestColorImage* image) {
    if (!image) return;
    if (image->view) vkDestroyImageView(device, image->view, nullptr);
    if (image->image) vkDestroyImage(device, image->image, nullptr);
    if (image->memory) vkFreeMemory(device, image->memory, nullptr);
    *image = {};
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

bool read_bytes(const char* path, std::vector<uint8_t>* output) {
    std::ifstream file(path, std::ios::binary);
    if (!file || !output) return false;
    output->assign(std::istreambuf_iterator<char>(file),
                   std::istreambuf_iterator<char>());
    return static_cast<bool>(file) || file.eof();
}

}  // namespace

int main(int argc, char** argv) {
    const bool has_copy_destination_shaders =
        argc == 18 || argc == 19 || argc == 27 || argc == 28;
    const bool has_edram_clear_shader = argc == 19 || argc == 24 || argc == 28;
    if (argc != 14 && argc != 18 && argc != 23 && argc != 24 &&
        argc != 19 && argc != 27 && argc != 28) {
        std::cerr << "usage: xbox_live_vulkan_renderer_check vertex.spv fragment.spv "
                     "geometry.spv copy-vertex.spv copy-fragment.spv "
                     "copy-single-fragment.spv window-vertex.spv window-fragment.spv "
                     "black-copy-fragment.spv gamma-encoded-fragment.spv "
                     "gamma-linear-fragment.spv gamma-single-copy-fragment.spv "
                     "gamma-ms-copy-fragment.spv\n";
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
    app.pApplicationName = "SHIFT synthetic Vulkan Copy/Convert smoke";
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
    VkPhysicalDeviceFeatures supported_features{};
    vkGetPhysicalDeviceFeatures(physical_device, &supported_features);
    VkPhysicalDeviceFeatures enabled_features{};
    enabled_features.geometryShader = supported_features.geometryShader;
    enabled_features.samplerAnisotropy = supported_features.samplerAnisotropy;
    std::vector<const char*> depth_resolve_extensions;
    const bool depth_resolve_extensions_supported =
        has_device_extension(physical_device, VK_KHR_CREATE_RENDERPASS_2_EXTENSION_NAME) &&
        has_device_extension(physical_device, VK_KHR_DEPTH_STENCIL_RESOLVE_EXTENSION_NAME);
    if (depth_resolve_extensions_supported) {
        depth_resolve_extensions = {
            VK_KHR_CREATE_RENDERPASS_2_EXTENSION_NAME,
            VK_KHR_DEPTH_STENCIL_RESOLVE_EXTENSION_NAME,
        };
    }
    VkDeviceCreateInfo device_info{};
    device_info.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
    device_info.queueCreateInfoCount = 1;
    device_info.pQueueCreateInfos = &queue_info;
    device_info.enabledExtensionCount =
        static_cast<uint32_t>(depth_resolve_extensions.size());
    device_info.ppEnabledExtensionNames = depth_resolve_extensions.data();
    device_info.pEnabledFeatures = &enabled_features;
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
    image_info.extent = {1280, 720, 1};
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
    std::vector<uint32_t> rectangle_geometry_spirv;
    if (enabled_features.geometryShader &&
        !read_spirv(argv[3], &rectangle_geometry_spirv)) {
        std::cerr << "could not read valid Vulkan 1.1 rectangle-list geometry SPIR-V\n";
        return 1;
    }
    shift::xbox::CapturedVulkanCopy copy{};
    copy.state = {0, 0, shift::xbox::CapturedCopyCommand::Convert,
                  0x0975E000u, 1280, 720, 6, true};
    if (!read_spirv(argv[4], &copy.vertex_shader_spirv) ||
        !read_spirv(argv[5], &copy.pixel_shader_spirv) ||
        !read_spirv(argv[6], &copy.single_sample_pixel_shader_spirv)) {
        std::cerr << "could not read valid Vulkan 1.1 sample-zero Copy/Convert shaders\n";
        return 1;
    }
    draw.pixel_shader_spirv_linear_target = draw.pixel_shader_spirv;
    std::vector<uint32_t> black_copy_fragment_spirv;
    if (!read_spirv(argv[9], &black_copy_fragment_spirv)) {
        std::cerr << "could not read valid Vulkan 1.1 black Copy/Convert shader\n";
        return 1;
    }
    std::vector<uint32_t> gamma_encoded_fragment_spirv;
    std::vector<uint32_t> gamma_linear_fragment_spirv;
    std::vector<uint32_t> gamma_copy_single_fragment_spirv;
    std::vector<uint32_t> gamma_copy_ms_fragment_spirv;
    if (!read_spirv(argv[10], &gamma_encoded_fragment_spirv) ||
        !read_spirv(argv[11], &gamma_linear_fragment_spirv) ||
        !read_spirv(argv[12], &gamma_copy_single_fragment_spirv) ||
        !read_spirv(argv[13], &gamma_copy_ms_fragment_spirv)) {
        std::cerr << "could not read Vulkan 1.1 gamma target regression shaders\n";
        return 1;
    }
    std::vector<uint32_t> disclaimer_vertex_spirv;
    std::vector<uint32_t> disclaimer_encoded_fragment_spirv;
    std::vector<uint32_t> disclaimer_linear_fragment_spirv;
    if ((argc == 24 || argc == 28) &&
        (!read_spirv(argv[14], &disclaimer_vertex_spirv) ||
         !read_spirv(argv[15], &disclaimer_encoded_fragment_spirv) ||
         !read_spirv(argv[16], &disclaimer_linear_fragment_spirv))) {
        std::cerr << "could not read captured disclaimer Vulkan 1.1 shaders\n";
        return 1;
    }
    std::vector<uint32_t> copy_4x_u16x4_spirv;
    std::vector<uint32_t> copy_sample0_rg16f_ms_spirv;
    std::vector<uint32_t> copy_sample0_rg16f_single_spirv;
    std::vector<uint32_t> copy_constant_fragment_spirv;
    std::vector<uint32_t> edram_clear_fragment_spirv;
    if (has_copy_destination_shaders) {
        const int first_copy_destination_shader =
            (argc == 27 || argc == 28) ? 23 : 14;
        if (!read_spirv(argv[first_copy_destination_shader],
                        &copy_4x_u16x4_spirv) ||
            !read_spirv(argv[first_copy_destination_shader + 1],
                        &copy_sample0_rg16f_ms_spirv) ||
            !read_spirv(argv[first_copy_destination_shader + 2],
                        &copy_sample0_rg16f_single_spirv) ||
            !read_spirv(argv[first_copy_destination_shader + 3],
                        &copy_constant_fragment_spirv) ||
            (has_edram_clear_shader &&
             !read_spirv(argv[argc - 1], &edram_clear_fragment_spirv))) {
            std::cerr << "could not read Vulkan 1.1 intermediate Copy/Convert shaders\n";
            return 1;
        }
    }
    std::vector<uint32_t> window_vertex_spirv;
    std::vector<uint32_t> window_fragment_spirv;
    if (!read_spirv(argv[7], &window_vertex_spirv) ||
        !read_spirv(argv[8], &window_fragment_spirv)) {
        std::cerr << "could not read clip-disabled window-coordinate SPIR-V shaders\n";
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
    draw.raster.surface_pitch = 1280;
    draw.raster.sample_count = 4;
    draw.raster.color_base_tiles = 13;
    draw.raster.depth_base_tiles = 29;
    draw.raster.color_format = shift::xbox::CapturedColorTargetFormat::Rgba8Gamma;
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
    draw.textures = {
        {0, draw.texture_sampling, 1, 1,
         shift::xbox::CapturedVulkanTexture::Format::R8, {255}},
        {1, draw.texture_sampling, 1, 1,
         shift::xbox::CapturedVulkanTexture::Format::Rgba8,
         {0, 255, 0, 255}},
    };

    shift::xbox::CapturedVulkanDraw operation_copy_geometry = draw;
    operation_copy_geometry.vertex_shader_spirv = window_vertex_spirv;
    operation_copy_geometry.geometry_shader_spirv = rectangle_geometry_spirv;
    operation_copy_geometry.pixel_shader_spirv = window_fragment_spirv;
    operation_copy_geometry.topology =
        shift::xbox::PrimitiveTopology::RectangleList;
    operation_copy_geometry.index_count = 3;
    operation_copy_geometry.auto_index = false;
    operation_copy_geometry.indices = {0, 0, 1, 0, 2, 0};
    operation_copy_geometry.vertex_stride_bytes = 0;
    operation_copy_geometry.vertices.clear();
    operation_copy_geometry.vertex_input_attributes.clear();
    operation_copy_geometry.raster.sample_count = 1;
    operation_copy_geometry.raster.color_format =
        shift::xbox::CapturedColorTargetFormat::Rgba8Linear;
    operation_copy_geometry.raster.depth_test_enabled = false;
    operation_copy_geometry.raster.depth_write_enabled = false;
    operation_copy_geometry.raster.stencil_test_enabled = false;
    operation_copy_geometry.raster.depth_control = 0;
    operation_copy_geometry.raster.viewport_y_flipped = true;
    operation_copy_geometry.raster.clip_disabled_window_coordinates = true;
    operation_copy_geometry.raster.blend_control_0 = 0x00010001u;

    std::vector<shift::xbox::CapturedVulkanDraw> draws;
    draws.push_back(draw);
    auto captured_alpha_blend = draw;
    captured_alpha_blend.raster.color_format =
        shift::xbox::CapturedColorTargetFormat::Rgba8Linear;
    captured_alpha_blend.raster.blend_control_0 = 0x07060706u;
    captured_alpha_blend.textures[0].pixels = {255};
    captured_alpha_blend.textures[1].pixels = {0, 255, 0, 255};
    draws.push_back(std::move(captured_alpha_blend));
    if (!rectangle_geometry_spirv.empty()) {
        auto rectangle = draw;
        rectangle.topology = shift::xbox::PrimitiveTopology::RectangleList;
        rectangle.index_count = 3;
        rectangle.geometry_shader_spirv = rectangle_geometry_spirv;
        draws.push_back(std::move(rectangle));
    }

    std::string error;
    std::vector<uint32_t> output_readback;
    shift::xbox::CapturedVulkanTextureCache texture_cache;
    VkPipelineCache pipeline_cache = VK_NULL_HANDLE;
    VkPipelineCacheCreateInfo pipeline_cache_info{};
    pipeline_cache_info.sType = VK_STRUCTURE_TYPE_PIPELINE_CACHE_CREATE_INFO;
    result = vkCreatePipelineCache(device, &pipeline_cache_info, nullptr,
                                   &pipeline_cache);
    if (result != VK_SUCCESS) {
        std::cerr << "vkCreatePipelineCache failed: " << result << '\n';
        return 1;
    }
    const bool submitted = shift::xbox::submit_captured_vulkan_frame(
        physical_device, device, queue, queue_family, output_image, output_view,
        false, 1280, 720, draws, &error, &output_readback,
        enabled_features.geometryShader, &copy, false, {}, pipeline_cache,
        &texture_cache);
    if (!submitted) {
      std::cerr << "captured Vulkan draw submission failed: " << error << '\n';
      return 1;
    }

    // These are synthetic Copy/Convert primitive checks. They exercise the
    // destination attachment formats and the captured sample-select modes;
    // they are not evidence that the retail transition packet is complete.
    auto format26_source = draw;
    format26_source.raster.color_format =
        shift::xbox::CapturedColorTargetFormat::Rgb10A2Float;
    format26_source.raster.guest_color_format = 12;
    format26_source.vertex_shader_spirv = copy.vertex_shader_spirv;
    format26_source.pixel_shader_spirv = copy_constant_fragment_spirv;
    format26_source.topology = shift::xbox::PrimitiveTopology::TriangleList;
    format26_source.index_count = 3;
    format26_source.auto_index = true;
    format26_source.vertex_stride_bytes = 0;
    format26_source.vertices.clear();
    format26_source.vertex_input_attributes.clear();
    format26_source.raster.depth_test_enabled = false;
    format26_source.raster.depth_write_enabled = false;
    format26_source.raster.stencil_test_enabled = false;
    format26_source.raster.depth_control = 0;
    std::vector<shift::xbox::CapturedVulkanDraw> format26_source_draws{
        format26_source};
    auto format31_source = draw;
    format31_source.raster.color_format =
        shift::xbox::CapturedColorTargetFormat::Rgb10A2Float;
    format31_source.raster.guest_color_format = 12;
    format31_source.raster.sample_count = 1;
    format31_source.vertex_shader_spirv = copy.vertex_shader_spirv;
    format31_source.pixel_shader_spirv = copy_constant_fragment_spirv;
    format31_source.topology = shift::xbox::PrimitiveTopology::TriangleList;
    format31_source.index_count = 3;
    format31_source.auto_index = true;
    format31_source.vertex_stride_bytes = 0;
    format31_source.vertices.clear();
    format31_source.vertex_input_attributes.clear();
    format31_source.raster.depth_test_enabled = false;
    format31_source.raster.depth_write_enabled = false;
    format31_source.raster.stencil_test_enabled = false;
    format31_source.raster.depth_control = 0;
    std::vector<shift::xbox::CapturedVulkanDraw> format31_source_draws{
        format31_source};
    auto format31_ms_source = format31_source;
    format31_ms_source.raster.sample_count = 4;
    std::vector<shift::xbox::CapturedVulkanDraw> format31_ms_source_draws{
        format31_ms_source};
    shift::xbox::CapturedVulkanTextureCache guest_copy_cache;
    const auto exercise_intermediate_copy = [&](uint32_t destination_format,
                                                VkFormat vk_format,
                                                uint32_t destination_width,
                                                uint32_t destination_height,
                                                const std::vector<
                                                    shift::xbox::CapturedVulkanDraw>&
                                                    source_draws,
                                                const std::vector<uint32_t>&
                                                    multisample_shader,
                                                const std::vector<uint32_t>&
                                                    single_sample_shader) {
      VkFormatProperties format_properties{};
      vkGetPhysicalDeviceFormatProperties(physical_device, vk_format,
                                          &format_properties);
      constexpr VkFormatFeatureFlags required_features =
          VK_FORMAT_FEATURE_COLOR_ATTACHMENT_BIT |
          VK_FORMAT_FEATURE_SAMPLED_IMAGE_BIT |
          VK_FORMAT_FEATURE_TRANSFER_SRC_BIT;
      if ((format_properties.optimalTilingFeatures & required_features) !=
          required_features) {
        std::cerr << "SKIP intermediate Copy/Convert format "
                  << destination_format << ": Vulkan device lacks required format features\n";
        return true;
      }
      TestColorImage target{};
      if (!create_test_color_image(device, memory_properties,
                                   vk_format, destination_width,
                                   destination_height, &target)) {
        destroy_test_color_image(device, &target);
        error = "could not create synthetic intermediate Copy/Convert target";
        return false;
      }
      auto intermediate_copy = copy;
      intermediate_copy.state.destination_format = destination_format;
      intermediate_copy.state.destination_pitch = destination_width;
      intermediate_copy.state.destination_height = destination_height;
      intermediate_copy.state.destination_swap_red_blue = false;
      intermediate_copy.state.source_gamma = false;
      intermediate_copy.state.destination_base = 0x0CC87000u;
      intermediate_copy.state.destination_number_format =
          destination_format == 26 ? 2u : 7u;
      intermediate_copy.state.destination_endian =
          destination_format == 26 ? 1u : 2u;
      intermediate_copy.state.destination_exp_bias =
          destination_format == 26 ? 11 : 0;
      intermediate_copy.state.sample_select = destination_format == 26 ? 6u : 0u;
      intermediate_copy.state.color_clear_enable = true;
      intermediate_copy.state.depth_clear_enable = destination_format == 26;
      intermediate_copy.color_clear = 0;
      intermediate_copy.color_clear_lo = 0;
      intermediate_copy.depth_clear = 0xFFFFFF00u;
      intermediate_copy.clear_values_ready = true;
      intermediate_copy.source_geometry_ready = true;
      intermediate_copy.source_geometry = operation_copy_geometry;
      intermediate_copy.edram_clear_pixel_shader_spirv =
          edram_clear_fragment_spirv;
      intermediate_copy.source_width = source_draws.front().raster.width;
      intermediate_copy.source_height = source_draws.front().raster.height;
      intermediate_copy.pixel_shader_spirv = multisample_shader;
      intermediate_copy.single_sample_pixel_shader_spirv = single_sample_shader;
      std::vector<uint32_t> converted;
      const bool converted_ok = shift::xbox::submit_captured_vulkan_frame(
          physical_device, device, queue, queue_family, target.image, target.view,
          false, destination_width, destination_height, source_draws, &error,
          &converted, enabled_features.geometryShader, &intermediate_copy,
          false, {}, pipeline_cache,
          &guest_copy_cache);
      bool payload_ok = converted_ok && !converted.empty();
      if (payload_ok && destination_format == 26) {
        const auto* components =
            reinterpret_cast<const uint16_t*>(converted.data());
        const size_t component_count = converted.size() * 2;
        payload_ok = component_count ==
                     static_cast<size_t>(destination_width) *
                         destination_height * 4;
        for (size_t i = 0; payload_ok && i < component_count; i += 4) {
          payload_ok = components[i] == 1024 &&
                       components[i + 1] == 512 &&
                       components[i + 2] == 256 &&
                       components[i + 3] == 2048;
        }
      } else if (payload_ok) {
        payload_ok = converted.size() ==
                         static_cast<size_t>(destination_width) *
                             destination_height &&
                     std::all_of(converted.begin(), converted.end(),
                                 [](uint32_t texel) {
                                   return texel == 0x34003800u;
                                 });
      }
      const size_t expected_cached_layouts = destination_format == 26 ? 1u : 2u;
      payload_ok = payload_ok &&
          guest_copy_cache.cached_guest_copy_image_count() ==
              expected_cached_layouts;
      if (payload_ok) {
        std::vector<uint32_t> reused_output;
        const bool reused_ok = shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, target.image,
            target.view, false, destination_width, destination_height,
            source_draws, &error, &reused_output,
            enabled_features.geometryShader, &intermediate_copy,
            false, {}, pipeline_cache, &guest_copy_cache);
        payload_ok = reused_ok && reused_output == converted &&
            guest_copy_cache.cached_guest_copy_image_count() ==
                expected_cached_layouts;
        if (!reused_ok) {
          error = "cached guest Copy/Convert image reuse failed: " + error;
        } else if (reused_output != converted) {
          std::ostringstream detail;
          detail << "cached Copy/Convert output changed across identical submissions; first sizes="
                 << converted.size() << '/' << reused_output.size();
          if (!converted.empty() && !reused_output.empty()) {
            detail << " first texel=0x" << std::hex << converted.front()
                   << "/0x" << reused_output.front();
          }
          error = detail.str();
        }
      }
      destroy_test_color_image(device, &target);
      if (!payload_ok) {
        if (converted_ok && error.empty()) {
          std::ostringstream detail;
          detail << "format " << destination_format
                 << " readback size " << converted.size()
                 << " had an unexpected extent or empty payload";
          detail << ", cached copy images="
                 << guest_copy_cache.cached_guest_copy_image_count()
                 << ", expected="
                 << (destination_format == 26 ? 1u : 2u);
          if (destination_format == 26 && !converted.empty()) {
            const auto* components =
                reinterpret_cast<const uint16_t*>(converted.data());
            const size_t component_count = converted.size() * 2;
            for (size_t i = 0; i + 3 < component_count; i += 4) {
              if (components[i] != 1024 || components[i + 1] != 512 ||
                  components[i + 2] != 256 || components[i + 3] != 2048) {
                detail << ", first mismatch at texel " << (i / 4)
                       << " components=" << components[i] << ','
                       << components[i + 1] << ',' << components[i + 2]
                       << ',' << components[i + 3];
                break;
              }
            }
            uint16_t max_alpha = 0;
            for (size_t i = 3; i < component_count; i += 4) {
              max_alpha = std::max(max_alpha, components[i]);
            }
            detail << ", max alpha=" << max_alpha;
          }
          error = detail.str();
        }
        return false;
      }
      return true;
    };
    if (has_edram_clear_shader && has_copy_destination_shaders &&
        enabled_features.geometryShader &&
        (!exercise_intermediate_copy(
             26, VK_FORMAT_R16G16B16A16_UINT, 1280, 720,
             format26_source_draws, copy_4x_u16x4_spirv, {}) ||
         !exercise_intermediate_copy(
             31, VK_FORMAT_R16G16_SFLOAT, 256, 243,
             format31_source_draws, copy_sample0_rg16f_ms_spirv,
             copy_sample0_rg16f_single_spirv) ||
         !exercise_intermediate_copy(
             31, VK_FORMAT_R16G16_SFLOAT, 256, 243,
             format31_ms_source_draws, copy_sample0_rg16f_ms_spirv,
             copy_sample0_rg16f_single_spirv))) {
      std::cerr << "synthetic intermediate Copy/Convert primitive failed: "
                << error << '\n';
      return 1;
    }
    if (has_edram_clear_shader && has_copy_destination_shaders &&
        enabled_features.geometryShader) {
      shift::xbox::CapturedVulkanCopy operation_copy = copy;
      operation_copy.source_geometry_ready = true;
      operation_copy.source_geometry = operation_copy_geometry;
      shift::xbox::CapturedVulkanCopy intermediate_copy = operation_copy;
      intermediate_copy.state.destination_base = 0x0CC87000u;
      intermediate_copy.state.destination_pitch = 256;
      intermediate_copy.state.destination_height = 243;
      intermediate_copy.state.destination_format = 31;
      intermediate_copy.state.destination_swap_red_blue = false;
      intermediate_copy.state.destination_number_format = 7;
      intermediate_copy.state.destination_endian = 2;
      intermediate_copy.state.destination_exp_bias = 0;
      intermediate_copy.state.sample_select = 0;
      intermediate_copy.state.color_clear_enable = true;
      intermediate_copy.state.depth_clear_enable = false;
      intermediate_copy.color_clear = 0;
      intermediate_copy.color_clear_lo = 0;
      intermediate_copy.depth_clear = 0xFFFFFF00u;
      intermediate_copy.clear_values_ready = true;
      intermediate_copy.edram_clear_pixel_shader_spirv =
          edram_clear_fragment_spirv;
      intermediate_copy.source_width = 1280;
      intermediate_copy.source_height = 720;
      intermediate_copy.pixel_shader_spirv =
          copy_sample0_rg16f_ms_spirv;
      intermediate_copy.single_sample_pixel_shader_spirv =
          copy_sample0_rg16f_single_spirv;
      shift::xbox::CapturedVulkanOperation draw0{};
      draw0.type = shift::xbox::CapturedVulkanOperation::Type::Draw;
      draw0.draw_index = 0;
      draw0.packet_index = 200;
      shift::xbox::CapturedVulkanOperation copy0{};
      copy0.type = shift::xbox::CapturedVulkanOperation::Type::CopyConvert;
      copy0.packet_index = 201;
      copy0.source_width = 1280;
      copy0.source_height = 720;
      copy0.copy_state = intermediate_copy.state;
      copy0.copy = intermediate_copy;
      copy0.copy_shaders_ready = true;
      auto cache_sample_draw = format31_source;
      cache_sample_draw.vertex_shader_spirv = draw.vertex_shader_spirv;
      cache_sample_draw.pixel_shader_spirv = draw.pixel_shader_spirv;
      shift::xbox::CapturedVulkanTexture copied_format31{};
      copied_format31.fetch_constant_index = 0;
      copied_format31.guest_address = 0x0CC87000u;
      copied_format31.guest_format = 31;
      copied_format31.guest_endian = 2;
      copied_format31.guest_pitch = 256;
      copied_format31.width = 256;
      copied_format31.height = 243;
      copied_format31.format =
          shift::xbox::CapturedVulkanTexture::Format::Rg16Float;
      copied_format31.guest_copy_source = true;
      copied_format31.pixels = {0x00, 0x3C, 0x00, 0x3C};  // deliberately stale
      copied_format31.sampling = draw.texture_sampling;
      auto black_detail = draw.textures[1];
      black_detail.pixels = {0, 0, 0, 0};
      cache_sample_draw.textures = {copied_format31, black_detail};
      shift::xbox::CapturedVulkanOperation draw1 = draw0;
      draw1.draw_index = 1;
      draw1.packet_index = 202;
      shift::xbox::CapturedVulkanOperation copy1{};
      copy1.type = shift::xbox::CapturedVulkanOperation::Type::CopyConvert;
      copy1.packet_index = 203;
      copy1.source_width = 1280;
      copy1.source_height = 720;
      copy1.copy_state = copy.state;
      copy1.copy = operation_copy;
      copy1.copy_shaders_ready = true;
      std::vector<uint32_t> ordered_readback;
      shift::xbox::CapturedVulkanTextureCache ordered_copy_cache;
      std::string ordered_submit_error;
      if (!shift::xbox::submit_captured_vulkan_operation_stream(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720,
              {format31_source, cache_sample_draw},
              {draw0, copy0, draw1, copy1}, &ordered_submit_error,
              &ordered_readback, enabled_features.geometryShader, &copy,
              false, {}, pipeline_cache, &ordered_copy_cache) ||
          ordered_copy_cache.cached_guest_copy_image_count() != 1u ||
          ordered_readback.size() != 1280u * 720u ||
          std::none_of(ordered_readback.begin(), ordered_readback.end(),
                       [](uint32_t pixel) {
                           return (pixel & 0x3FFFFFFFu) != 0;
                       })) {
        std::cerr << "ordered Draw/Copy/Draw/Copy Vulkan submissions failed: "
                  << ordered_submit_error << '\n';
        return 1;
      }

      // Synthetic regression: independent cached Vulkan images may serve
      // sequential stages only when their complete Xenos tile footprints do
      // not overlap. This is not retail transition parity evidence.
      auto disjoint_target_draw = cache_sample_draw;
      disjoint_target_draw.raster.width = 80;
      disjoint_target_draw.raster.height = 16;
      disjoint_target_draw.raster.surface_pitch = 80;
      disjoint_target_draw.raster.color_base_tiles = 800;
      disjoint_target_draw.raster.depth_base_tiles = 900;
      disjoint_target_draw.raster.viewport_x = 0.0f;
      disjoint_target_draw.raster.viewport_y = 0.0f;
      disjoint_target_draw.raster.viewport_width = 80.0f;
      disjoint_target_draw.raster.viewport_height = 16.0f;
      disjoint_target_draw.raster.scissor_x0 = 0;
      disjoint_target_draw.raster.scissor_y0 = 0;
      disjoint_target_draw.raster.scissor_x1 = 80;
      disjoint_target_draw.raster.scissor_y1 = 16;
      auto disjoint_draw_operation = draw1;
      disjoint_draw_operation.packet_index = 204;
      auto disjoint_copy_operation = copy1;
      disjoint_copy_operation.packet_index = 205;
      disjoint_copy_operation.source_width = 80;
      disjoint_copy_operation.source_height = 16;
      std::vector<uint32_t> disjoint_layout_readback;
      shift::xbox::CapturedVulkanTextureCache disjoint_layout_cache;
      if (!shift::xbox::submit_captured_vulkan_operation_stream(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720,
              {format31_source, disjoint_target_draw},
              {draw0, copy0, disjoint_draw_operation,
               disjoint_copy_operation},
              &ordered_submit_error, &disjoint_layout_readback,
              enabled_features.geometryShader, &copy, false, {},
              pipeline_cache, &disjoint_layout_cache) ||
          disjoint_layout_cache.cached_guest_edram_target_count() != 2u ||
          disjoint_layout_readback.size() != 1280u * 720u) {
        std::cerr << "ordered Vulkan stream rejected or lost disjoint target layouts: "
                  << ordered_submit_error << '\n';
        return 1;
      }
      disjoint_layout_cache.clear();

      auto disjoint_copy = operation_copy;
      disjoint_copy.source_width = 80;
      disjoint_copy.source_height = 16;
      auto disjoint_stage_target_draw = disjoint_target_draw;
      for (auto& texture : disjoint_stage_target_draw.textures) {
        if (!texture.guest_copy_source) continue;
        texture.guest_copy_source = false;
        texture.pixels.resize(
            static_cast<size_t>(texture.width) * texture.height * 4u);
      }
      std::vector<uint32_t> disjoint_direct_readback;
      if (!shift::xbox::submit_captured_vulkan_frame(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720, {disjoint_stage_target_draw},
              &ordered_submit_error, &disjoint_direct_readback,
              enabled_features.geometryShader, &disjoint_copy, false, {},
              pipeline_cache)) {
        std::cerr << "direct disjoint-layout Copy/Convert baseline failed: "
                  << ordered_submit_error << '\n';
        return 1;
      }
      std::vector<uint32_t> disjoint_single_stage_readback;
      shift::xbox::CapturedVulkanTextureCache disjoint_single_stage_cache;
      if (!shift::xbox::submit_captured_vulkan_operation_stream(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720,
              {format31_source, disjoint_stage_target_draw},
              {draw0, disjoint_draw_operation, disjoint_copy_operation},
              &ordered_submit_error, &disjoint_single_stage_readback,
              enabled_features.geometryShader, &copy, false, {},
              pipeline_cache, &disjoint_single_stage_cache) ||
          disjoint_single_stage_cache.cached_guest_edram_target_count() != 2u ||
          disjoint_single_stage_readback != disjoint_direct_readback) {
        std::cerr << "ordered executor failed to persist a disjoint layout switch inside one Draw segment: "
                  << ordered_submit_error << '\n';
        return 1;
      }
      disjoint_single_stage_cache.clear();

      auto aliased_target_draw = disjoint_target_draw;
      aliased_target_draw.raster.color_base_tiles =
          format31_source.raster.color_base_tiles;
      aliased_target_draw.raster.depth_base_tiles =
          format31_source.raster.depth_base_tiles;
      aliased_target_draw.raster.guest_color_format =
          format31_source.raster.guest_color_format + 1u;
      shift::xbox::CapturedVulkanTextureCache aliased_layout_cache;
      const bool aliased_layout_rejected =
          !shift::xbox::submit_captured_vulkan_operation_stream(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720,
              {format31_source, aliased_target_draw},
              {draw0, copy0, disjoint_draw_operation,
               disjoint_copy_operation},
              &ordered_submit_error, nullptr,
              enabled_features.geometryShader, &copy, false, {},
              pipeline_cache, &aliased_layout_cache) &&
          ordered_submit_error.find("aliases a cached layout") !=
              std::string::npos;
      if (!aliased_layout_rejected) {
        std::cerr << "ordered Vulkan stream did not reject aliased target layouts: "
                  << ordered_submit_error << '\n';
        return 1;
      }
      aliased_layout_cache.clear();

      auto uploaded_reference = cache_sample_draw;
      uploaded_reference.textures[0].guest_copy_source = false;
      uploaded_reference.textures[0].pixels.resize(256u * 243u * 4u);
      for (size_t offset = 0;
           offset < uploaded_reference.textures[0].pixels.size(); offset += 4) {
        uploaded_reference.textures[0].pixels[offset + 0] = 0x00;
        uploaded_reference.textures[0].pixels[offset + 1] = 0x38;
        uploaded_reference.textures[0].pixels[offset + 2] = 0x00;
        uploaded_reference.textures[0].pixels[offset + 3] = 0x34;
      }
      std::vector<uint32_t> uploaded_reference_readback;
      shift::xbox::CapturedVulkanTextureCache uploaded_reference_cache;
      if (!shift::xbox::submit_captured_vulkan_operation_stream(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720,
              {format31_source, uploaded_reference},
              {draw0, copy0, draw1, copy1}, &ordered_submit_error,
              &uploaded_reference_readback, enabled_features.geometryShader,
              &copy, false, {}, pipeline_cache, &uploaded_reference_cache) ||
          ordered_readback != uploaded_reference_readback) {
        std::cerr << "format-31 Copy/Convert cache image did not sample like its exact R16G16_FLOAT payload: "
                  << ordered_submit_error << '\n';
        return 1;
      }
      uploaded_reference_cache.clear();
      if (ordered_copy_cache.cached_guest_edram_target_count() != 1u) {
        std::cerr << "ordered Copy/Convert did not retain its guest EDRAM color target\n";
        return 1;
      }

      std::vector<uint32_t> one_draw_baseline;
      if (!shift::xbox::submit_captured_vulkan_frame(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720, {format31_source},
              &ordered_submit_error, &one_draw_baseline, false, &copy)) {
        std::cerr << "single-draw baseline for EDRAM persistence failed: "
                  << ordered_submit_error << '\n';
        return 1;
      }
      shift::xbox::CapturedVulkanOperation seed_draw = draw0;
      seed_draw.packet_index = 300;
      shift::xbox::CapturedVulkanOperation seed_copy{};
      seed_copy.type =
          shift::xbox::CapturedVulkanOperation::Type::CopyConvert;
      seed_copy.packet_index = 301;
      seed_copy.source_width = 1280;
      seed_copy.source_height = 720;
      seed_copy.copy_state = operation_copy.state;
      seed_copy.copy = operation_copy;
      seed_copy.copy_shaders_ready = true;
      std::string edram_seed_error;
      shift::xbox::CapturedVulkanTextureCache persistent_edram_cache;
      if (!shift::xbox::submit_captured_vulkan_operation_stream(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720, {format31_source},
              {seed_draw, seed_copy}, &edram_seed_error, nullptr,
              enabled_features.geometryShader, &copy, false, {},
              pipeline_cache, &persistent_edram_cache) ||
          persistent_edram_cache.cached_guest_edram_target_count() != 1u) {
        std::cerr << "could not seed a persistent Xenos EDRAM target: "
                  << edram_seed_error << '\n';
        return 1;
      }
      shift::xbox::CapturedVulkanOperation present_copy{};
      present_copy.type =
          shift::xbox::CapturedVulkanOperation::Type::CopyConvert;
      present_copy.packet_index = 303;
      present_copy.source_width = 1280;
      present_copy.source_height = 720;
      present_copy.copy_state = operation_copy.state;
      present_copy.copy = operation_copy;
      present_copy.copy_shaders_ready = true;
      present_copy.source_raster_ready = true;
      present_copy.source_raster = format31_source.raster;
      std::vector<uint32_t> persisted_edram_readback;
      std::string edram_preserve_error;
      if (!shift::xbox::submit_captured_vulkan_operation_stream(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720, {}, {present_copy},
              &edram_preserve_error,
              &persisted_edram_readback, enabled_features.geometryShader,
              &copy, false, {}, pipeline_cache, &persistent_edram_cache) ||
          persisted_edram_readback != one_draw_baseline ||
          persistent_edram_cache.cached_guest_edram_target_count() != 1u) {
        std::cerr << "cached-source Copy/Convert did not preserve the previous Xenos EDRAM color target: "
                  << edram_preserve_error << '\n';
        return 1;
      }
      shift::xbox::CapturedVulkanOperation clear_cached_source{};
      clear_cached_source.type =
          shift::xbox::CapturedVulkanOperation::Type::CopyConvert;
      clear_cached_source.packet_index = 304;
      clear_cached_source.source_width = 1280;
      clear_cached_source.source_height = 720;
      clear_cached_source.source_raster_ready = true;
      clear_cached_source.source_raster = format31_source.raster;
      clear_cached_source.copy_state = intermediate_copy.state;
      clear_cached_source.copy = intermediate_copy;
      clear_cached_source.copy_shaders_ready = true;
      auto present_after_clear = present_copy;
      present_after_clear.packet_index = 305;
      std::vector<uint32_t> cleared_edram_readback;
      std::string edram_clear_error;
      if (!shift::xbox::submit_captured_vulkan_operation_stream(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720, {},
              {clear_cached_source, present_after_clear}, &edram_clear_error,
              &cleared_edram_readback, enabled_features.geometryShader,
              &operation_copy, false, {}, pipeline_cache,
              &persistent_edram_cache) ||
          cleared_edram_readback.size() != 1280u * 720u ||
          !std::all_of(cleared_edram_readback.begin(),
                       cleared_edram_readback.end(),
                       [](uint32_t texel) { return texel == 0; })) {
        std::cerr << "captured Copy/Convert zero clear did not update the exact cached Xenos EDRAM target before the following presenter copy: "
                  << edram_clear_error << '\n';
        return 1;
      }
      persistent_edram_cache.clear();

      auto copy_without_geometry = copy0;
      copy_without_geometry.copy.source_geometry_ready = false;
      std::string missing_geometry_error;
      if (shift::xbox::submit_captured_vulkan_operation_stream(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720, {format31_source},
              {draw0, copy_without_geometry}, &missing_geometry_error,
              nullptr, enabled_features.geometryShader, &copy, false, {},
              pipeline_cache, nullptr) ||
          missing_geometry_error.find(
              "ordered replay refuses a fullscreen substitute") ==
              std::string::npos) {
        std::cerr << "ordered executor accepted Copy/Convert without captured PM4 geometry: "
                  << missing_geometry_error << '\n';
        return 1;
      }

      auto mismatched_copy_source = copy0;
      mismatched_copy_source.packet_index = 202;
      mismatched_copy_source.source_raster_ready = true;
      mismatched_copy_source.source_raster = format31_source.raster;
      ++mismatched_copy_source.source_raster.color_base_tiles;
      std::string mismatched_layout_error;
      if (shift::xbox::submit_captured_vulkan_operation_stream(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720, {format31_source},
              {draw0, mismatched_copy_source}, &mismatched_layout_error,
              nullptr, enabled_features.geometryShader, &copy, false, {},
              pipeline_cache, nullptr) ||
          mismatched_layout_error.find(
              "Copy/Convert packet 202 reinterprets the active draw segment") ==
              std::string::npos ||
          mismatched_layout_error.find("active draw={color_base=0x") ==
              std::string::npos ||
          mismatched_layout_error.find(", copy source={color_base=0x") ==
              std::string::npos) {
        std::cerr << "Copy/Convert EDRAM mismatch diagnostic omitted its source layouts: "
                  << mismatched_layout_error << '\n';
        return 1;
      }

      auto layout_change_draw = draw0;
      layout_change_draw.packet_index = 201;
      layout_change_draw.draw_index = 1;
      auto layout_change_copy = copy0;
      layout_change_copy.packet_index = 202;
      auto layout_change_source = format31_source;
      ++layout_change_source.raster.color_base_tiles;
      std::string layout_change_error;
      if (shift::xbox::submit_captured_vulkan_operation_stream(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720,
              {format31_source, layout_change_source},
              {draw0, layout_change_draw, layout_change_copy},
              &layout_change_error,
              nullptr, enabled_features.geometryShader, &copy, false, {},
              pipeline_cache, nullptr) ||
          layout_change_error.find("draw packet 201 changes target layout before a "
                                   "Copy/Convert boundary") == std::string::npos ||
          layout_change_error.find("prior draw packet 200 layout={color_base=0x") ==
              std::string::npos ||
          layout_change_error.find(", next layout={color_base=0x") ==
              std::string::npos) {
        std::cerr << "ordered EDRAM layout-change diagnostic omitted both draw layouts: "
                  << layout_change_error << '\n';
        return 1;
      }

      auto packet49_draw = draw;
      packet49_draw.topology = shift::xbox::PrimitiveTopology::TriangleList;
      packet49_draw.index_count = 3;
      packet49_draw.pixel_shader_spirv = gamma_encoded_fragment_spirv;
      packet49_draw.pixel_shader_spirv_linear_target =
          gamma_linear_fragment_spirv;
      packet49_draw.raster.color_base_tiles = 0;
      packet49_draw.raster.depth_base_tiles = 0x2d0;
      packet49_draw.raster.surface_pitch = 640;
      packet49_draw.raster.sample_count = 4;
      packet49_draw.raster.color_format =
          shift::xbox::CapturedColorTargetFormat::Rgba8Gamma;
      packet49_draw.raster.guest_color_format = 1;
      packet49_draw.raster.depth_test_enabled = false;
      packet49_draw.raster.depth_write_enabled = false;
      packet49_draw.raster.stencil_test_enabled = false;
      packet49_draw.raster.depth_control = 0;
      auto packet49_source = packet49_draw.raster;
      packet49_source.color_format =
          shift::xbox::CapturedColorTargetFormat::Rgba8Linear;
      packet49_source.sample_count = 1;
      packet49_source.surface_pitch = 1280;
      packet49_source.guest_color_format = 0;
      auto packet49_copy = copy;
      packet49_copy.source_gamma = false;
      packet49_copy.source_geometry_ready = true;
      packet49_copy.source_geometry = operation_copy_geometry;
      packet49_copy.source_geometry.raster = packet49_source;
      shift::xbox::CapturedVulkanOperation packet49_draw_operation{};
      packet49_draw_operation.type =
          shift::xbox::CapturedVulkanOperation::Type::Draw;
      packet49_draw_operation.packet_index = 24;
      packet49_draw_operation.draw_index = 0;
      shift::xbox::CapturedVulkanOperation packet49_copy_operation{};
      packet49_copy_operation.type =
          shift::xbox::CapturedVulkanOperation::Type::CopyConvert;
      packet49_copy_operation.packet_index = 49;
      packet49_copy_operation.source_width = 1280;
      packet49_copy_operation.source_height = 720;
      packet49_copy_operation.source_raster_ready = true;
      packet49_copy_operation.source_raster = packet49_source;
      packet49_copy_operation.copy_state = packet49_copy.state;
      packet49_copy_operation.copy = packet49_copy;
      packet49_copy_operation.copy_shaders_ready = true;
      std::vector<uint32_t> packet49_direct_readback;
      std::vector<uint32_t> packet49_ordered_readback;
      std::string packet49_error;
      if (!shift::xbox::submit_captured_vulkan_frame(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720, {packet49_draw}, &packet49_error,
              &packet49_direct_readback, enabled_features.geometryShader,
              &packet49_copy, false, {}, pipeline_cache, nullptr) ||
          !shift::xbox::submit_captured_vulkan_operation_stream(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720, {packet49_draw},
              {packet49_draw_operation, packet49_copy_operation},
              &packet49_error, &packet49_ordered_readback,
              enabled_features.geometryShader, &packet49_copy, false, {},
              pipeline_cache, nullptr) ||
          packet49_ordered_readback != packet49_direct_readback) {
        std::cerr << "captured packet-49 4x gamma draw to sample-zero 1x "
                     "linear source replay failed: " << packet49_error << '\n';
        return 1;
      }

      // Regression shaped like the live ordered packet 24..28 -> Copy 53
      // transition. Its shaders and triangles are synthetic smoke inputs; the
      // test checks ordered executor acceptance and equality with its direct
      // mixed-sample path, not retail image parity.
      std::vector<shift::xbox::CapturedVulkanDraw> packet24_to_53_draws(
          5, packet49_draw);
      for (size_t i = 1; i < packet24_to_53_draws.size(); ++i) {
        packet24_to_53_draws[i].raster.sample_count = 1;
        packet24_to_53_draws[i].raster.surface_pitch = 1280;
      }
      std::vector<shift::xbox::CapturedVulkanOperation>
          packet24_to_53_operations;
      for (uint32_t i = 0; i < packet24_to_53_draws.size(); ++i) {
        shift::xbox::CapturedVulkanOperation operation{};
        operation.type = shift::xbox::CapturedVulkanOperation::Type::Draw;
        operation.packet_index = 24u + i;
        operation.draw_index = i;
        packet24_to_53_operations.push_back(operation);
      }
      auto packet53_copy_operation = packet49_copy_operation;
      packet53_copy_operation.packet_index = 53;
      packet24_to_53_operations.push_back(packet53_copy_operation);
      std::vector<uint32_t> packet24_to_53_direct_readback;
      std::vector<uint32_t> packet24_to_53_ordered_readback;
      if (!shift::xbox::submit_captured_vulkan_frame(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720, packet24_to_53_draws,
              &packet49_error, &packet24_to_53_direct_readback,
              enabled_features.geometryShader, &packet49_copy, false, {},
              pipeline_cache, nullptr) ||
          !shift::xbox::submit_captured_vulkan_operation_stream(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720, packet24_to_53_draws,
              packet24_to_53_operations, &packet49_error,
              &packet24_to_53_ordered_readback,
              enabled_features.geometryShader, &packet49_copy, false, {},
              pipeline_cache, nullptr) ||
          packet24_to_53_ordered_readback != packet24_to_53_direct_readback) {
        std::cerr << "ordered packet 24..28 4x-to-1x Draw/Copy 53 transition "
                     "failed or differed from its mixed-sample path: "
                  << packet49_error << '\n';
        return 1;
      }
      auto unsupported_transition_draws = packet24_to_53_draws;
      unsupported_transition_draws[1].raster.surface_pitch = 1272;
      std::string unsupported_transition_error;
      if (shift::xbox::submit_captured_vulkan_operation_stream(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720, unsupported_transition_draws,
              packet24_to_53_operations, &unsupported_transition_error,
              nullptr, enabled_features.geometryShader, &packet49_copy, false,
              {}, pipeline_cache, nullptr) ||
          unsupported_transition_error.find(
              "draw packet 25 changes target layout before a Copy/Convert boundary") ==
              std::string::npos) {
        std::cerr << "ordered executor accepted an unobserved 4x-to-1x target "
                     "pitch: " << unsupported_transition_error << '\n';
        return 1;
      }

      auto captured_depth_only_view = packet49_draw;
      captured_depth_only_view.raster.depth_only = true;
      captured_depth_only_view.raster.color_format =
          shift::xbox::CapturedColorTargetFormat::Rgba8Linear;
      captured_depth_only_view.raster.guest_color_format = 0;
      captured_depth_only_view.raster.color_write_mask = 0;
      captured_depth_only_view.raster.depth_test_enabled = true;
      captured_depth_only_view.raster.depth_write_enabled = true;
      captured_depth_only_view.raster.depth_control = 6u | (7u << 4);
      shift::xbox::CapturedVulkanOperation depth_only_operation{};
      depth_only_operation.type =
          shift::xbox::CapturedVulkanOperation::Type::Draw;
      depth_only_operation.packet_index = 25;
      depth_only_operation.draw_index = 1;
      std::vector<uint32_t> depth_only_view_direct_readback;
      std::vector<uint32_t> depth_only_view_ordered_readback;
      const std::vector<shift::xbox::CapturedVulkanOperation>
          depth_only_view_operations{packet49_draw_operation,
                                     depth_only_operation,
                                     packet49_copy_operation};
      if (!shift::xbox::submit_captured_vulkan_frame(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720,
              {packet49_draw, captured_depth_only_view}, &packet49_error,
              &depth_only_view_direct_readback, enabled_features.geometryShader,
              &packet49_copy, false, {}, pipeline_cache, nullptr) ||
          !shift::xbox::submit_captured_vulkan_operation_stream(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720,
              {packet49_draw, captured_depth_only_view},
              depth_only_view_operations, &packet49_error,
              &depth_only_view_ordered_readback,
              enabled_features.geometryShader, &packet49_copy, false, {},
              pipeline_cache, nullptr) ||
          depth_only_view_ordered_readback != depth_only_view_direct_readback) {
        std::cerr << "captured gamma-to-depth-only target view did not preserve "
                     "ordered Draw/Copy execution: " << packet49_error << '\n';
        return 1;
      }
      // v45 also changes from the captured 1x gamma view back to its 4x,
      // pitch-640 depth-only view before Copy/Convert packet 54. The draw
      // payload is synthetic; this checks ordered routing and executor parity.
      auto packet29_depth_only = packet24_to_53_draws.back();
      packet29_depth_only.raster.depth_only = true;
      packet29_depth_only.raster.color_format =
          shift::xbox::CapturedColorTargetFormat::Rgba8Linear;
      packet29_depth_only.raster.guest_color_format = 0;
      packet29_depth_only.raster.color_write_mask = 0;
      packet29_depth_only.raster.sample_count = 4;
      packet29_depth_only.raster.surface_pitch = 640;
      packet29_depth_only.raster.depth_test_enabled = false;
      packet29_depth_only.raster.depth_write_enabled = false;
      packet29_depth_only.raster.stencil_test_enabled = false;
      auto packet24_to_54_draws = packet24_to_53_draws;
      packet24_to_54_draws.push_back(packet29_depth_only);
      auto packet24_to_54_operations = packet24_to_53_operations;
      packet24_to_54_operations.pop_back();
      shift::xbox::CapturedVulkanOperation packet29_operation{};
      packet29_operation.type =
          shift::xbox::CapturedVulkanOperation::Type::Draw;
      packet29_operation.packet_index = 29;
      packet29_operation.draw_index = 5;
      packet24_to_54_operations.push_back(packet29_operation);
      auto packet54_copy_operation = packet53_copy_operation;
      packet54_copy_operation.packet_index = 54;
      packet24_to_54_operations.push_back(packet54_copy_operation);
      std::vector<uint32_t> packet24_to_54_direct_readback;
      std::vector<uint32_t> packet24_to_54_ordered_readback;
      if (!shift::xbox::submit_captured_vulkan_frame(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720, packet24_to_54_draws,
              &packet49_error, &packet24_to_54_direct_readback,
              enabled_features.geometryShader, &packet49_copy, false, {},
              pipeline_cache, nullptr) ||
          !shift::xbox::submit_captured_vulkan_operation_stream(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720, packet24_to_54_draws,
              packet24_to_54_operations, &packet49_error,
              &packet24_to_54_ordered_readback,
              enabled_features.geometryShader, &packet49_copy, false, {},
              pipeline_cache, nullptr) ||
          packet24_to_54_ordered_readback != packet24_to_54_direct_readback) {
        std::cerr << "ordered packet 24..29 mixed-sample depth-only view failed: "
                  << packet49_error << '\n';
        return 1;
      }

      // Another v45 transition starts on a 4x depth-only view and returns to
      // its 1x gamma color view. The Copy/Convert reads that last color view.
      auto packet24_depth_only = packet29_depth_only;
      auto packet26_gamma = packet24_to_53_draws[1];
      const std::vector<shift::xbox::CapturedVulkanDraw>
          packet24_to_72_draws{packet24_depth_only, packet26_gamma};
      auto packet24_operation = packet49_draw_operation;
      packet24_operation.packet_index = 24;
      auto packet26_operation = depth_only_operation;
      packet26_operation.packet_index = 26;
      packet26_operation.draw_index = 1;
      auto packet72_copy_operation = packet49_copy_operation;
      packet72_copy_operation.packet_index = 72;
      const std::vector<shift::xbox::CapturedVulkanOperation>
          packet24_to_72_operations{packet24_operation, packet26_operation,
                                    packet72_copy_operation};
      std::vector<uint32_t> packet24_to_72_direct_readback;
      std::vector<uint32_t> packet24_to_72_ordered_readback;
      if (!shift::xbox::submit_captured_vulkan_frame(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720, packet24_to_72_draws,
              &packet49_error, &packet24_to_72_direct_readback,
              enabled_features.geometryShader, &packet49_copy, false, {},
              pipeline_cache, nullptr) ||
          !shift::xbox::submit_captured_vulkan_operation_stream(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720, packet24_to_72_draws,
              packet24_to_72_operations, &packet49_error,
              &packet24_to_72_ordered_readback,
              enabled_features.geometryShader, &packet49_copy, false, {},
              pipeline_cache, nullptr) ||
          packet24_to_72_ordered_readback != packet24_to_72_direct_readback) {
        std::cerr << "ordered packet 24..26 depth-only-to-gamma transition failed: "
                  << packet49_error << '\n';
        return 1;
      }

      auto unsupported_packet29_layout = packet24_to_54_draws;
      unsupported_packet29_layout.back().raster.surface_pitch = 636;
      std::string unsupported_packet29_error;
      if (shift::xbox::submit_captured_vulkan_operation_stream(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720, unsupported_packet29_layout,
              packet24_to_54_operations, &unsupported_packet29_error, nullptr,
              enabled_features.geometryShader, &packet49_copy, false, {},
              pipeline_cache, nullptr) ||
          unsupported_packet29_error.find(
              "draw packet 29 changes target layout before a Copy/Convert boundary") ==
              std::string::npos) {
        std::cerr << "ordered executor accepted an unmatched packet-29 depth-only "
                     "pitch: " << unsupported_packet29_error << '\n';
        return 1;
      }

      auto unsupported_depth_only_view = captured_depth_only_view;
      ++unsupported_depth_only_view.raster.depth_base_tiles;
      std::string unsupported_depth_only_error;
      if (shift::xbox::submit_captured_vulkan_operation_stream(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720,
              {packet49_draw, unsupported_depth_only_view},
              depth_only_view_operations, &unsupported_depth_only_error,
              nullptr, enabled_features.geometryShader, &packet49_copy, false,
              {}, pipeline_cache, nullptr) ||
          unsupported_depth_only_error.find(
              "draw packet 25 changes target layout before a Copy/Convert boundary") ==
              std::string::npos) {
        std::cerr << "ordered executor accepted a depth-only view with an "
                     "unmatched depth base: " << unsupported_depth_only_error
                  << '\n';
        return 1;
      }

      auto unsupported_packet49_source = packet49_copy_operation;
      unsupported_packet49_source.source_raster.surface_pitch = 1272;
      std::string unsupported_packet49_error;
      if (shift::xbox::submit_captured_vulkan_operation_stream(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720, {packet49_draw},
              {packet49_draw_operation, unsupported_packet49_source},
              &unsupported_packet49_error, nullptr,
              enabled_features.geometryShader, &packet49_copy, false, {},
              pipeline_cache, nullptr) ||
          unsupported_packet49_error.find(
              "Copy/Convert packet 49 reinterprets the active draw segment") ==
              std::string::npos) {
        std::cerr << "ordered replay accepted a near-matching packet-49 source pitch: "
                  << unsupported_packet49_error << '\n';
        return 1;
      }

      auto copy_without_source = copy0;
      copy_without_source.packet_index = 200;
      auto draw_after_copy = draw0;
      draw_after_copy.packet_index = 201;
      std::string missing_source_error;
      if (shift::xbox::submit_captured_vulkan_operation_stream(
              physical_device, device, queue, queue_family, output_image,
              output_view, false, 1280, 720, {format31_source},
              {copy_without_source, draw_after_copy}, &missing_source_error,
              nullptr, enabled_features.geometryShader, &copy, false, {},
              pipeline_cache, nullptr) ||
          missing_source_error.find(
              "Copy/Convert packet 200 has no preceding captured draw segment") ==
              std::string::npos) {
        std::cerr << "ordered executor guessed an unavailable initial EDRAM source: "
                  << missing_source_error << '\n';
        return 1;
      }
      ordered_copy_cache.clear();
    }
    const size_t cached_sampler_count = texture_cache.cached_sampler_count();
    const size_t cached_descriptor_layout_count =
        texture_cache.cached_descriptor_layout_count();
    const size_t descriptor_layout_cache_hits =
        texture_cache.descriptor_layout_cache_hits();
    if (texture_cache.size() != draws.size() ||
        texture_cache.cached_pipeline_count() != draws.size() ||
        cached_descriptor_layout_count == 0 ||
        cached_sampler_count == 0) {
      std::cerr << "captured texture or graphics pipeline cache did not retain "
                   "each draw resource and its sampler state\n";
      return 1;
    }
    auto switched_render_target_draws = draws;
    switched_render_target_draws[1].raster.color_base_tiles++;
    std::string switched_render_target_error;
    if (shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, switched_render_target_draws,
            &switched_render_target_error, nullptr,
            enabled_features.geometryShader, &copy) ||
        switched_render_target_error.find(
            "at draw 1 (color_base=13 -> 14") ==
            std::string::npos) {
      std::cerr << "distinct captured render-target bases were merged into one "
                   "Vulkan pass: "
                << switched_render_target_error << '\n';
      return 1;
    }
    auto changed_extent_draws = draws;
    changed_extent_draws[1].raster.width--;
    std::string changed_extent_error;
    if (shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, changed_extent_draws,
            &changed_extent_error, nullptr, enabled_features.geometryShader,
            &copy) ||
        changed_extent_error.find("extent=1280x720 -> 1279x720") ==
            std::string::npos ||
        changed_extent_error.find("ordered target layouts=draw0{extent=1280x720") ==
            std::string::npos ||
        changed_extent_error.find("draw1{extent=1279x720,samples=") ==
            std::string::npos ||
        changed_extent_error.find(",color_base=") == std::string::npos ||
        changed_extent_error.find(",depth_format=") == std::string::npos ||
        changed_extent_error.find(",pitch=") == std::string::npos) {
      std::cerr << "distinct captured target extents were merged or the ordered "
                   "layout diagnostic was incomplete: "
                << changed_extent_error << '\n';
      return 1;
    }

    // Target layouts transcribed from the Redmi retail 14-draw transition.
    // Keep this fail-closed until the renderer persists and reinterprets the
    // aliased Xenos EDRAM contents between these Vulkan passes.
    auto retail_layout_4x_hdr = draws.front().raster;
    retail_layout_4x_hdr.width = 2560;
    retail_layout_4x_hdr.height = 1440;
    retail_layout_4x_hdr.surface_pitch = 1280;
    retail_layout_4x_hdr.sample_count = 4;
    retail_layout_4x_hdr.color_base_tiles = 0;
    retail_layout_4x_hdr.depth_base_tiles = 1024;
    retail_layout_4x_hdr.color_format =
        shift::xbox::CapturedColorTargetFormat::Rgb10A2Float;
    retail_layout_4x_hdr.guest_color_format = 12u;
    auto retail_layout_4x_rgba8 = retail_layout_4x_hdr;
    retail_layout_4x_rgba8.width = 1280;
    retail_layout_4x_rgba8.height = 720;
    retail_layout_4x_rgba8.surface_pitch = 640;
    retail_layout_4x_rgba8.depth_base_tiles = 720;
    retail_layout_4x_rgba8.color_format =
        shift::xbox::CapturedColorTargetFormat::Rgba8Linear;
    retail_layout_4x_rgba8.guest_color_format = 0u;
    auto retail_layout_1x_gamma = retail_layout_4x_rgba8;
    retail_layout_1x_gamma.surface_pitch = 1280;
    retail_layout_1x_gamma.sample_count = 1;
    retail_layout_1x_gamma.color_format =
        shift::xbox::CapturedColorTargetFormat::Rgba8Gamma;
    retail_layout_1x_gamma.guest_color_format = 1u;
    const std::array<shift::xbox::CapturedRasterState, 4>
        retail_transition_layouts{{retail_layout_4x_hdr,
                                   retail_layout_4x_rgba8,
                                   retail_layout_1x_gamma,
                                   retail_layout_4x_rgba8}};
    constexpr std::array<size_t, 14> retail_layout_by_draw{{
        0, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 2, 2,
    }};
    std::vector<shift::xbox::CapturedVulkanDraw> retail_transition_draws(
        retail_layout_by_draw.size(), draws.front());
    for (size_t i = 0; i < retail_transition_draws.size(); ++i) {
      retail_transition_draws[i].raster =
          retail_transition_layouts[retail_layout_by_draw[i]];
    }
    std::string retail_transition_error;
    if (shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, retail_transition_draws,
            &retail_transition_error, nullptr,
            enabled_features.geometryShader, &copy) ||
        retail_transition_error.find(
            "at draw 1 (color_base=0 -> 0, depth_base=1024 -> 720, "
            "extent=2560x1440 -> 1280x720, color_format=3 -> 0, "
            "guest_color_format=12 -> 0, "
            "pitch=1280 -> 640)") == std::string::npos ||
        retail_transition_error.find(
            "Xenos color sample 0 aliases at EDRAM byte offset 0") ==
            std::string::npos) {
      std::cerr << "the captured retail 14-draw target transition was not "
                   "rejected at its first unsupported EDRAM layout change: "
                << retail_transition_error << '\n';
      return 1;
    }
    for (size_t draw_index = 0; draw_index < retail_layout_by_draw.size();
         ++draw_index) {
      const auto& layout =
          retail_transition_layouts[retail_layout_by_draw[draw_index]];
      std::ostringstream expected_layout;
      expected_layout << "draw" << draw_index << "{extent=" << layout.width
                      << 'x' << layout.height << ",samples="
                      << layout.sample_count << ",color_base="
                      << layout.color_base_tiles << ",depth_base="
                      << layout.depth_base_tiles << ",color_format="
                      << static_cast<unsigned>(layout.color_format)
                      << ",guest_color_format=" << layout.guest_color_format
                      << ",depth_format="
                      << static_cast<unsigned>(layout.depth_format)
                      << ",pitch=" << layout.surface_pitch << '}';
      if (retail_transition_error.find(expected_layout.str()) ==
          std::string::npos) {
        std::cerr << "the captured retail target transition diagnostic lost "
                     "draw "
                  << draw_index << " layout: " << retail_transition_error
                  << '\n';
        return 1;
      }
    }

    std::vector<shift::xbox::CapturedVulkanOperation> ordered_operations;
    for (size_t draw_index = 0; draw_index < draws.size(); ++draw_index) {
      if (draw_index == 1) {
        shift::xbox::CapturedVulkanOperation copy_operation{};
        copy_operation.type =
            shift::xbox::CapturedVulkanOperation::Type::CopyConvert;
        copy_operation.packet_index = 101;
        copy_operation.source_width = 1280;
        copy_operation.source_height = 720;
        copy_operation.source_surface_info = 0x14020500u;
        copy_operation.source_color_info = 0x000C0000u;
        copy_operation.source_depth_info = 0x00000400u;
        copy_operation.source_mode_control = 6u;
        copy_operation.copy_state.destination_base = 0x0CC87000u;
        copy_operation.copy_state.destination_pitch = 256;
        copy_operation.copy_state.destination_height = 243;
        copy_operation.copy_state.destination_format = 31;
        copy_operation.copy_state.destination_number_format = 7;
        copy_operation.copy_state.destination_endian = 2;
        copy_operation.copy_state.color_clear_enable = true;
        copy_operation.copy = copy;
        copy_operation.copy.state = copy_operation.copy_state;
        copy_operation.copy.pixel_shader_spirv =
            copy_sample0_rg16f_ms_spirv;
        copy_operation.copy.single_sample_pixel_shader_spirv =
            copy_sample0_rg16f_single_spirv;
        copy_operation.copy_shaders_ready = true;
        ordered_operations.push_back(copy_operation);
      }
      shift::xbox::CapturedVulkanOperation draw_operation{};
      draw_operation.type = shift::xbox::CapturedVulkanOperation::Type::Draw;
      draw_operation.draw_index = static_cast<uint32_t>(draw_index);
      draw_operation.packet_index = 100u + static_cast<uint32_t>(draw_index) * 2u;
      ordered_operations.push_back(draw_operation);
    }
    std::string ordered_operations_error;
    if (shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, changed_extent_draws,
            &ordered_operations_error, nullptr, enabled_features.geometryShader,
            &copy, false, {}, VK_NULL_HANDLE, nullptr, nullptr, nullptr,
            &ordered_operations) ||
        ordered_operations_error.find(
            "ordered operations=draw(packet=100,index=0);copy(packet=101,source=1280x720,source_regs=0x14020500/0xc0000/0x400/0x6,destination=0xcc87000,256x243,format=31/7,endian=2,exp_bias=0,samples=0,clear=1/0,clear_registers={ready:0,color:0x0,color_lo:0x0,depth:0x0},source_target={ready:0},swap_rb=0,shaders=prepared,source_geometry=missing);draw(packet=102,index=1)") ==
            std::string::npos) {
      std::cerr << "ordered draw/copy operations were lost from the target-layout "
                   "diagnostic: "
                << ordered_operations_error << '\n';
      return 1;
    }
    auto unprepared_copy_operations = ordered_operations;
    unprepared_copy_operations[1].copy_shaders_ready = false;
    std::string unprepared_copy_error;
    if (shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, changed_extent_draws,
            &unprepared_copy_error, nullptr, enabled_features.geometryShader,
            &copy, false, {}, VK_NULL_HANDLE, nullptr, nullptr, nullptr,
            &unprepared_copy_operations) ||
        unprepared_copy_error.find(
            "Copy/Convert packet 101 has no prepared Vulkan shader payload") ==
            std::string::npos) {
      std::cerr << "Copy/Convert without its operation-local shaders was accepted: "
                << unprepared_copy_error << '\n';
      return 1;
    }
    auto reordered_operations = ordered_operations;
    std::swap(reordered_operations[0], reordered_operations[2]);
    std::string reordered_operations_error;
    if (shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, changed_extent_draws,
            &reordered_operations_error, nullptr, enabled_features.geometryShader,
            &copy, false, {}, VK_NULL_HANDLE, nullptr, nullptr, nullptr,
            &reordered_operations) ||
        reordered_operations_error.find(
            "captured operation stream has duplicate or reordered draw") ==
            std::string::npos) {
      std::cerr << "reordered captured draw references were accepted: "
                << reordered_operations_error << '\n';
      return 1;
    }
    auto reordered_packet_operations = ordered_operations;
    reordered_packet_operations[1].packet_index = 103;
    std::string reordered_packet_error;
    if (shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, changed_extent_draws,
            &reordered_packet_error, nullptr, enabled_features.geometryShader,
            &copy, false, {}, VK_NULL_HANDLE, nullptr, nullptr, nullptr,
            &reordered_packet_operations) ||
        reordered_packet_error.find(
            "captured operation stream has missing or reordered packet ordinal") ==
            std::string::npos) {
      std::cerr << "reordered captured packet ordinals were accepted: "
                << reordered_packet_error << '\n';
      return 1;
    }
    auto incomplete_copy_operations = ordered_operations;
    incomplete_copy_operations[1].copy_state.destination_pitch = 0;
    std::string incomplete_copy_error;
    if (shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, changed_extent_draws,
            &incomplete_copy_error, nullptr, enabled_features.geometryShader,
            &copy, false, {}, VK_NULL_HANDLE, nullptr, nullptr, nullptr,
            &incomplete_copy_operations) ||
        incomplete_copy_error.find(
            "Copy/Convert packet 101 has incomplete source or destination extent") ==
            std::string::npos) {
      std::cerr << "incomplete captured Copy/Convert was accepted: "
                << incomplete_copy_error << '\n';
      return 1;
    }
    auto unresolved_draw_operations = ordered_operations;
    unresolved_draw_operations[0].type =
        shift::xbox::CapturedVulkanOperation::Type::UnresolvedDraw;
    unresolved_draw_operations[0].draw_raster_ready = true;
    unresolved_draw_operations[0].draw_raster = changed_extent_draws[0].raster;
    unresolved_draw_operations[0].draw_registers_ready = true;
    unresolved_draw_operations[0].draw_register_valid_mask = 0x17038u;
    unresolved_draw_operations[0].draw_registers.surface_info = 0x14000500u;
    unresolved_draw_operations[0].draw_registers.color_info = 0x000D0000u;
    unresolved_draw_operations[0].draw_registers.depth_info = 0x0001D000u;
    unresolved_draw_operations[0].draw_registers.mode_control = 4u;
    unresolved_draw_operations[0].draw_registers.depth_control = 0x00008777u;
    unresolved_draw_operations[0].draw_registers.color_mask = 0xFu;
    unresolved_draw_operations[0].draw_registers.stencil_refmask = 0x00123456u;
    unresolved_draw_operations[0].draw_registers.stencil_refmask_valid = true;
    const std::string unresolved_draw_trace =
        shift::xbox::describe_captured_vulkan_operations(unresolved_draw_operations);
    if (unresolved_draw_trace.find(
            "unresolved(packet=100,draw_registers={valid_mask=0x17038") ==
            std::string::npos ||
        unresolved_draw_trace.find("depth_write=1,stencil_test=1") ==
            std::string::npos ||
        unresolved_draw_trace.find(
            "surface=0x14000500,color=0xd0000,depth=0x1d000") ==
            std::string::npos ||
        unresolved_draw_trace.find("stencil_refmask_valid=1") ==
            std::string::npos) {
      std::cerr << "unresolved draw trace lost captured target side effects: "
                << unresolved_draw_trace << '\n';
      return 1;
    }
    std::string unresolved_draw_error;
    if (shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, changed_extent_draws,
            &unresolved_draw_error, nullptr, enabled_features.geometryShader,
            &copy, false, {}, VK_NULL_HANDLE, nullptr, nullptr, nullptr,
            &unresolved_draw_operations) ||
        unresolved_draw_error.find(
            "captured operation stream contains unresolved draw packet 100") ==
            std::string::npos ||
        unresolved_draw_error.find(
            "unresolved(packet=100,draw_registers={valid_mask=0x17038") ==
            std::string::npos ||
        unresolved_draw_error.find("depth_write=1,stencil_test=1") ==
            std::string::npos) {
      std::cerr << "unresolved captured draw was accepted: "
                << unresolved_draw_error << '\n';
      return 1;
    }
    auto resolved_draw_operations = unresolved_draw_operations;
    resolved_draw_operations[0].type =
        shift::xbox::CapturedVulkanOperation::Type::Draw;
    const std::string resolved_draw_trace =
        shift::xbox::describe_captured_vulkan_operations(resolved_draw_operations);
    if (resolved_draw_trace.find(
            "draw(packet=100,index=0,draw_registers={valid_mask=0x17038") ==
            std::string::npos ||
        resolved_draw_trace.find(
            "surface=0x14000500,color=0xd0000,depth=0x1d000") ==
            std::string::npos ||
        resolved_draw_trace.find("depth_write=1,stencil_test=1") ==
            std::string::npos) {
      std::cerr << "resolved draw trace lost captured raster state: "
                << resolved_draw_trace << '\n';
      return 1;
    }
    auto unresolved_copy_operations = ordered_operations;
    unresolved_copy_operations[1].type =
        shift::xbox::CapturedVulkanOperation::Type::UnresolvedCopy;
    std::string unresolved_copy_error;
    if (shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, changed_extent_draws,
            &unresolved_copy_error, nullptr, enabled_features.geometryShader,
            &copy, false, {}, VK_NULL_HANDLE, nullptr, nullptr, nullptr,
            &unresolved_copy_operations) ||
        unresolved_copy_error.find(
            "captured operation stream contains unresolved Copy/Convert packet 101") ==
            std::string::npos) {
      std::cerr << "unresolved captured Copy/Convert was accepted: "
                << unresolved_copy_error << '\n';
      return 1;
    }
    auto oversized_target_draws = changed_extent_draws;
    oversized_target_draws.resize(66, draws.front());
    std::string oversized_target_error;
    if (shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, oversized_target_draws,
            &oversized_target_error, nullptr, enabled_features.geometryShader,
            &copy) ||
        oversized_target_error.find("omitted target layouts=2") ==
            std::string::npos) {
      std::cerr << "ordered target layout diagnostics were not bounded at 64: "
                << oversized_target_error << '\n';
      return 1;
    }
    auto changed_format_draws = draws;
    changed_format_draws[1].raster.color_format =
        shift::xbox::CapturedColorTargetFormat::Rgb10A2Unorm;
    std::string changed_format_error;
    if (shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, changed_format_draws,
            &changed_format_error, nullptr, enabled_features.geometryShader,
            &copy) ||
        changed_format_error.find("color_format=1 -> 2") == std::string::npos) {
      std::cerr << "distinct captured target formats were merged into one "
                   "Vulkan pass: "
                << changed_format_error << '\n';
      return 1;
    }
    auto aliased_vk_color_format_draws = draws;
    aliased_vk_color_format_draws[0].raster.color_format =
        shift::xbox::CapturedColorTargetFormat::Rgb10A2Float;
    aliased_vk_color_format_draws[0].raster.guest_color_format = 3u;
    aliased_vk_color_format_draws[1].raster.color_format =
        shift::xbox::CapturedColorTargetFormat::Rgb10A2Float;
    aliased_vk_color_format_draws[1].raster.guest_color_format = 12u;
    std::string aliased_vk_color_format_error;
    if (shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, aliased_vk_color_format_draws,
            &aliased_vk_color_format_error, nullptr,
            enabled_features.geometryShader, &copy) ||
        aliased_vk_color_format_error.find(
            "guest_color_format=3 -> 12") == std::string::npos) {
      std::cerr << "Distinct Xenos formats sharing a Vulkan format were merged: "
                << aliased_vk_color_format_error << '\n';
      return 1;
    }
    auto changed_pitch_draws = draws;
    changed_pitch_draws[1].raster.surface_pitch--;
    std::string changed_pitch_error;
    if (shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, changed_pitch_draws,
            &changed_pitch_error, nullptr, enabled_features.geometryShader,
            &copy) ||
        changed_pitch_error.find("pitch=1280 -> 1279") == std::string::npos) {
      std::cerr << "distinct captured target pitches were merged into one "
                   "Vulkan pass: "
                << changed_pitch_error << '\n';
      return 1;
    }
    const std::vector<uint32_t> cached_output = output_readback;
    std::vector<uint32_t> repeated_cached_output;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, draws, &error,
            &repeated_cached_output, enabled_features.geometryShader, &copy,
            false, {}, pipeline_cache, &texture_cache) ||
        repeated_cached_output != cached_output ||
        texture_cache.cached_pipeline_count() != draws.size() ||
        texture_cache.cached_sampler_count() != cached_sampler_count ||
        texture_cache.cached_descriptor_layout_count() !=
            cached_descriptor_layout_count ||
        texture_cache.descriptor_layout_cache_hits() <=
            descriptor_layout_cache_hits) {
      std::cerr << "reused Vulkan pipeline cache changed captured draw output: "
                << error << '\n';
      return 1;
    }

    auto black_copy = copy;
    black_copy.pixel_shader_spirv = black_copy_fragment_spirv;
    black_copy.single_sample_pixel_shader_spirv = black_copy_fragment_spirv;
    shift::xbox::CapturedVulkanSourceReadback colored_source_readback;
    std::vector<shift::xbox::CapturedVulkanDrawVisibility>
        colored_source_visibility;
    std::vector<uint32_t> black_final_output;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, draws, &error, &black_final_output,
            enabled_features.geometryShader, &black_copy, false, {},
            pipeline_cache, nullptr, &colored_source_readback,
            &colored_source_visibility)) {
        std::cerr << "source color-target readback with black Copy/Convert failed: "
                  << error << '\n';
        return 1;
    }
    bool colored_source_has_rgb = false;
    for (size_t pixel = 0; pixel + 7 < colored_source_readback.bytes.size();
         pixel += 8) {
        for (size_t channel = 0; channel < 3; ++channel) {
            colored_source_has_rgb |=
                colored_source_readback.bytes[pixel + channel * 2] != 0 ||
                colored_source_readback.bytes[pixel + channel * 2 + 1] != 0;
        }
    }
    if (colored_source_readback.status !=
            shift::xbox::CapturedVulkanSourceReadback::Status::Captured ||
        colored_source_readback.width != 1280 ||
        colored_source_readback.height != 720 ||
        colored_source_readback.format != VK_FORMAT_R16G16B16A16_UNORM ||
        colored_source_readback.sample_count != 4 ||
        !colored_source_readback.multisample_average_resolve ||
        colored_source_readback.bytes.size() != 1280u * 720u * 8u ||
        !colored_source_has_rgb || black_final_output.size() != 1280u * 720u ||
        colored_source_visibility.size() != draws.size() ||
        !colored_source_visibility[0].available ||
        !colored_source_visibility[0].any_samples_passed ||
        std::any_of(black_final_output.begin(), black_final_output.end(),
                    [](uint32_t pixel) {
                        return (pixel & 0x3FFFFFFFu) != 0;
                    })) {
        std::cerr << "pre-Copy readback did not distinguish a colored 4x source "
                     "from its black final output\n";
        return 1;
    }

    std::vector<uint32_t> copy_preservation_baseline;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, draws, &error,
            &copy_preservation_baseline, enabled_features.geometryShader,
            &copy, false, {}, pipeline_cache)) {
      std::cerr << "Copy/Convert geometry preservation baseline failed: "
                << error << '\n';
      return 1;
    }
    const bool copy_baseline_has_color = std::any_of(
        copy_preservation_baseline.begin(), copy_preservation_baseline.end(),
        [](uint32_t pixel) { return (pixel & 0x3FFFFFFFu) != 0; });
    auto empty_scissor_copy = black_copy;
    empty_scissor_copy.source_geometry_ready = true;
    empty_scissor_copy.source_geometry = operation_copy_geometry;
    empty_scissor_copy.source_geometry.raster.scissor_x0 = 0;
    empty_scissor_copy.source_geometry.raster.scissor_y0 = 0;
    empty_scissor_copy.source_geometry.raster.scissor_x1 = 0;
    empty_scissor_copy.source_geometry.raster.scissor_y1 = 0;
    empty_scissor_copy.source_geometry.raster.scissor_has_area = false;
    std::vector<uint32_t> empty_scissor_copy_output;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, true, 1280, 720, draws, &error,
            &empty_scissor_copy_output, enabled_features.geometryShader,
            &empty_scissor_copy, false, {}, pipeline_cache) ||
        copy_preservation_baseline.size() != 1280u * 720u ||
        !copy_baseline_has_color ||
        empty_scissor_copy_output != copy_preservation_baseline) {
        std::cerr << "captured Copy/Convert scissor did not preserve the loaded destination: "
                  << error << '\n';
        return 1;
    }

    auto black_source_draws = draws;
    for (auto& source_draw : black_source_draws) {
        source_draw.raster.color_write_mask = 0;
    }
    shift::xbox::CapturedVulkanSourceReadback black_source_readback;
    std::vector<shift::xbox::CapturedVulkanDrawVisibility>
        black_source_visibility;
    std::vector<uint32_t> black_source_final_output;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, black_source_draws, &error,
            &black_source_final_output, enabled_features.geometryShader,
            &black_copy, false, {}, pipeline_cache, nullptr,
            &black_source_readback, &black_source_visibility) ||
        black_source_readback.status !=
            shift::xbox::CapturedVulkanSourceReadback::Status::Captured ||
        black_source_readback.bytes.size() != 1280u * 720u * 8u ||
        black_source_final_output.size() != 1280u * 720u ||
        black_source_visibility.size() != black_source_draws.size() ||
        !black_source_visibility[0].available ||
        !black_source_visibility[0].any_samples_passed) {
        std::cerr << "black source color-target readback failed: " << error << '\n';
        return 1;
    }
    for (size_t pixel = 0; pixel + 7 < black_source_readback.bytes.size();
         pixel += 8) {
        if (black_source_readback.bytes[pixel] ||
            black_source_readback.bytes[pixel + 1] ||
            black_source_readback.bytes[pixel + 2] ||
            black_source_readback.bytes[pixel + 3] ||
            black_source_readback.bytes[pixel + 4] ||
            black_source_readback.bytes[pixel + 5]) {
            std::cerr << "black source target readback contained RGB color\n";
            return 1;
        }
    }
    if (std::any_of(black_source_final_output.begin(),
                    black_source_final_output.end(), [](uint32_t pixel) {
                        return (pixel & 0x3FFFFFFFu) != 0;
                    })) {
        std::cerr << "black source Copy/Convert unexpectedly wrote final RGB color\n";
        return 1;
    }

    auto changed_texture_draws = draws;
    changed_texture_draws.front().textures.front().pixels.front() = 0;
    const std::vector<shift::xbox::CapturedVulkanDraw> changed_texture_draw{
        changed_texture_draws.front()};
    std::vector<uint32_t> cached_updated_output;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, changed_texture_draw, &error,
            &cached_updated_output, enabled_features.geometryShader, &copy,
            false, {}, pipeline_cache, &texture_cache) ||
        texture_cache.size() != draws.size() ||
        texture_cache.cached_pipeline_count() != draws.size()) {
      std::cerr
          << "reused Vulkan R8 texture cache failed to update a video plane: "
          << error << '\n';
      return 1;
    }
    std::vector<uint32_t> uncached_updated_output;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, changed_texture_draw, &error,
            &uncached_updated_output, enabled_features.geometryShader, &copy) ||
        cached_updated_output != uncached_updated_output ||
        cached_updated_output == cached_output) {
      std::cerr << "reused Vulkan R8 texture cache disagrees with fresh video "
                   "upload: "
                << error << '\n';
      return 1;
    }

    auto point_sample_draw = changed_texture_draw.front();
    for (auto& texture : point_sample_draw.textures) {
      texture.sampling.mag_filter = shift::xbox::TextureFilter::Point;
      texture.sampling.min_filter = shift::xbox::TextureFilter::Point;
    }
    const std::vector<shift::xbox::CapturedVulkanDraw> point_sample_draws{
        point_sample_draw};
    std::vector<uint32_t> cached_point_sample_output;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, point_sample_draws, &error,
            &cached_point_sample_output, enabled_features.geometryShader,
            &copy, false, {}, pipeline_cache, &texture_cache) ||
        texture_cache.cached_sampler_count() != cached_sampler_count + 1) {
      std::cerr << "sampler cache merged distinct captured filter states: "
                << error << '\n';
      return 1;
    }
    std::vector<uint32_t> uncached_point_sample_output;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, point_sample_draws, &error,
            &uncached_point_sample_output, enabled_features.geometryShader,
            &copy) ||
        cached_point_sample_output != uncached_point_sample_output) {
      std::cerr << "cached captured sampler state changed Vulkan output: "
                << error << '\n';
      return 1;
    }

    shift::xbox::CapturedVulkanTextureCache asynchronous_cache;
    if (asynchronous_cache.has_in_flight_frames()) {
      std::cerr << "new Vulkan texture cache unexpectedly has in-flight frames\n";
      return 1;
    }
    size_t reusable_draw_buffer_count = 0;
    for (uint32_t frame = 0; frame < 4; ++frame) {
      if (!shift::xbox::submit_captured_vulkan_frame(
              physical_device, device, queue, queue_family, output_image,
              output_view, true, 1280, 720, draws, &error, nullptr,
              enabled_features.geometryShader, &copy, false, {}, pipeline_cache,
              &asynchronous_cache)) {
        std::cerr << "asynchronous cached Vulkan frame " << frame
                  << " failed: " << error << '\n';
        return 1;
      }
      if (!asynchronous_cache.has_in_flight_frames()) {
        std::cerr << "asynchronous cached frame was not tracked as in flight\n";
        return 1;
      }
      const size_t draw_buffer_count =
          asynchronous_cache.cached_draw_buffer_count();
      if (frame == 1) {
        reusable_draw_buffer_count = draw_buffer_count;
        if (reusable_draw_buffer_count == 0) {
          std::cerr << "cached asynchronous draws retained no upload buffers\n";
          return 1;
        }
      } else if (frame >= 2 &&
                 draw_buffer_count != reusable_draw_buffer_count) {
        std::cerr << "draw upload buffers were not reused after their frame "
                     "slot retired\n";
        return 1;
      }
    }
    const size_t coherent_pipeline_count =
        asynchronous_cache.cached_pipeline_count();
    const size_t coherent_texture_count = asynchronous_cache.size();
    if (!asynchronous_cache.wait_for_guest_memory_coherency(&error) ||
        asynchronous_cache.has_in_flight_frames() ||
        asynchronous_cache.cached_pipeline_count() != coherent_pipeline_count ||
        asynchronous_cache.size() != coherent_texture_count) {
      std::cerr << "guest memory coherency drain failed or discarded reusable "
                   "Vulkan resources: "
                << error << '\n';
      return 1;
    }
    std::vector<uint32_t> asynchronous_readback;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, true, 1280, 720, draws, &error, &asynchronous_readback,
            enabled_features.geometryShader, &copy, false, {}, pipeline_cache,
            &asynchronous_cache) ||
        asynchronous_readback != cached_output) {
      std::cerr
          << "in-flight cached Vulkan frames changed the captured output: "
          << error << '\n';
      return 1;
    }
    asynchronous_cache.clear();
    if (asynchronous_cache.cached_pipeline_count() != 0 ||
        asynchronous_cache.cached_sampler_count() != 0 ||
        asynchronous_cache.cached_draw_buffer_count() != 0) {
      std::cerr
          << "clearing in-flight texture cache retained GPU objects\n";
      return 1;
    }

    auto window_coordinates = draw;
    window_coordinates.vertex_shader_spirv = std::move(window_vertex_spirv);
    window_coordinates.geometry_shader_spirv = rectangle_geometry_spirv;
    window_coordinates.pixel_shader_spirv = std::move(window_fragment_spirv);
    window_coordinates.topology = shift::xbox::PrimitiveTopology::RectangleList;
    window_coordinates.index_count = 3;
    window_coordinates.auto_index = true;
    window_coordinates.vertex_stride_bytes = 0;
    window_coordinates.vertices.clear();
    window_coordinates.vertex_input_attributes.clear();
    window_coordinates.raster.sample_count = 1;
    window_coordinates.raster.color_format =
        shift::xbox::CapturedColorTargetFormat::Rgba8Linear;
    window_coordinates.raster.depth_test_enabled = false;
    window_coordinates.raster.depth_write_enabled = false;
    window_coordinates.raster.stencil_test_enabled = false;
    window_coordinates.raster.depth_control = 0;
    window_coordinates.raster.viewport_y_flipped = true;
    window_coordinates.raster.clip_disabled_window_coordinates = true;
    window_coordinates.raster.blend_control_0 = 0x00010001u;
    window_coordinates.textures = {draw.textures.front()};
    std::vector<uint32_t> window_output;
    std::string window_error;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image, output_view,
            false, 1280, 720, {window_coordinates}, &window_error, &window_output,
            enabled_features.geometryShader)) {
        std::cerr << "clip-disabled window-coordinate Vulkan draw failed: "
                  << window_error << '\n';
        return 1;
    }
    if (window_output.size() != 1280u * 720u) {
        std::cerr << "clip-disabled window-coordinate readback has the wrong size\n";
        return 1;
    }
    const auto channel = [&window_output](uint32_t x, uint32_t y, uint32_t shift) {
        return ((window_output[static_cast<size_t>(y) * 1280u + x] >> shift) & 1023u) /
               1023.0f;
    };
    if (channel(64, 64, 0) > 0.12f || channel(64, 64, 10) > 0.15f ||
        channel(1216, 656, 0) < 0.88f || channel(1216, 656, 10) < 0.82f) {
        std::cerr << "clip-disabled window coordinates were clipped or Y-flipped: "
                  << "top-left=" << channel(64, 64, 0) << ','
                  << channel(64, 64, 10) << " bottom-right="
                  << channel(1216, 656, 0) << ',' << channel(1216, 656, 10) << '\n';
        return 1;
    }

    auto anisotropic_draw = draws.front();
    anisotropic_draw.textures[0].sampling.anisotropy =
        shift::xbox::TextureAnisotropy::Max4To1;
    const shift::xbox::CapturedVulkanSamplerCapabilities sampler_capabilities{
        enabled_features.samplerAnisotropy != VK_FALSE,
        device_properties.limits.maxSamplerAnisotropy,
    };
    std::vector<uint32_t> anisotropy_fallback_output;
    std::string anisotropy_fallback_error;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image, output_view,
            false, 1280, 720, {anisotropic_draw}, &anisotropy_fallback_error,
            &anisotropy_fallback_output, enabled_features.geometryShader, nullptr,
            false, {false, 1.0f}) ||
        anisotropy_fallback_output.size() != 1280u * 720u) {
        std::cerr << "captured anisotropy capability fallback failed: "
                  << anisotropy_fallback_error << '\n';
        return 1;
    }
    if (enabled_features.samplerAnisotropy) {
        std::vector<uint32_t> anisotropy_output;
        std::string anisotropy_error;
        if (!shift::xbox::submit_captured_vulkan_frame(
                physical_device, device, queue, queue_family, output_image, output_view,
                false, 1280, 720, {anisotropic_draw}, &anisotropy_error,
                &anisotropy_output, enabled_features.geometryShader, nullptr, false,
                sampler_capabilities) ||
            anisotropy_output.size() != 1280u * 720u) {
            std::cerr << "captured 4:1 anisotropic sampler failed: "
                      << anisotropy_error << '\n';
            return 1;
        }
    }
    const bool anisotropy_sampler_path_ran = enabled_features.samplerAnisotropy;

    auto linear_target_draw = draws[1];
    linear_target_draw.raster.color_format =
        shift::xbox::CapturedColorTargetFormat::Rgba8Linear;
    std::vector<uint32_t> gamma_linear_output;
    std::string gamma_linear_error;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image, output_view,
            false, 1280, 720, {draws[0], linear_target_draw}, &gamma_linear_error,
            &gamma_linear_output, enabled_features.geometryShader, &copy) ||
        gamma_linear_output.size() != 1280u * 720u ||
        std::none_of(gamma_linear_output.begin(), gamma_linear_output.end(),
                     [](uint32_t pixel) { return (pixel & 0x3FFFFFFFu) != 0; })) {
        std::cerr << "captured Gamma-to-Linear target format transition failed: "
                  << gamma_linear_error << '\n';
        return 1;
    }

    auto gamma_target_draw = draws[0];
    gamma_target_draw.raster.sample_count = 4;
    gamma_target_draw.raster.depth_test_enabled = false;
    gamma_target_draw.raster.depth_write_enabled = false;
    gamma_target_draw.raster.stencil_test_enabled = false;
    gamma_target_draw.topology = shift::xbox::PrimitiveTopology::TriangleList;
    gamma_target_draw.index_count = 3;
    gamma_target_draw.pixel_shader_spirv = gamma_encoded_fragment_spirv;
    gamma_target_draw.pixel_shader_spirv_linear_target =
        gamma_linear_fragment_spirv;
    auto gamma_target_copy = copy;
    gamma_target_copy.source_gamma = true;
    gamma_target_copy.gamma_single_sample_pixel_shader_spirv =
        gamma_copy_single_fragment_spirv;
    gamma_target_copy.gamma_pixel_shader_spirv =
        gamma_copy_ms_fragment_spirv;
    shift::xbox::CapturedVulkanSourceReadback gamma_source_readback;
    std::vector<uint32_t> gamma_target_output;
    std::string gamma_target_error;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image, output_view,
            false, 1280, 720, {gamma_target_draw}, &gamma_target_error,
            &gamma_target_output, enabled_features.geometryShader,
            &gamma_target_copy, false, {}, pipeline_cache, nullptr,
            &gamma_source_readback) ||
        gamma_source_readback.status !=
            shift::xbox::CapturedVulkanSourceReadback::Status::Captured ||
        gamma_source_readback.format != VK_FORMAT_R16G16B16A16_UNORM ||
        gamma_source_readback.bytes.size() != 1280u * 720u * 8u ||
        gamma_target_output.size() != 1280u * 720u) {
        std::cerr << "linear UNORM16 gamma-target replay failed: "
                  << gamma_target_error << '\n';
        return 1;
    }
    const auto gamma_copy_encoded_once = [](
        const std::vector<uint32_t>& output,
        const shift::xbox::CapturedVulkanSourceReadback& source_readback) {
      for (size_t pixel = 0; pixel < output.size(); ++pixel) {
        const size_t source = pixel * 8u;
        const auto read_unorm16 = [&source_readback, source](size_t lane) {
          return static_cast<uint32_t>(source_readback.bytes[source + lane * 2u]) |
                 (static_cast<uint32_t>(
                      source_readback.bytes[source + lane * 2u + 1u]) << 8);
        };
        if (read_unorm16(0) < 16300u || read_unorm16(0) > 16450u ||
            read_unorm16(1) < 16300u || read_unorm16(1) > 16450u ||
            read_unorm16(2) < 16300u || read_unorm16(2) > 16450u ||
            read_unorm16(3) < 65400u) {
          continue;
        }
        const uint32_t pixel_output = output[pixel];
        const uint32_t red = pixel_output & 0x3FFu;
        const uint32_t green = (pixel_output >> 10) & 0x3FFu;
        const uint32_t blue = (pixel_output >> 20) & 0x3FFu;
        const bool encoded_once =
            red >= 507u && red <= 513u && green >= 507u && green <= 513u &&
            blue >= 507u && blue <= 513u;
        return encoded_once;
      }
      return false;
    };
    if (!gamma_copy_encoded_once(gamma_target_output, gamma_source_readback)) {
        std::cerr << "gamma target must blend in linear UNORM16 and encode once "
                     "at Copy/Convert\n";
        return 1;
    }

    auto gamma_linear_tail = gamma_target_draw;
    gamma_linear_tail.raster.sample_count = 1;
    gamma_linear_tail.raster.color_format =
        shift::xbox::CapturedColorTargetFormat::Rgba8Linear;
    gamma_linear_tail.pixel_shader_spirv = gamma_linear_fragment_spirv;
    shift::xbox::CapturedVulkanSourceReadback gamma_mixed_source_readback;
    std::vector<uint32_t> gamma_mixed_output;
    std::string gamma_mixed_error;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image, output_view,
            false, 1280, 720, {gamma_target_draw, gamma_linear_tail},
            &gamma_mixed_error, &gamma_mixed_output,
            enabled_features.geometryShader, &gamma_target_copy, false, {},
            pipeline_cache, nullptr, &gamma_mixed_source_readback) ||
        gamma_mixed_source_readback.status !=
            shift::xbox::CapturedVulkanSourceReadback::Status::Captured ||
        gamma_mixed_source_readback.format != VK_FORMAT_R16G16B16A16_UNORM ||
        gamma_mixed_source_readback.bytes.size() != 1280u * 720u * 8u ||
        gamma_mixed_output.size() != 1280u * 720u ||
        !gamma_copy_encoded_once(gamma_mixed_output, gamma_mixed_source_readback)) {
        std::cerr << "mixed-sample gamma target must encode once at Copy/Convert: "
                  << gamma_mixed_error << '\n';
        return 1;
    }

    auto packed_vertex_inputs = draw;
    packed_vertex_inputs.vertex_input_attributes = {
        {0, 1, 6, 6, 3},
        {1, 0, 37, 6, 4},
    };
    packed_vertex_inputs.vertex_stride_bytes = 24;
    packed_vertex_inputs.vertices.resize(24);
    std::vector<uint32_t> packed_vertex_output;
    std::string packed_vertex_error;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image, output_view,
            false, 1280, 720, {packed_vertex_inputs}, &packed_vertex_error,
            &packed_vertex_output, enabled_features.geometryShader, &copy) ||
        packed_vertex_output.size() != 1280u * 720u ||
        std::none_of(packed_vertex_output.begin(), packed_vertex_output.end(),
                     [](uint32_t pixel) { return (pixel & 0x3FFFFFFFu) != 0; })) {
        std::cerr << "captured 8_8_8_8/32_32_FLOAT Vulkan vertex inputs failed: "
                  << packed_vertex_error << '\n';
        return 1;
    }

    auto triangle = draw;
    triangle.topology = shift::xbox::PrimitiveTopology::TriangleList;
    triangle.index_count = 3;
    triangle.raster.cull_mode =
        shift::xbox::CapturedRasterState::CullMode::Back;
    // This test triangle is clockwise after the renderer's Y-flipped viewport;
    // the captured Xenos face bit must select it as the front-facing primitive.
    triangle.raster.front_face_ccw = false;
    const auto render_triangle = [&](shift::xbox::CapturedVulkanDraw test_draw,
                                    bool expected_visible) {
        std::vector<uint32_t> pixels;
        std::string triangle_error;
        if (!shift::xbox::submit_captured_vulkan_frame(
                physical_device, device, queue, queue_family, output_image,
                output_view, false, 1280, 720, {test_draw}, &triangle_error,
                &pixels, enabled_features.geometryShader, &copy)) {
            std::cerr << "Xenos cull-state triangle draw failed: "
                      << triangle_error << '\n';
            return false;
        }
        const bool visible = std::any_of(
            pixels.begin(), pixels.end(),
            [](uint32_t pixel) { return (pixel & 0x3FFFFFFFu) != 0; });
        if (visible != expected_visible) {
            std::cerr << "Xenos cull-state triangle visibility changed: expected "
                      << expected_visible << ", got " << visible << '\n';
            return false;
        }
        return true;
    };
    if (!render_triangle(triangle, true)) return 1;
    triangle.topology = shift::xbox::PrimitiveTopology::TriangleStrip;
    if (!render_triangle(triangle, true)) return 1;
    triangle.topology = shift::xbox::PrimitiveTopology::TriangleList;
    triangle.raster.cull_mode =
        shift::xbox::CapturedRasterState::CullMode::Front;
    if (!render_triangle(triangle, false)) return 1;
    triangle.raster.front_face_ccw = true;
    if (!render_triangle(triangle, true)) return 1;
    triangle.raster.cull_mode =
        shift::xbox::CapturedRasterState::CullMode::Back;
    if (!render_triangle(triangle, false)) return 1;

    auto float_target_triangle = triangle;
    float_target_triangle.raster.width = 2560;
    float_target_triangle.raster.height = 1440;
    float_target_triangle.raster.surface_pitch = 1280;
    float_target_triangle.raster.color_format =
        shift::xbox::CapturedColorTargetFormat::Rgb10A2Float;
    float_target_triangle.raster.cull_mode =
        shift::xbox::CapturedRasterState::CullMode::None;
    float_target_triangle.raster.front_face_ccw = true;
    float_target_triangle.raster.scissor_x0 = 0;
    float_target_triangle.raster.scissor_y0 = 0;
    float_target_triangle.raster.scissor_x1 = 2560;
    float_target_triangle.raster.scissor_y1 = 1440;
    auto float_target_single_sample = float_target_triangle;
    float_target_single_sample.raster.sample_count = 1;
    float_target_single_sample.raster.depth_test_enabled = false;
    float_target_single_sample.raster.depth_write_enabled = false;
    float_target_single_sample.raster.stencil_test_enabled = false;
    shift::xbox::CapturedVulkanCopy scaled_copy = copy;
    scaled_copy.source_width = 2560;
    scaled_copy.source_height = 1440;
    std::vector<uint32_t> scaled_float_output;
    std::string scaled_float_error;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720,
            {float_target_triangle, float_target_single_sample},
            &scaled_float_error, &scaled_float_output,
            enabled_features.geometryShader, &scaled_copy)) {
        std::cerr << "captured 4x 2_10_10_10_FLOAT Vulkan target failed: "
                  << scaled_float_error << '\n';
        return 1;
    }
    if (std::none_of(scaled_float_output.begin(), scaled_float_output.end(),
                     [](uint32_t pixel) {
                         return (pixel & 0x3FFFFFFFu) != 0;
                     })) {
        std::cerr << "captured float target and 2x Copy/Convert produced no pixels\n";
        return 1;
    }

    auto rg16_target_draw = draw;
    rg16_target_draw.raster.width = 320;
    rg16_target_draw.raster.height = 243;
    rg16_target_draw.raster.surface_pitch = 320;
    rg16_target_draw.raster.sample_count = 1;
    rg16_target_draw.raster.color_format =
        shift::xbox::CapturedColorTargetFormat::Rg16Float;
    rg16_target_draw.raster.depth_test_enabled = false;
    rg16_target_draw.raster.depth_write_enabled = false;
    rg16_target_draw.raster.stencil_test_enabled = false;
    rg16_target_draw.raster.scissor_x1 = 320;
    rg16_target_draw.raster.scissor_y1 = 243;
    auto rg16_copy = copy;
    rg16_copy.source_width = 320;
    rg16_copy.source_height = 243;
    std::vector<uint32_t> rg16_target_output;
    std::string rg16_target_error;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, {rg16_target_draw},
            &rg16_target_error, &rg16_target_output,
            enabled_features.geometryShader, &rg16_copy) ||
        std::none_of(rg16_target_output.begin(), rg16_target_output.end(),
                     [](uint32_t pixel) {
                         return (pixel & 0x3FFFFFFFu) != 0;
                     })) {
        std::cerr << "captured Redmi 16_16_FLOAT target Copy/Convert failed: "
                  << rg16_target_error << '\n';
        return 1;
    }

    auto partial_viewport_draw = draw;
    partial_viewport_draw.topology = shift::xbox::PrimitiveTopology::PointList;
    partial_viewport_draw.index_count = 1;
    partial_viewport_draw.raster.sample_count = 1;
    partial_viewport_draw.raster.depth_test_enabled = false;
    partial_viewport_draw.raster.depth_write_enabled = false;
    partial_viewport_draw.raster.stencil_test_enabled = false;
    partial_viewport_draw.raster.viewport_x = 392.0f;
    partial_viewport_draw.raster.viewport_y = 486.0f;
    partial_viewport_draw.raster.viewport_width = 496.0f;
    partial_viewport_draw.raster.viewport_height = -8.0f;
    partial_viewport_draw.raster.scissor_x0 = 392;
    partial_viewport_draw.raster.scissor_y0 = 478;
    partial_viewport_draw.raster.scissor_x1 = 888;
    partial_viewport_draw.raster.scissor_y1 = 486;
    std::vector<uint32_t> partial_viewport_output;
    std::string partial_viewport_error;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, {partial_viewport_draw},
            &partial_viewport_error, &partial_viewport_output,
            enabled_features.geometryShader) ||
        partial_viewport_output.size() != 1280u * 720u) {
        std::cerr << "run-058 partial viewport Vulkan draw failed: "
                  << partial_viewport_error << '\n';
        return 1;
    }
    size_t partial_viewport_pixels = 0;
    for (uint32_t y = 0; y < 720; ++y) {
        for (uint32_t x = 0; x < 1280; ++x) {
            if ((partial_viewport_output[static_cast<size_t>(y) * 1280u + x] &
                 0x3FFFFFFFu) == 0) {
                continue;
            }
            ++partial_viewport_pixels;
            if (x < 392 || x >= 888 || y < 478 || y >= 486) {
                std::cerr << "run-058 viewport escaped its captured scissor at "
                          << x << ',' << y << '\n';
                return 1;
            }
        }
    }
    if (partial_viewport_pixels == 0) {
        std::cerr << "run-058 partial viewport produced no visible test pixels\n";
        return 1;
    }

    auto depth_only_draw = partial_viewport_draw;
    depth_only_draw.raster.depth_only = true;
    depth_only_draw.raster.color_write_mask = 0;
    depth_only_draw.raster.depth_control = 0x00008701u;
    depth_only_draw.raster.depth_test_enabled = false;
    depth_only_draw.raster.depth_write_enabled = false;
    depth_only_draw.raster.stencil_test_enabled = true;
    depth_only_draw.raster.stencil_refmask = 0x00FF0000u;
    std::vector<uint32_t> depth_only_output;
    std::string depth_only_error;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, {depth_only_draw},
            &depth_only_error, &depth_only_output,
            enabled_features.geometryShader) ||
        depth_only_output.size() != 1280u * 720u ||
        std::any_of(depth_only_output.begin(), depth_only_output.end(),
                    [](uint32_t pixel) { return (pixel & 0x3FFFFFFFu) != 0; })) {
        std::cerr << "run-060 depth-only Vulkan draw wrote color or failed: "
                  << depth_only_error << '\n';
        return 1;
    }

    std::vector<shift::xbox::CapturedVulkanDraw> mixed_sample_draws{
        draws[0], draws[1]};
    // The live Linux retail run changes this target from 4x MSAA/pitch 640 to
    // 1x/pitch 1280 before XE_SWAP. Keep that captured sample/pitch transition
    // in the renderer regression; the shaders and geometry here remain smoke
    // inputs and do not claim retail image parity.
    mixed_sample_draws[0].raster.color_base_tiles = 0;
    mixed_sample_draws[0].raster.depth_base_tiles = 720;
    mixed_sample_draws[0].raster.surface_pitch = 640;
    mixed_sample_draws[1].raster.sample_count = 1;
    mixed_sample_draws[1].raster.color_base_tiles = 0;
    mixed_sample_draws[1].raster.depth_base_tiles = 720;
    mixed_sample_draws[1].raster.surface_pitch = 1280;
    mixed_sample_draws[1].raster.color_format =
        shift::xbox::CapturedColorTargetFormat::Rgba8Linear;
    mixed_sample_draws[1].raster.depth_test_enabled = false;
    mixed_sample_draws[1].raster.depth_write_enabled = false;
    mixed_sample_draws[1].raster.stencil_test_enabled = false;
    std::string mixed_sample_error;
    std::vector<uint32_t> mixed_sample_output;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image, output_view,
            false, 1280, 720, mixed_sample_draws, &mixed_sample_error,
            &mixed_sample_output, enabled_features.geometryShader, &copy) ||
        mixed_sample_output.size() != 1280u * 720u) {
        std::cerr << "mixed 4x-MSAA/1x captured Copy/Convert failed: "
                  << mixed_sample_error << '\n';
        return 1;
    }
    auto mismatched_copy_extent = copy;
    mismatched_copy_extent.source_width = 1281;
    std::string mismatched_copy_error;
    if (shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image,
            output_view, false, 1280, 720, mixed_sample_draws,
            &mismatched_copy_error, nullptr,
            enabled_features.geometryShader, &mismatched_copy_extent) ||
        mismatched_copy_error.find(
            "source extent 1281x720 does not match first render target 1280x720") ==
            std::string::npos) {
        std::cerr << "mismatched mixed Copy/Convert extent was not diagnosed precisely: "
                  << mismatched_copy_error << '\n';
        return 1;
    }
    bool mixed_has_color = false;
    bool mixed_has_source_red = false;
    for (const uint32_t pixel : mixed_sample_output) {
        mixed_has_color |= (pixel & 0x3FFFFFFFu) != 0;
        mixed_has_source_red |= (pixel & 0x000003FFu) != 0;
    }
    if (!mixed_has_color || !mixed_has_source_red) {
        std::cerr << "mixed-sample Copy/Convert lost the canonical source red channel\n";
        return 1;
    }

    VkPhysicalDeviceDepthStencilResolveProperties resolve_properties{};
    resolve_properties.sType =
        VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DEPTH_STENCIL_RESOLVE_PROPERTIES;
    VkPhysicalDeviceProperties2 properties2{};
    properties2.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2;
    properties2.pNext = &resolve_properties;
    const auto get_physical_device_properties_2 =
        reinterpret_cast<PFN_vkGetPhysicalDeviceProperties2>(
            vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceProperties2"));
    if (get_physical_device_properties_2) {
        get_physical_device_properties_2(physical_device, &properties2);
    }
    const VkResolveModeFlags sample_zero = VK_RESOLVE_MODE_SAMPLE_ZERO_BIT;
    const bool can_resolve_sample_zero = depth_resolve_extensions_supported &&
        get_physical_device_properties_2 &&
        (resolve_properties.supportedDepthResolveModes & sample_zero) != 0 &&
        (resolve_properties.supportedStencilResolveModes & sample_zero) != 0;

    auto depth_preserve_draws = mixed_sample_draws;
    for (auto& depth_draw : depth_preserve_draws) {
        depth_draw.topology = shift::xbox::PrimitiveTopology::TriangleList;
        depth_draw.index_count = 3;
        depth_draw.auto_index = true;
        depth_draw.raster.blend_control_0 = 0x00010001u;
    }
    depth_preserve_draws[0].raster.depth_test_enabled = true;
    depth_preserve_draws[0].raster.depth_write_enabled = true;
    depth_preserve_draws[0].raster.stencil_test_enabled = false;
    depth_preserve_draws[0].raster.depth_control = 7u << 4;
    depth_preserve_draws[0].textures[0].pixels = {255};
    depth_preserve_draws[0].textures[1].pixels = {0, 0, 0, 255};
    depth_preserve_draws[1].raster.depth_test_enabled = true;
    depth_preserve_draws[1].raster.depth_write_enabled = false;
    depth_preserve_draws[1].raster.stencil_test_enabled = false;
    depth_preserve_draws[1].raster.depth_control = 1u << 4;
    depth_preserve_draws[1].textures[0].pixels = {0};
    depth_preserve_draws[1].textures[1].pixels = {0, 255, 0, 255};
    std::string depth_preserve_error;
    std::vector<uint32_t> depth_preserve_output;
    const bool depth_preserve_submitted =
        shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image, output_view,
            false, 1280, 720, depth_preserve_draws, &depth_preserve_error,
            &depth_preserve_output, enabled_features.geometryShader, &copy,
            can_resolve_sample_zero);
    if (can_resolve_sample_zero) {
        const uint32_t center = depth_preserve_output.size() == 1280u * 720u
            ? depth_preserve_output[360u * 1280u + 640u] : 0u;
        const uint32_t center_red = center & 0x3FFu;
        const uint32_t center_green = (center >> 10) & 0x3FFu;
        if (!depth_preserve_submitted || center_red <= center_green) {
            std::cerr << "4x-to-1x sample-zero depth resolve did not preserve the "
                         "depth test result at the triangle interior (red="
                      << center_red << ", green=" << center_green << "): "
                      << depth_preserve_error << '\n';
            return 1;
        }
    } else if (depth_preserve_submitted ||
               (depth_preserve_error.find("requires enabled") == std::string::npos &&
                depth_preserve_error.find("provider-confirmed") == std::string::npos &&
                depth_preserve_error.find("SAMPLE_ZERO") == std::string::npos)) {
        std::cerr << "unsupported depth/stencil resolve was not rejected precisely: "
                  << depth_preserve_error << '\n';
        return 1;
    }
    if (can_resolve_sample_zero) {
        std::string unconfirmed_capability_error;
        if (shift::xbox::submit_captured_vulkan_frame(
                physical_device, device, queue, queue_family, output_image,
                output_view, false, 1280, 720, depth_preserve_draws,
                &unconfirmed_capability_error, nullptr,
                enabled_features.geometryShader, &copy, false) ||
            unconfirmed_capability_error.find("provider-confirmed") ==
                std::string::npos) {
            std::cerr << "depth/stencil resolve did not fail closed when the provider "
                         "capability was unconfirmed: "
                      << unconfirmed_capability_error << '\n';
            return 1;
        }
    }

    auto stencil_preserve_draws = mixed_sample_draws;
    for (auto& stencil_draw : stencil_preserve_draws) {
        stencil_draw.topology = shift::xbox::PrimitiveTopology::TriangleList;
        stencil_draw.index_count = 3;
        stencil_draw.auto_index = true;
        stencil_draw.raster.blend_control_0 = 0x00010001u;
    }
    stencil_preserve_draws[0].raster.depth_test_enabled = false;
    stencil_preserve_draws[0].raster.depth_write_enabled = false;
    stencil_preserve_draws[0].raster.stencil_test_enabled = true;
    stencil_preserve_draws[0].raster.depth_control = (7u << 8) | (2u << 14);
    stencil_preserve_draws[0].raster.stencil_refmask = 0x00FFFF55u;
    stencil_preserve_draws[0].textures[0].pixels = {255};
    stencil_preserve_draws[0].textures[1].pixels = {0, 0, 0, 255};
    stencil_preserve_draws[1].raster.depth_test_enabled = false;
    stencil_preserve_draws[1].raster.depth_write_enabled = false;
    stencil_preserve_draws[1].raster.stencil_test_enabled = true;
    stencil_preserve_draws[1].raster.depth_control = 2u << 8;
    stencil_preserve_draws[1].raster.stencil_refmask = 0x0000FF55u;
    stencil_preserve_draws[1].textures[0].pixels = {0};
    stencil_preserve_draws[1].textures[1].pixels = {0, 255, 0, 255};
    std::string stencil_preserve_error;
    std::vector<uint32_t> stencil_preserve_output;
    const bool stencil_preserve_submitted =
        shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image, output_view,
            false, 1280, 720, stencil_preserve_draws, &stencil_preserve_error,
            &stencil_preserve_output, enabled_features.geometryShader, &copy,
            can_resolve_sample_zero);
    if (can_resolve_sample_zero) {
        const uint32_t center = stencil_preserve_output.size() == 1280u * 720u
            ? stencil_preserve_output[360u * 1280u + 640u] : 0u;
        const uint32_t center_red = center & 0x3FFu;
        const uint32_t center_green = (center >> 10) & 0x3FFu;
        if (!stencil_preserve_submitted || center_green <= center_red) {
            std::cerr << "4x-to-1x sample-zero stencil resolve did not preserve the "
                         "stencil test result at the triangle interior (red="
                      << center_red << ", green=" << center_green << "): "
                      << stencil_preserve_error << '\n';
            return 1;
        }
    } else if (stencil_preserve_submitted ||
               (stencil_preserve_error.find("requires enabled") == std::string::npos &&
                stencil_preserve_error.find("provider-confirmed") == std::string::npos &&
                stencil_preserve_error.find("SAMPLE_ZERO") == std::string::npos)) {
        std::cerr << "unsupported depth/stencil resolve was not rejected precisely: "
                  << stencil_preserve_error << '\n';
        return 1;
    }

    if (can_resolve_sample_zero) {
        auto interleaved_stencil_writer = stencil_preserve_draws[0];
        interleaved_stencil_writer.raster.color_write_mask = 0;
        interleaved_stencil_writer.raster.depth_test_enabled = false;
        interleaved_stencil_writer.raster.depth_write_enabled = false;
        interleaved_stencil_writer.raster.stencil_test_enabled = true;
        interleaved_stencil_writer.raster.depth_control = (7u << 8) | (2u << 14);
        interleaved_stencil_writer.raster.stencil_refmask = 0x00FFFF00u;
        const std::vector<shift::xbox::CapturedVulkanDraw> interleaved_stencil_draws{
            stencil_preserve_draws[0], stencil_preserve_draws[1],
            interleaved_stencil_writer, stencil_preserve_draws[1]};
        std::string interleaved_stencil_error;
        std::vector<uint32_t> interleaved_stencil_output;
        if (!shift::xbox::submit_captured_vulkan_frame(
                physical_device, device, queue, queue_family, output_image,
                output_view, false, 1280, 720, interleaved_stencil_draws,
                &interleaved_stencil_error, &interleaved_stencil_output,
                enabled_features.geometryShader, &copy, true) ||
            interleaved_stencil_output != stencil_preserve_output) {
            std::cerr << "4x stencil-only draw between 1x stencil consumers was not "
                         "replayed through the resolved sample-zero attachment: "
                      << interleaved_stencil_error << '\n';
            return 1;
        }
    }

    auto trailing_stencil_draw = mixed_sample_draws[0];
    trailing_stencil_draw.raster.sample_count = 4;
    trailing_stencil_draw.raster.surface_pitch = 640;
    trailing_stencil_draw.raster.color_format =
        shift::xbox::CapturedColorTargetFormat::Rgba8Linear;
    trailing_stencil_draw.raster.color_write_mask = 0;
    trailing_stencil_draw.raster.depth_test_enabled = false;
    trailing_stencil_draw.raster.depth_write_enabled = false;
    trailing_stencil_draw.raster.stencil_test_enabled = true;
    auto trailing_msaa_draws = mixed_sample_draws;
    trailing_msaa_draws.push_back(trailing_stencil_draw);
    std::string trailing_msaa_error;
    std::vector<uint32_t> trailing_msaa_output;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image, output_view,
            false, 1280, 720, trailing_msaa_draws, &trailing_msaa_error,
            &trailing_msaa_output, enabled_features.geometryShader, &copy) ||
        trailing_msaa_output != mixed_sample_output) {
        std::cerr << "trailing 4x stencil-only retail draw changed the copied color: "
                  << trailing_msaa_error << '\n';
        return 1;
    }

    auto final_single_sample_draw = mixed_sample_draws[1];
    auto interleaved_msaa_draws = mixed_sample_draws;
    interleaved_msaa_draws.push_back(trailing_stencil_draw);
    interleaved_msaa_draws.push_back(final_single_sample_draw);
    std::string interleaved_msaa_error;
    std::vector<uint32_t> interleaved_msaa_output;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image, output_view,
            false, 1280, 720, interleaved_msaa_draws, &interleaved_msaa_error,
            &interleaved_msaa_output, enabled_features.geometryShader, &copy) ||
        interleaved_msaa_output != mixed_sample_output) {
        std::cerr << "non-writing 4x draw between 1x draws changed the copied color: "
                  << interleaved_msaa_error << '\n';
        return 1;
    }

    trailing_stencil_draw.raster.color_write_mask = 0xFu;
    trailing_msaa_draws.back() = trailing_stencil_draw;
    std::string trailing_color_write_error;
    if (shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image, output_view,
            false, 1280, 720, trailing_msaa_draws, &trailing_color_write_error,
            nullptr, enabled_features.geometryShader, &copy) ||
        trailing_color_write_error.find(
            "returns to 4x after its 1x draws with a color/depth-writing draw") ==
            std::string::npos) {
        std::cerr << "unsupported trailing color draw was not rejected precisely: "
                  << trailing_color_write_error << '\n';
        return 1;
    }

    if (argc == 23 || argc == 24 || argc == 27 || argc == 28) {
        std::vector<uint8_t> disclaimer_texture_source;
        std::vector<uint8_t> disclaimer_texture;
        std::vector<uint8_t> expected_disclaimer_texture;
        const uint32_t disclaimer_fetch_words[6] = {
            0x840248FEu, 0x0A24B054u, 0x0000E1FFu,
            0x06A80D10u, 0x00000E43u, 0x0A24BA10u,
        };
        shift::xbox::CapturedTextureFetch disclaimer_fetch{};
        std::string disclaimer_texture_error;
        if (!read_bytes(argv[17], &disclaimer_texture_source) ||
            disclaimer_texture_source.size() != 65536u ||
            !shift::xbox::decode_captured_texture_fetch(
                disclaimer_fetch_words, &disclaimer_fetch,
                &disclaimer_texture_error) ||
            !disclaimer_fetch.packed_mips ||
            disclaimer_fetch.width != 512u || disclaimer_fetch.height != 8u ||
            !shift::xbox::untile_captured_texture_2d(
                disclaimer_fetch, disclaimer_texture_source.data(),
                disclaimer_texture_source.size(), &disclaimer_texture,
                &disclaimer_texture_error) ||
            !read_bytes(argv[18], &expected_disclaimer_texture) ||
            disclaimer_texture != expected_disclaimer_texture) {
            std::cerr << "captured disclaimer packed DXT texture decode failed: "
                      << disclaimer_texture_error << '\n';
            return 1;
        }
        shift::xbox::CapturedVulkanDraw disclaimer_draw{};
        disclaimer_draw.raster.width = 1280;
        disclaimer_draw.raster.height = 720;
        disclaimer_draw.raster.surface_pitch = 1280;
        disclaimer_draw.raster.sample_count = 1;
        disclaimer_draw.raster.color_base_tiles = 0;
        disclaimer_draw.raster.color_format =
            shift::xbox::CapturedColorTargetFormat::Rgba8Gamma;
        disclaimer_draw.raster.depth_base_tiles = 720;
        disclaimer_draw.raster.depth_format =
            shift::xbox::CapturedDepthTargetFormat::D24S8;
        disclaimer_draw.raster.color_write_mask = 0xFu;
        disclaimer_draw.raster.depth_test_enabled = true;
        disclaimer_draw.raster.depth_control = 0x12u;
        disclaimer_draw.raster.viewport_y_flipped = true;
        disclaimer_draw.raster.scissor_x0 = 0;
        disclaimer_draw.raster.scissor_y0 = 0;
        disclaimer_draw.raster.scissor_x1 = 1280;
        disclaimer_draw.raster.scissor_y1 = 720;
        disclaimer_draw.raster.scissor_has_area = true;
        disclaimer_draw.raster.blend_control_0 = 0x07060706u;
        disclaimer_draw.raster.setup_mode_control = 0x00218000u;
        disclaimer_draw.constants.vertex_float_constants[0] = {
            0x3FBB18D8u, 0, 0, 0};
        disclaimer_draw.constants.vertex_float_constants[1] = {
            0, 0x3FBB18D8u, 0, 0};
        disclaimer_draw.constants.vertex_float_constants[2] = {
            0, 0, 0x3F8020CDu, 0xBDCD0148u};
        disclaimer_draw.constants.vertex_float_constants[3] = {
            0, 0, 0x3F800000u, 0};
        disclaimer_draw.vertex_shader_spirv = disclaimer_vertex_spirv;
        disclaimer_draw.pixel_shader_spirv =
            disclaimer_encoded_fragment_spirv;
        disclaimer_draw.pixel_shader_spirv_linear_target =
            disclaimer_linear_fragment_spirv;
        disclaimer_draw.vertex_stride_bytes = 24;
        disclaimer_draw.vertex_input_attributes = {
            {0, 2, 57, 6, 0}, {1, 1, 6, 6, 3}, {2, 0, 37, 6, 4},
        };
        disclaimer_draw.topology =
            shift::xbox::PrimitiveTopology::TriangleList;
        disclaimer_draw.auto_index = true;
        disclaimer_draw.index_count = 6;
        disclaimer_draw.texture_width = 512;
        disclaimer_draw.texture_height = 8;
        disclaimer_draw.texture_sampling.swizzle = {
            shift::xbox::TextureComponent::X,
            shift::xbox::TextureComponent::Y,
            shift::xbox::TextureComponent::Z,
            shift::xbox::TextureComponent::W,
        };
        disclaimer_draw.texture_sampling.signs = {
            shift::xbox::TextureSign::Gamma,
            shift::xbox::TextureSign::Gamma,
            shift::xbox::TextureSign::Gamma,
            shift::xbox::TextureSign::Unsigned,
        };
        disclaimer_draw.texture_sampling.clamps = {
            shift::xbox::TextureClamp::ClampToEdge,
            shift::xbox::TextureClamp::ClampToEdge,
            shift::xbox::TextureClamp::ClampToEdge,
        };
        disclaimer_draw.texture_sampling.mag_filter =
            shift::xbox::TextureFilter::Linear;
        disclaimer_draw.texture_sampling.min_filter =
            shift::xbox::TextureFilter::Linear;
        disclaimer_draw.texture_sampling.mip_filter =
            shift::xbox::TextureFilter::Linear;
        disclaimer_draw.texture_sampling.anisotropy =
            shift::xbox::TextureAnisotropy::Max4To1;
        disclaimer_draw.texture_sampling.border_color =
            shift::xbox::TextureBorderColor::AbgrBlack;
        disclaimer_draw.texture_sampling.border_alpha_known = false;
        disclaimer_draw.textures.push_back({
            0, disclaimer_draw.texture_sampling, 512, 8,
            shift::xbox::CapturedVulkanTexture::Format::Rgba8,
            disclaimer_texture});
        std::vector<shift::xbox::CapturedVulkanDraw> disclaimer_draws;
        disclaimer_draws.reserve(4);
        for (int i = 0; i < 4; ++i) {
            auto captured_draw = disclaimer_draw;
            if (!read_bytes(argv[19 + i], &captured_draw.vertices) ||
                captured_draw.vertices.size() != 6u * 24u) {
                std::cerr << "captured disclaimer vertex fixture is missing or malformed\n";
                return 1;
            }
            disclaimer_draws.push_back(std::move(captured_draw));
        }
        auto disclaimer_copy = copy;
        disclaimer_copy.source_gamma = true;
        disclaimer_copy.gamma_single_sample_pixel_shader_spirv =
            gamma_copy_single_fragment_spirv;
        disclaimer_copy.gamma_pixel_shader_spirv =
            gamma_copy_ms_fragment_spirv;
        std::vector<uint32_t> disclaimer_output;
        std::string disclaimer_error;
        if (!shift::xbox::submit_captured_vulkan_frame(
                physical_device, device, queue, queue_family, output_image,
                output_view, false, 1280, 720, disclaimer_draws,
                &disclaimer_error, &disclaimer_output,
                enabled_features.geometryShader, &disclaimer_copy, false,
                sampler_capabilities, pipeline_cache, &texture_cache) ||
            disclaimer_output.size() != 1280u * 720u) {
            std::cerr << "captured disclaimer frame replay failed: "
                      << disclaimer_error << '\n';
            return 1;
        }
        size_t upper_strip_pixels = 0;
        size_t lower_strip_pixels = 0;
        for (uint32_t y = 0; y < 720; ++y) {
            for (uint32_t x = 0; x < 1280; ++x) {
                if ((disclaimer_output[static_cast<size_t>(y) * 1280 + x] &
                     0x3FFFFFFFu) == 0) {
                    continue;
                }
                if (y >= 175 && y < 205) ++upper_strip_pixels;
                if (y >= 515 && y < 550) ++lower_strip_pixels;
            }
        }
        if (upper_strip_pixels < 100 || lower_strip_pixels < 100) {
            std::cerr << "captured disclaimer strips lost visible output: top="
                      << upper_strip_pixels << " bottom=" << lower_strip_pixels
                      << '\n';
            return 1;
        }
        for (uint32_t y : {187u, 541u}) {
            for (uint32_t x = 185u; x < 1095u; ++x) {
                if ((disclaimer_output[static_cast<size_t>(y) * 1280 + x] &
                     0x3FFFFFFFu) == 0) {
                    std::cerr << "captured disclaimer packed border has a gap at "
                              << x << ',' << y << '\n';
                    return 1;
                }
            }
        }
        if (const char* output_path = std::getenv(
                "SHIFT_VULKAN_DISCLAIMER_REPLAY_RAW_OUT")) {
            std::ofstream output(output_path, std::ios::binary);
            output.write(reinterpret_cast<const char*>(disclaimer_output.data()),
                         static_cast<std::streamsize>(disclaimer_output.size() *
                                                      sizeof(uint32_t)));
            if (!output) {
                std::cerr << "could not write captured disclaimer replay output\n";
                return 1;
            }
        }
        std::cout << "captured retail disclaimer strip draws passed on "
                  << device_properties.deviceName << '\n';
    }

    std::vector<shift::xbox::CapturedVulkanDraw> reverse_sample_draws{
        draws[0], draws[1]};
    reverse_sample_draws[0].raster.sample_count = 1;
    reverse_sample_draws[1].raster.sample_count = 4;
    std::string reverse_sample_error;
    if (shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image, output_view,
            false, 1280, 720, reverse_sample_draws, &reverse_sample_error, nullptr,
            enabled_features.geometryShader, &copy) ||
        reverse_sample_error.find(
            "mixed captured frame requires 4x-MSAA followed by 1x") ==
            std::string::npos) {
        std::cerr << "unsupported reverse sample transition was not rejected precisely: "
                  << reverse_sample_error << '\n';
        return 1;
    }

    auto invalid_scissor_draws = draws;
    invalid_scissor_draws[0].raster.scissor_x1 = 1281;
    std::string invalid_scissor_error;
    if (shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image, output_view,
            false, 1280, 720, invalid_scissor_draws, &invalid_scissor_error, nullptr,
            enabled_features.geometryShader) ||
        invalid_scissor_error.find(
            "draw 0 scissor [0,0,1281,720] is outside raster extent 1280x720") ==
            std::string::npos) {
        std::cerr << "invalid scissor rejection did not identify the incompatible draw: "
                  << invalid_scissor_error << '\n';
        return 1;
    }

    bool has_color = false;
    bool has_source_red = false;
    bool has_source_green = false;
    size_t colored_pixels = 0;
    for (const uint32_t pixel : output_readback) {
        if (pixel & 0x3FFFFFFFu) {
          has_color = true;
          ++colored_pixels;
        }
        if (pixel & 0x000003FFu)
          has_source_red = true;
        if (pixel & 0x000FFC00u)
          has_source_green = true;
    }
    guest_copy_cache.clear();
    if (guest_copy_cache.cached_guest_copy_image_count() != 0) {
      std::cerr << "clearing guest Copy/Convert cache retained destination images\n";
      return 1;
    }
    texture_cache.clear();
    if (texture_cache.cached_pipeline_count() != 0 ||
        texture_cache.cached_sampler_count() != 0 ||
        texture_cache.cached_descriptor_layout_count() != 0 ||
        texture_cache.descriptor_layout_cache_hits() != 0) {
      std::cerr << "clearing texture cache retained GPU objects\n";
      return 1;
    }
    vkDestroyImageView(device, output_view, nullptr);
    vkDestroyImage(device, output_image, nullptr);
    vkFreeMemory(device, output_memory, nullptr);
    vkDestroyPipelineCache(device, pipeline_cache, nullptr);
    vkDestroyDevice(device, nullptr);
    if (messenger) {
      auto destroy_messenger =
          reinterpret_cast<PFN_vkDestroyDebugUtilsMessengerEXT>(
              vkGetInstanceProcAddr(instance,
                                    "vkDestroyDebugUtilsMessengerEXT"));
      if (destroy_messenger)
        destroy_messenger(instance, messenger, nullptr);
    }
    vkDestroyInstance(instance, nullptr);

    if (!has_color) {
        std::cerr << "Vulkan sample-zero Copy/Convert produced no non-black pixels\n";
        return 1;
    }
    if (!has_source_red) {
        std::cerr << "Vulkan Copy/Convert lost the canonical source red channel\n";
        return 1;
    }
    if (!has_source_green) {
        std::cerr << "Vulkan draw did not sample the second texture binding\n";
        return 1;
    }
    if (enabled_features.geometryShader && colored_pixels < 100) {
        std::cerr << "Vulkan rectangle-list draw produced too few colored pixels: "
                  << colored_pixels << '\n';
        return 1;
    }
    if (validation_errors != 0) {
        std::cerr << validation_errors << " Vulkan validation errors\n";
        return 1;
    }
    if (output_readback.size() != 1280u * 720u) {
        std::cerr << "Vulkan output readback has the wrong pixel count\n";
        return 1;
    }
    std::cout << "synthetic offscreen Vulkan 1.1 AutoIndex point"
              << (enabled_features.geometryShader ? " and rectangle-list" : "")
              << " draw"
              << (can_resolve_sample_zero
                      ? " plus 4x-to-1x depth/stencil SAMPLE_ZERO preservation"
                      : " with depth/stencil resolve fail-closed")
              << (anisotropy_sampler_path_ran ? " and 4:1 anisotropy sampler"
                                             : " with anisotropy fallback")
              << " with R16G16_SFLOAT target and captured sample-zero "
                 "Copy/Convert plus synthetic format-26 all-sample and "
                 "format-31 sample-zero conversions"
              << (has_copy_destination_shaders
                      ? " plus ordered format-31 Copy-to-texture cache sampling"
                      : "")
              << " passed on "
              << device_properties.deviceName
              << (use_validation ? " with validation enabled\n" : "\n");
    return 0;
}
