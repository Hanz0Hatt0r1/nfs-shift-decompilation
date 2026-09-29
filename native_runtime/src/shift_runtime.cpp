#include <vulkan/vulkan.h>
#include <xcb/xcb.h>

#include "shift_ir.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr uint32_t kWindowWidth = 1280;
constexpr uint32_t kWindowHeight = 720;
constexpr int kDefaultFrames = 120;
constexpr size_t kFramesInFlight = 2;

#pragma pack(push, 1)
struct GeometryHeader {
    char magic[4];
    uint32_t version;
    uint32_t vertex_count;
    uint32_t index_count;
    uint32_t stride;
    uint32_t attribute_count;
    uint32_t first_index;
    float center_x;
    float center_y;
    float center_z;
    float scale;
};
struct GeometryAttribute {
    uint32_t location;
    uint32_t format;
    uint32_t offset;
    uint32_t stride;
};
#pragma pack(pop)

static_assert(sizeof(GeometryHeader) == 44);
static_assert(sizeof(GeometryAttribute) == 16);

struct PacketGeometry {
    std::vector<float> positions;
    std::vector<uint32_t> indices;
    uint32_t first_index = 0;
    std::string source = "MGEO";
};


void vk_check(VkResult result, const char* message) {
    if (result != VK_SUCCESS) {
        throw std::runtime_error(
            std::string(message) + " (VkResult=" +
            std::to_string(static_cast<int>(result)) + ")");
    }
}

uint32_t find_memory_type(
    VkPhysicalDevice physical,
    uint32_t type_bits,
    VkMemoryPropertyFlags required) {

    VkPhysicalDeviceMemoryProperties props{};
    vkGetPhysicalDeviceMemoryProperties(physical, &props);
    for (uint32_t i = 0; i < props.memoryTypeCount; ++i) {
        if ((type_bits & (1u << i)) != 0u &&
            (props.memoryTypes[i].propertyFlags & required) == required) {
            return i;
        }
    }
    throw std::runtime_error("no compatible Vulkan memory type");
}

std::vector<uint32_t> read_spirv(const std::string& path) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file) throw std::runtime_error("cannot open SPIR-V: " + path);
    const std::streamsize size = file.tellg();
    if (size <= 0 || size % static_cast<std::streamsize>(sizeof(uint32_t)) != 0) {
        throw std::runtime_error("invalid SPIR-V size: " + path);
    }
    file.seekg(0);
    std::vector<uint32_t> code(static_cast<size_t>(size) / sizeof(uint32_t));
    if (!file.read(reinterpret_cast<char*>(code.data()), size)) {
        throw std::runtime_error("cannot read SPIR-V: " + path);
    }
    return code;
}


std::vector<uint8_t> read_file_bytes(const std::string& path) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file) throw std::runtime_error("cannot open file: " + path);
    const std::streamsize size = file.tellg();
    if (size <= 0) throw std::runtime_error("empty file: " + path);
    file.seekg(0);
    std::vector<uint8_t> data(static_cast<size_t>(size));
    if (!file.read(reinterpret_cast<char*>(data.data()), size)) {
        throw std::runtime_error("cannot read file: " + path);
    }
    return data;
}

bool file_contains(const std::string& path, const std::string& needle) {
    std::ifstream file(path, std::ios::binary);
    if (!file) return false;
    const std::string contents(
        (std::istreambuf_iterator<char>(file)),
        std::istreambuf_iterator<char>());
    return contents.find(needle) != std::string::npos;
}

