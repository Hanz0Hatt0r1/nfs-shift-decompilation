#include "shift_xbox_live_vulkan_renderer.hpp"

#include <vulkan/vulkan.h>

#include <algorithm>
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
    if (argc != 9) {
        std::cerr << "usage: xbox_live_vulkan_renderer_check vertex.spv fragment.spv "
                     "geometry.spv copy-vertex.spv copy-fragment.spv "
                     "copy-single-fragment.spv window-vertex.spv window-fragment.spv\n";
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

    std::vector<shift::xbox::CapturedVulkanDraw> draws;
    draws.push_back(draw);
    auto captured_alpha_blend = draw;
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
        physical_device, device, queue, queue_family, output_image, output_view, false,
        1280, 720, draws, &error, &output_readback,
        enabled_features.geometryShader, &copy, false, {}, pipeline_cache);
    if (!submitted) {
        std::cerr << "captured Vulkan draw submission failed: " << error << '\n';
        return 1;
    }
    const std::vector<uint32_t> cached_output = output_readback;
    std::vector<uint32_t> repeated_cached_output;
    if (!shift::xbox::submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family, output_image, output_view,
            false, 1280, 720, draws, &error, &repeated_cached_output,
            enabled_features.geometryShader, &copy, false, {}, pipeline_cache) ||
        repeated_cached_output != cached_output) {
        std::cerr << "reused Vulkan pipeline cache changed captured draw output: "
                  << error << '\n';
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
        if (pixel & 0x000003FFu) has_source_red = true;
        if (pixel & 0x000FFC00u) has_source_green = true;
    }
    vkDestroyImageView(device, output_view, nullptr);
    vkDestroyImage(device, output_image, nullptr);
    vkFreeMemory(device, output_memory, nullptr);
    vkDestroyPipelineCache(device, pipeline_cache, nullptr);
    vkDestroyDevice(device, nullptr);
    if (messenger) {
        auto destroy_messenger = reinterpret_cast<PFN_vkDestroyDebugUtilsMessengerEXT>(
            vkGetInstanceProcAddr(instance, "vkDestroyDebugUtilsMessengerEXT"));
        if (destroy_messenger) destroy_messenger(instance, messenger, nullptr);
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
              << " and captured sample-zero Copy/Convert passed on "
              << device_properties.deviceName
              << (use_validation ? " with validation enabled\n" : "\n");
    return 0;
}