PacketGeometry load_bundle_geometry(const std::string& root) {
    const std::string manifest = root + "/bundle_manifest.json";
    const std::string gate = root + "/native_submission_gate.json";
    if (!file_contains(manifest, "\"format\": \"SHIFT.BMWVulkanBundle/1\"")) {
        throw std::runtime_error("bundle manifest is not SHIFT.BMWVulkanBundle/1");
    }
    if (!file_contains(gate, "\"format\": \"SHIFT.NativeSubmissionGate/1\"") ||
        !file_contains(gate, "\"ready\": true") ||
        !file_contains(gate, "\"blocking_reasons\": []")) {
        throw std::runtime_error("native submission gate is missing or not ready");
    }

    const auto data = read_file_bytes(root + "/geometry.svpk");
    if (data.size() < sizeof(GeometryHeader)) {
        throw std::runtime_error("geometry packet truncated");
    }

    GeometryHeader header{};
    std::memcpy(&header, data.data(), sizeof(header));
    if (std::memcmp(header.magic, "SVGP", 4) != 0 ||
        (header.version != 1 && header.version != 2)) {
        throw std::runtime_error("unsupported SVGP geometry packet");
    }
    if (header.vertex_count == 0 || header.index_count == 0 ||
        header.stride == 0 || header.attribute_count == 0 ||
        header.attribute_count > 16 || header.index_count % 3 != 0) {
        throw std::runtime_error("invalid SVGP geometry header");
    }

    const size_t attributes_bytes =
        static_cast<size_t>(header.attribute_count) * sizeof(GeometryAttribute);
    const size_t vertices_bytes =
        static_cast<size_t>(header.vertex_count) * header.stride;
    const size_t indices_bytes =
        static_cast<size_t>(header.index_count) * sizeof(uint32_t);
    const size_t expected =
        sizeof(GeometryHeader) + attributes_bytes +
        vertices_bytes + indices_bytes;
    if (expected != data.size()) {
        throw std::runtime_error("SVGP geometry packet size mismatch");
    }

    std::vector<GeometryAttribute> attributes(header.attribute_count);
    std::memcpy(
        attributes.data(), data.data() + sizeof(GeometryHeader),
        attributes_bytes);

    const GeometryAttribute* position = nullptr;
    for (const auto& attribute : attributes) {
        if (attribute.location == 0) {
            position = &attribute;
            break;
        }
    }
    if (!position || position->format != 2 ||
        position->stride != header.stride ||
        position->offset + sizeof(float) * 3 > header.stride) {
        throw std::runtime_error("SVGP POSITION0 is not FLOAT3");
    }

    const size_t vertex_base = sizeof(GeometryHeader) + attributes_bytes;
    const size_t index_base = vertex_base + vertices_bytes;

    PacketGeometry out;
    out.source = "SHIFT.BMWVulkanBundle/1";
    out.first_index = header.first_index;
    out.positions.resize(static_cast<size_t>(header.vertex_count) * 3u);
    for (uint32_t vertex = 0; vertex < header.vertex_count; ++vertex) {
        const uint8_t* src =
            data.data() + vertex_base +
            static_cast<size_t>(vertex) * header.stride +
            position->offset;
        std::memcpy(
            out.positions.data() + static_cast<size_t>(vertex) * 3u,
            src, sizeof(float) * 3u);
    }

    out.indices.resize(header.index_count);
    std::memcpy(
        out.indices.data(), data.data() + index_base, indices_bytes);
    for (uint32_t index : out.indices) {
        if (index >= header.vertex_count) {
            throw std::runtime_error("SVGP index out of range");
        }
    }
    return out;
}

struct Window {
    xcb_connection_t* connection = nullptr;
    xcb_window_t window = XCB_WINDOW_NONE;

    void create() {
        int screen_index = 0;
        connection = xcb_connect(nullptr, &screen_index);
        if (!connection || xcb_connection_has_error(connection)) {
            throw std::runtime_error("cannot connect to X11");
        }

        const xcb_setup_t* setup = xcb_get_setup(connection);
        auto screen_it = xcb_setup_roots_iterator(setup);
        for (int i = 0; i < screen_index && screen_it.rem; ++i) {
            xcb_screen_next(&screen_it);
        }
        if (!screen_it.rem) {
            throw std::runtime_error("cannot find X11 screen");
        }

        const xcb_screen_t* screen = screen_it.data;
        window = xcb_generate_id(connection);

        const uint32_t event_mask =
            XCB_EVENT_MASK_EXPOSURE |
            XCB_EVENT_MASK_STRUCTURE_NOTIFY |
            XCB_EVENT_MASK_KEY_PRESS;

        const uint32_t values[] = {
            screen->black_pixel,
            event_mask
        };

        xcb_create_window(
            connection,
            XCB_COPY_FROM_PARENT,
            window,
            screen->root,
            0, 0,
            kWindowWidth, kWindowHeight,
            0,
            XCB_WINDOW_CLASS_INPUT_OUTPUT,
            screen->root_visual,
            XCB_CW_BACK_PIXEL | XCB_CW_EVENT_MASK,
            values);

        const char title[] = "SHIFT Linux Test Runtime";
        xcb_change_property(
            connection,
            XCB_PROP_MODE_REPLACE,
            window,
            XCB_ATOM_WM_NAME,
            XCB_ATOM_STRING,
            8,
            static_cast<uint32_t>(sizeof(title) - 1),
            title);

        xcb_map_window(connection, window);
        xcb_flush(connection);
    }

    void poll(bool& quit) {
        while (xcb_generic_event_t* raw = xcb_poll_for_event(connection)) {
            const uint8_t type = raw->response_type & 0x7f;
            if (type == XCB_KEY_PRESS) {
                const auto* event =
                    reinterpret_cast<const xcb_key_press_event_t*>(raw);
                if (event->detail == 9 || event->detail == 24) {
                    quit = true;
                }
            } else if (type == XCB_DESTROY_NOTIFY) {
                quit = true;
            }
            std::free(raw);
        }
    }

    void destroy() {
        if (!connection) return;
        if (window != XCB_WINDOW_NONE) {
            xcb_destroy_window(connection, window);
        }
        xcb_disconnect(connection);
        connection = nullptr;
        window = XCB_WINDOW_NONE;
    }
};

struct Buffer {
    VkDevice device = VK_NULL_HANDLE;
    VkBuffer handle = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;

    void destroy() {
        if (device != VK_NULL_HANDLE) {
            if (handle) vkDestroyBuffer(device, handle, nullptr);
            if (memory) vkFreeMemory(device, memory, nullptr);
        }
        device = VK_NULL_HANDLE;
        handle = VK_NULL_HANDLE;
        memory = VK_NULL_HANDLE;
    }
};

struct Runtime {
    Window* window = nullptr;

    VkInstance instance = VK_NULL_HANDLE;
    VkSurfaceKHR surface = VK_NULL_HANDLE;
    VkPhysicalDevice physical = VK_NULL_HANDLE;
    VkDevice device = VK_NULL_HANDLE;
    VkQueue graphics_queue = VK_NULL_HANDLE;
    VkQueue present_queue = VK_NULL_HANDLE;
    uint32_t graphics_family = 0;
    uint32_t present_family = 0;

    VkSwapchainKHR swapchain = VK_NULL_HANDLE;
    VkFormat swapchain_format = VK_FORMAT_UNDEFINED;
    VkExtent2D swapchain_extent{};
    std::vector<VkImage> swapchain_images;
    std::vector<VkImageView> swapchain_views;

    VkRenderPass render_pass = VK_NULL_HANDLE;
    VkPipelineLayout pipeline_layout = VK_NULL_HANDLE;
    VkPipeline pipeline = VK_NULL_HANDLE;
    VkShaderModule vertex_shader = VK_NULL_HANDLE;
    VkShaderModule fragment_shader = VK_NULL_HANDLE;
    std::vector<VkFramebuffer> framebuffers;

    VkCommandPool command_pool = VK_NULL_HANDLE;
    std::vector<VkCommandBuffer> command_buffers;

    std::array<VkSemaphore, kFramesInFlight> image_available{};
    std::array<VkSemaphore, kFramesInFlight> render_finished{};
    std::array<VkFence, kFramesInFlight> fences{};
    size_t frame_slot = 0;

    Buffer vertex_buffer;
    Buffer index_buffer;
    uint32_t index_count = 0;

    void create_instance() {
        const char* extensions[] = {
            VK_KHR_SURFACE_EXTENSION_NAME,
            VK_KHR_XCB_SURFACE_EXTENSION_NAME
        };

        VkApplicationInfo app{};
        app.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
        app.pApplicationName = "Need for Speed: SHIFT Linux Test Runtime";
        app.applicationVersion = 1;
        app.pEngineName = "SHIFT";
        app.engineVersion = 1;
        app.apiVersion = VK_API_VERSION_1_0;

        VkInstanceCreateInfo create{};
        create.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
        create.pApplicationInfo = &app;
        create.enabledExtensionCount = 2;
        create.ppEnabledExtensionNames = extensions;

        vk_check(vkCreateInstance(&create, nullptr, &instance),
                 "vkCreateInstance failed");
    }

    void create_surface() {
        VkXcbSurfaceCreateInfoKHR create{};
        create.sType = VK_STRUCTURE_TYPE_XCB_SURFACE_CREATE_INFO_KHR;
        create.connection = window->connection;
        create.window = window->window;

        vk_check(vkCreateXcbSurfaceKHR(
                     instance, &create, nullptr, &surface),
                 "vkCreateXcbSurfaceKHR failed");
    }

    bool pick_queue_families(VkPhysicalDevice candidate) {
        uint32_t count = 0;
        vkGetPhysicalDeviceQueueFamilyProperties(candidate, &count, nullptr);
        std::vector<VkQueueFamilyProperties> families(count);
        vkGetPhysicalDeviceQueueFamilyProperties(
            candidate, &count, families.data());

        int graphics = -1;
        int present = -1;
        for (uint32_t i = 0; i < count; ++i) {
            if ((families[i].queueFlags & VK_QUEUE_GRAPHICS_BIT) != 0u &&
                graphics < 0) {
                graphics = static_cast<int>(i);
            }

            VkBool32 supports_present = VK_FALSE;
            vk_check(vkGetPhysicalDeviceSurfaceSupportKHR(
                         candidate, i, surface, &supports_present),
                     "vkGetPhysicalDeviceSurfaceSupportKHR failed");
            if (supports_present == VK_TRUE && present < 0) {
                present = static_cast<int>(i);
            }
        }

        if (graphics < 0 || present < 0) return false;
        graphics_family = static_cast<uint32_t>(graphics);
        present_family = static_cast<uint32_t>(present);
        return true;
    }

    void create_device() {
        uint32_t count = 0;
        vk_check(vkEnumeratePhysicalDevices(
                     instance, &count, nullptr),
                 "vkEnumeratePhysicalDevices(count) failed");
        if (count == 0) throw std::runtime_error("no Vulkan physical devices");

        std::vector<VkPhysicalDevice> devices(count);
        vk_check(vkEnumeratePhysicalDevices(
                     instance, &count, devices.data()),
                 "vkEnumeratePhysicalDevices(data) failed");

        for (VkPhysicalDevice candidate : devices) {
            if (pick_queue_families(candidate)) {
                physical = candidate;
                break;
            }
        }
        if (!physical) {
            throw std::runtime_error(
                "no Vulkan device supports graphics + XCB presentation");
        }

        const float priority = 1.0f;
        std::array<VkDeviceQueueCreateInfo, 2> queue_infos{};
        queue_infos[0].sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
        queue_infos[0].queueFamilyIndex = graphics_family;
        queue_infos[0].queueCount = 1;
        queue_infos[0].pQueuePriorities = &priority;

        uint32_t queue_count = 1;
        if (present_family != graphics_family) {
            queue_infos[1] = queue_infos[0];
            queue_infos[1].queueFamilyIndex = present_family;
            queue_count = 2;
        }

        const char* device_extensions[] = {
            VK_KHR_SWAPCHAIN_EXTENSION_NAME
        };

        VkDeviceCreateInfo create{};
        create.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
        create.queueCreateInfoCount = queue_count;
        create.pQueueCreateInfos = queue_infos.data();
        create.enabledExtensionCount = 1;
        create.ppEnabledExtensionNames = device_extensions;

        vk_check(vkCreateDevice(
                     physical, &create, nullptr, &device),
                 "vkCreateDevice failed");

        vkGetDeviceQueue(
            device, graphics_family, 0, &graphics_queue);
        vkGetDeviceQueue(
            device, present_family, 0, &present_queue);
    }

    void create_swapchain() {
        VkSurfaceCapabilitiesKHR caps{};
        vk_check(vkGetPhysicalDeviceSurfaceCapabilitiesKHR(
                     physical, surface, &caps),
                 "surface capabilities failed");

        uint32_t format_count = 0;
        vk_check(vkGetPhysicalDeviceSurfaceFormatsKHR(
                     physical, surface, &format_count, nullptr),
                 "surface formats failed");
        if (format_count == 0) throw std::runtime_error("no Vulkan surface formats");

        std::vector<VkSurfaceFormatKHR> formats(format_count);
        vk_check(vkGetPhysicalDeviceSurfaceFormatsKHR(
                     physical, surface, &format_count, formats.data()),
                 "surface formats failed");

        VkSurfaceFormatKHR chosen = formats.front();
        for (const auto& format : formats) {
            if (format.format == VK_FORMAT_B8G8R8A8_UNORM &&
                format.colorSpace == VK_COLOR_SPACE_SRGB_NONLINEAR_KHR) {
                chosen = format;
                break;
            }
        }
        swapchain_format = chosen.format;

        swapchain_extent = caps.currentExtent;
        if (swapchain_extent.width == std::numeric_limits<uint32_t>::max()) {
            swapchain_extent = {
                std::clamp(kWindowWidth, caps.minImageExtent.width,
                           caps.maxImageExtent.width),
                std::clamp(kWindowHeight, caps.minImageExtent.height,
                           caps.maxImageExtent.height)
            };
        }

        uint32_t image_count = caps.minImageCount + 1;
        if (caps.maxImageCount != 0) {
            image_count = std::min(image_count, caps.maxImageCount);
        }

        VkSwapchainCreateInfoKHR create{};
        create.sType = VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR;
        create.surface = surface;
        create.minImageCount = image_count;
        create.imageFormat = chosen.format;
        create.imageColorSpace = chosen.colorSpace;
        create.imageExtent = swapchain_extent;
        create.imageArrayLayers = 1;
        create.imageUsage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT;
        if (graphics_family != present_family) {
            const uint32_t families[] = {graphics_family, present_family};
            create.imageSharingMode = VK_SHARING_MODE_CONCURRENT;
            create.queueFamilyIndexCount = 2;
            create.pQueueFamilyIndices = families;
        } else {
            create.imageSharingMode = VK_SHARING_MODE_EXCLUSIVE;
        }
        create.preTransform = caps.currentTransform;
        create.compositeAlpha = VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR;
        create.presentMode = VK_PRESENT_MODE_FIFO_KHR;
        create.clipped = VK_TRUE;

        vk_check(vkCreateSwapchainKHR(
                     device, &create, nullptr, &swapchain),
                 "vkCreateSwapchainKHR failed");

        vk_check(vkGetSwapchainImagesKHR(
                     device, swapchain, &image_count, nullptr),
                 "vkGetSwapchainImagesKHR(count) failed");
        swapchain_images.resize(image_count);
        vk_check(vkGetSwapchainImagesKHR(
                     device, swapchain, &image_count, swapchain_images.data()),
                 "vkGetSwapchainImagesKHR(data) failed");

        swapchain_views.resize(swapchain_images.size());
        for (size_t i = 0; i < swapchain_images.size(); ++i) {
            VkImageViewCreateInfo view{};
            view.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
            view.image = swapchain_images[i];
            view.viewType = VK_IMAGE_VIEW_TYPE_2D;
            view.format = swapchain_format;
            view.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
            view.subresourceRange.baseMipLevel = 0;
            view.subresourceRange.levelCount = 1;
            view.subresourceRange.baseArrayLayer = 0;
            view.subresourceRange.layerCount = 1;
            vk_check(vkCreateImageView(
                         device, &view, nullptr, &swapchain_views[i]),
                     "vkCreateImageView failed");
        }
    }

    VkShaderModule load_shader(const std::string& path) {
        const auto code = read_spirv(path);
        VkShaderModuleCreateInfo create{};
        create.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
        create.codeSize = code.size() * sizeof(uint32_t);
        create.pCode = code.data();

        VkShaderModule module = VK_NULL_HANDLE;
        vk_check(vkCreateShaderModule(
                     device, &create, nullptr, &module),
                 "vkCreateShaderModule failed");
        return module;
    }

    void create_pipeline(const std::string& shader_dir) {
        vertex_shader =
            load_shader(shader_dir + "/runtime.vert.spv");
        fragment_shader =
            load_shader(shader_dir + "/runtime.frag.spv");

        VkAttachmentDescription color{};
        color.format = swapchain_format;
        color.samples = VK_SAMPLE_COUNT_1_BIT;
        color.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
        color.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
        color.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        color.finalLayout = VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;

        VkAttachmentReference color_ref{};
        color_ref.attachment = 0;
        color_ref.layout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;

        VkSubpassDescription subpass{};
        subpass.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
        subpass.colorAttachmentCount = 1;
        subpass.pColorAttachments = &color_ref;

        VkSubpassDependency dependency{};
        dependency.srcSubpass = VK_SUBPASS_EXTERNAL;
        dependency.dstSubpass = 0;
        dependency.srcStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
        dependency.dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
        dependency.dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;

        VkRenderPassCreateInfo pass{};
        pass.sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
        pass.attachmentCount = 1;
        pass.pAttachments = &color;
        pass.subpassCount = 1;
        pass.pSubpasses = &subpass;
        pass.dependencyCount = 1;
        pass.pDependencies = &dependency;
        vk_check(vkCreateRenderPass(
                     device, &pass, nullptr, &render_pass),
                 "vkCreateRenderPass failed");

        VkPushConstantRange push{};
        push.stageFlags = VK_SHADER_STAGE_VERTEX_BIT;
        push.offset = 0;
        push.size = sizeof(float) * 16;

        VkPipelineLayoutCreateInfo layout{};
        layout.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
        layout.pushConstantRangeCount = 1;
        layout.pPushConstantRanges = &push;
        vk_check(vkCreatePipelineLayout(
                     device, &layout, nullptr, &pipeline_layout),
                 "vkCreatePipelineLayout failed");

        VkPipelineShaderStageCreateInfo stages[2]{};
        stages[0].sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module = vertex_shader;
        stages[0].pName = "main";
        stages[1].sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module = fragment_shader;
        stages[1].pName = "main";

        VkVertexInputBindingDescription binding{};
        binding.binding = 0;
        binding.stride = sizeof(float) * 3;
        binding.inputRate = VK_VERTEX_INPUT_RATE_VERTEX;

        VkVertexInputAttributeDescription attribute{};
        attribute.location = 0;
        attribute.binding = 0;
        attribute.format = VK_FORMAT_R32G32B32_SFLOAT;
        attribute.offset = 0;

        VkPipelineVertexInputStateCreateInfo vertex_input{};
        vertex_input.sType =
            VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO;
        vertex_input.vertexBindingDescriptionCount = 1;
        vertex_input.pVertexBindingDescriptions = &binding;
        vertex_input.vertexAttributeDescriptionCount = 1;
        vertex_input.pVertexAttributeDescriptions = &attribute;

        VkPipelineInputAssemblyStateCreateInfo assembly{};
        assembly.sType =
            VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO;
        assembly.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;

        VkViewport viewport{};
        viewport.width = static_cast<float>(swapchain_extent.width);
        viewport.height = static_cast<float>(swapchain_extent.height);
        viewport.maxDepth = 1.0f;

        VkRect2D scissor{};
        scissor.extent = swapchain_extent;

        VkPipelineViewportStateCreateInfo viewport_state{};
        viewport_state.sType =
            VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO;
        viewport_state.viewportCount = 1;
        viewport_state.pViewports = &viewport;
        viewport_state.scissorCount = 1;
        viewport_state.pScissors = &scissor;

        VkPipelineRasterizationStateCreateInfo raster{};
        raster.sType =
            VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO;
        raster.polygonMode = VK_POLYGON_MODE_FILL;
        raster.cullMode = VK_CULL_MODE_BACK_BIT;
        raster.frontFace = VK_FRONT_FACE_COUNTER_CLOCKWISE;
        raster.lineWidth = 1.0f;

        VkPipelineMultisampleStateCreateInfo multisample{};
        multisample.sType =
            VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO;
        multisample.rasterizationSamples = VK_SAMPLE_COUNT_1_BIT;

        VkPipelineColorBlendAttachmentState color_blend{};
        color_blend.colorWriteMask =
            VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
            VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT;

        VkPipelineColorBlendStateCreateInfo blend{};
        blend.sType = VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO;
        blend.attachmentCount = 1;
        blend.pAttachments = &color_blend;

        VkGraphicsPipelineCreateInfo create{};
        create.sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO;
        create.stageCount = 2;
        create.pStages = stages;
        create.pVertexInputState = &vertex_input;
        create.pInputAssemblyState = &assembly;
        create.pViewportState = &viewport_state;
        create.pRasterizationState = &raster;
        create.pMultisampleState = &multisample;
        create.pColorBlendState = &blend;
        create.layout = pipeline_layout;
        create.renderPass = render_pass;
        create.subpass = 0;

        vk_check(vkCreateGraphicsPipelines(
                     device, VK_NULL_HANDLE, 1, &create, nullptr, &pipeline),
                 "vkCreateGraphicsPipelines failed");
    }

    void create_buffer(
        const void* data, VkDeviceSize size,
        VkBufferUsageFlags usage, Buffer& out) {

        VkBufferCreateInfo create{};
        create.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
        create.size = size;
        create.usage = usage;
        create.sharingMode = VK_SHARING_MODE_EXCLUSIVE;

        vk_check(vkCreateBuffer(
                     device, &create, nullptr, &out.handle),
                 "vkCreateBuffer failed");
        out.device = device;

        VkMemoryRequirements requirements{};
        vkGetBufferMemoryRequirements(
            device, out.handle, &requirements);

        VkMemoryAllocateInfo allocate{};
        allocate.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
        allocate.allocationSize = requirements.size;
        allocate.memoryTypeIndex = find_memory_type(
            physical, requirements.memoryTypeBits,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
            VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);

        vk_check(vkAllocateMemory(
                     device, &allocate, nullptr, &out.memory),
                 "vkAllocateMemory failed");
        vk_check(vkBindBufferMemory(
                     device, out.handle, out.memory, 0),
                 "vkBindBufferMemory failed");

        void* mapped = nullptr;
        vk_check(vkMapMemory(
                     device, out.memory, 0, size, 0, &mapped),
                 "vkMapMemory failed");
        std::memcpy(mapped, data, static_cast<size_t>(size));
        vkUnmapMemory(device, out.memory);
    }

    void create_geometry(const PacketGeometry& geometry) {
        if (geometry.positions.empty() || geometry.indices.empty()) {
            throw std::runtime_error("runtime geometry has no drawable data");
        }
        create_buffer(
            geometry.positions.data(),
            static_cast<VkDeviceSize>(geometry.positions.size() * sizeof(float)),
            VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
            vertex_buffer);
        create_buffer(
            geometry.indices.data(),
            static_cast<VkDeviceSize>(geometry.indices.size() * sizeof(uint32_t)),
            VK_BUFFER_USAGE_INDEX_BUFFER_BIT,
            index_buffer);
        index_count = static_cast<uint32_t>(geometry.indices.size());
    }

    void create_framebuffers() {
        framebuffers.resize(swapchain_views.size());
        for (size_t i = 0; i < swapchain_views.size(); ++i) {
            VkFramebufferCreateInfo create{};
            create.sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
            create.renderPass = render_pass;
            create.attachmentCount = 1;
            create.pAttachments = &swapchain_views[i];
            create.width = swapchain_extent.width;
            create.height = swapchain_extent.height;
            create.layers = 1;
            vk_check(vkCreateFramebuffer(
                         device, &create, nullptr, &framebuffers[i]),
                     "vkCreateFramebuffer failed");
        }
    }

    void create_sync_and_commands() {
        VkCommandPoolCreateInfo pool{};
        pool.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
        pool.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
        pool.queueFamilyIndex = graphics_family;
        vk_check(vkCreateCommandPool(
                     device, &pool, nullptr, &command_pool),
                 "vkCreateCommandPool failed");

        command_buffers.resize(framebuffers.size());
        VkCommandBufferAllocateInfo allocate{};
        allocate.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
        allocate.commandPool = command_pool;
        allocate.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        allocate.commandBufferCount =
            static_cast<uint32_t>(command_buffers.size());
        vk_check(vkAllocateCommandBuffers(
                     device, &allocate, command_buffers.data()),
                 "vkAllocateCommandBuffers failed");

        VkSemaphoreCreateInfo semaphore{};
        semaphore.sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO;

        VkFenceCreateInfo fence{};
        fence.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
        fence.flags = VK_FENCE_CREATE_SIGNALED_BIT;

        for (size_t i = 0; i < kFramesInFlight; ++i) {
            vk_check(vkCreateSemaphore(
                         device, &semaphore, nullptr, &image_available[i]),
                     "vkCreateSemaphore failed");
            vk_check(vkCreateSemaphore(
                         device, &semaphore, nullptr, &render_finished[i]),
                     "vkCreateSemaphore failed");
            vk_check(vkCreateFence(
                         device, &fence, nullptr, &fences[i]),
                     "vkCreateFence failed");
        }
    }

    void record(VkCommandBuffer command, uint32_t image_index) {
        VkCommandBufferBeginInfo begin{};
        begin.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
        vk_check(vkBeginCommandBuffer(
                     command, &begin),
                 "vkBeginCommandBuffer failed");

        VkRenderPassBeginInfo pass{};
        pass.sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
        pass.renderPass = render_pass;
        pass.framebuffer = framebuffers[image_index];
        pass.renderArea.extent = swapchain_extent;

        VkClearValue clear{};
        clear.color.float32[0] = 0.018f;
        clear.color.float32[1] = 0.022f;
        clear.color.float32[2] = 0.032f;
        clear.color.float32[3] = 1.0f;
        pass.clearValueCount = 1;
        pass.pClearValues = &clear;

        vkCmdBeginRenderPass(
            command, &pass, VK_SUBPASS_CONTENTS_INLINE);
        vkCmdBindPipeline(
            command, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline);

        VkDeviceSize offset = 0;
        vkCmdBindVertexBuffers(
            command, 0, 1, &vertex_buffer.handle, &offset);
        vkCmdBindIndexBuffer(
            command, index_buffer.handle, 0, VK_INDEX_TYPE_UINT32);

        const std::array<float, 16> mvp = {
            1.05f, 0.0f, 0.0f, 0.0f,
            0.0f, -1.05f, 0.0f, 0.0f,
            0.0f, 0.0f, 0.8f, 0.0f,
            0.0f, 0.0f, 0.0f, 1.0f
        };

        vkCmdPushConstants(
            command, pipeline_layout, VK_SHADER_STAGE_VERTEX_BIT,
            0, sizeof(mvp), mvp.data());

        vkCmdDrawIndexed(
            command, index_count, 1, 0, 0, 0);
        vkCmdEndRenderPass(command);

        vk_check(vkEndCommandBuffer(
                     command),
                 "vkEndCommandBuffer failed");
    }

    bool frame() {
        const size_t slot = frame_slot % kFramesInFlight;
        vk_check(vkWaitForFences(
                     device, 1, &fences[slot], VK_TRUE, UINT64_MAX),
                 "vkWaitForFences failed");

        uint32_t image_index = 0;
        const VkResult acquire = vkAcquireNextImageKHR(
            device, swapchain, UINT64_MAX,
            image_available[slot], VK_NULL_HANDLE,
            &image_index);

        if (acquire == VK_ERROR_OUT_OF_DATE_KHR) return false;
        vk_check(acquire, "vkAcquireNextImageKHR failed");

        vk_check(vkResetFences(
                     device, 1, &fences[slot]),
                 "vkResetFences failed");
        vk_check(vkResetCommandBuffer(
                     command_buffers[image_index], 0),
                 "vkResetCommandBuffer failed");

        record(command_buffers[image_index], image_index);

        const VkPipelineStageFlags wait_stage =
            VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
        VkSubmitInfo submit{};
        submit.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
        submit.waitSemaphoreCount = 1;
        submit.pWaitSemaphores = &image_available[slot];
        submit.pWaitDstStageMask = &wait_stage;
        submit.commandBufferCount = 1;
        submit.pCommandBuffers = &command_buffers[image_index];
        submit.signalSemaphoreCount = 1;
        submit.pSignalSemaphores = &render_finished[slot];

        vk_check(vkQueueSubmit(
                     graphics_queue, 1, &submit, fences[slot]),
                 "vkQueueSubmit failed");

        VkPresentInfoKHR present{};
        present.sType = VK_STRUCTURE_TYPE_PRESENT_INFO_KHR;
        present.waitSemaphoreCount = 1;
        present.pWaitSemaphores = &render_finished[slot];
        present.swapchainCount = 1;
        present.pSwapchains = &swapchain;
        present.pImageIndices = &image_index;

        const VkResult present_result =
            vkQueuePresentKHR(present_queue, &present);

        ++frame_slot;
        if (present_result == VK_ERROR_OUT_OF_DATE_KHR ||
            present_result == VK_SUBOPTIMAL_KHR) {
            return false;
        }
        vk_check(present_result, "vkQueuePresentKHR failed");
        return true;
    }

    void destroy() {
        if (device != VK_NULL_HANDLE) {
            vkDeviceWaitIdle(device);
        }

        vertex_buffer.destroy();
        index_buffer.destroy();

        for (size_t i = 0; i < kFramesInFlight; ++i) {
            if (image_available[i]) {
                vkDestroySemaphore(device, image_available[i], nullptr);
            }
            if (render_finished[i]) {
                vkDestroySemaphore(device, render_finished[i], nullptr);
            }
            if (fences[i]) {
                vkDestroyFence(device, fences[i], nullptr);
            }
        }

        if (command_pool) {
            vkDestroyCommandPool(device, command_pool, nullptr);
        }
        for (auto framebuffer : framebuffers) {
            vkDestroyFramebuffer(device, framebuffer, nullptr);
        }
        if (pipeline) {
            vkDestroyPipeline(device, pipeline, nullptr);
        }
        if (pipeline_layout) {
            vkDestroyPipelineLayout(device, pipeline_layout, nullptr);
        }
        if (render_pass) {
            vkDestroyRenderPass(device, render_pass, nullptr);
        }
        if (vertex_shader) {
            vkDestroyShaderModule(device, vertex_shader, nullptr);
        }
        if (fragment_shader) {
            vkDestroyShaderModule(device, fragment_shader, nullptr);
        }
        for (auto view : swapchain_views) {
            vkDestroyImageView(device, view, nullptr);
        }
        if (swapchain) {
            vkDestroySwapchainKHR(device, swapchain, nullptr);
        }
        if (device) {
            vkDestroyDevice(device, nullptr);
        }
        if (surface) {
            vkDestroySurfaceKHR(instance, surface, nullptr);
        }
        if (instance) {
            vkDestroyInstance(instance, nullptr);
        }

        instance = VK_NULL_HANDLE;
        surface = VK_NULL_HANDLE;
        physical = VK_NULL_HANDLE;
        device = VK_NULL_HANDLE;
    }
};

struct Args {
    std::string mesh;
    std::string bundle;
    std::string shader_dir;
    int frames = kDefaultFrames;
};

Args parse_args(int argc, char** argv) {
    Args args;
    for (int i = 1; i < argc; ++i) {
        const std::string option = argv[i];
        if (option == "--mesh" || option == "--bundle" ||
            option == "--shader-dir" || option == "--frames") {
            if (i + 1 >= argc) {
                throw std::runtime_error("missing value for " + option);
            }
            const std::string value = argv[++i];
            if (option == "--mesh") args.mesh = value;
            else if (option == "--bundle") args.bundle = value;
            else if (option == "--shader-dir") args.shader_dir = value;
            else args.frames = std::max(1, std::stoi(value));
        } else if (option == "--help") {
            std::cout
                << "usage: shift_runtime (--mesh FILE | --bundle DIR) "
                << "--shader-dir DIR [--frames N]\n";
            std::exit(EXIT_SUCCESS);
        } else {
            throw std::runtime_error("unknown option: " + option);
        }
    }
    if (args.mesh.empty() == args.bundle.empty()) {
        throw std::runtime_error("exactly one of --mesh or --bundle is required");
    }
    if (args.shader_dir.empty()) {
        throw std::runtime_error("--shader-dir is required");
    }
    return args;
}

}  // namespace

int main(int argc, char** argv) {
    Runtime runtime;
    Window window;

    try {
        const Args args = parse_args(argc, argv);
        PacketGeometry geometry;
        if (!args.bundle.empty()) {
            geometry = load_bundle_geometry(args.bundle);
        } else {
            const shift::ir::Mesh mesh = shift::ir::loadMgeo(args.mesh);
            geometry.positions.reserve(mesh.positions.size() * 3u);
            for (const auto& vertex : mesh.positions) {
                geometry.positions.push_back(vertex.x);
                geometry.positions.push_back(vertex.y);
                geometry.positions.push_back(vertex.z);
            }
            geometry.indices = mesh.indices;
            geometry.source = "MGEO";
        }

        std::cout
            << "{\n"
            << "  \"format\": \"SHIFT.NativeRuntimeBootstrap/1\",\n"
            << "  \"geometry_source\": \"" << geometry.source << "\",\n"
            << "  \"geometry_vertices\": " << (geometry.positions.size() / 3u) << ",\n"
            << "  \"geometry_indices\": " << geometry.indices.size() << ",\n"
            << "  \"frames_requested\": " << args.frames << "\n"
            << "}\n";

        window.create();
        runtime.window = &window;
        runtime.create_instance();
        runtime.create_surface();
        runtime.create_device();
        runtime.create_swapchain();
        runtime.create_pipeline(args.shader_dir);
        runtime.create_geometry(geometry);
        runtime.create_framebuffers();
        runtime.create_sync_and_commands();

        int rendered = 0;
        bool quit = false;
        const auto start = std::chrono::steady_clock::now();

        while (!quit && rendered < args.frames) {
            window.poll(quit);
            if (!runtime.frame()) break;
            ++rendered;
        }

        vk_check(vkDeviceWaitIdle(runtime.device),
                 "vkDeviceWaitIdle failed");

        const auto elapsed_ms =
            std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::steady_clock::now() - start).count();

        std::cout
            << "{\n"
            << "  \"format\": \"SHIFT.NativeRuntimeFrameLoop/1\",\n"
            << "  \"frames_rendered\": " << rendered << ",\n"
            << "  \"elapsed_ms\": " << elapsed_ms << ",\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";

        runtime.destroy();
        window.destroy();
        return rendered > 0 ? EXIT_SUCCESS : EXIT_FAILURE;
    } catch (const std::exception& error) {
        std::cerr << "shift_runtime: " << error.what() << "\n";
        runtime.destroy();
        window.destroy();
        return EXIT_FAILURE;
    }
}
