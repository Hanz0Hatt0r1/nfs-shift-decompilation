#include <vulkan/vulkan.h>
#include <xcb/xcb.h>

#include "shift_ir.hpp"
#include "runtime_state.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
#include <map>
#include <cctype>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr uint32_t kWindowWidth = 1280;
constexpr uint32_t kWindowHeight = 720;
constexpr int kDefaultFrames = 120;
constexpr size_t kFramesInFlight = 2;
constexpr double kFixedDt = 1.0 / 60.0;

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
    std::vector<uint8_t> vertex_bytes;
    std::vector<GeometryAttribute> attributes;
    std::vector<uint32_t> indices;
    uint32_t stride = sizeof(float) * 3u;
    uint32_t first_index = 0;
    std::string source = "MGEO";
};

constexpr size_t kBundleConstantBytes = 4096;

struct BundleTexture {
    uint32_t register_index = 0;
    uint32_t width = 0;
    uint32_t height = 0;
    uint32_t sampler_mode = 1;
    std::vector<uint8_t> pixels;
};

struct BundleCube {
    uint32_t register_index = 3;
    uint32_t width = 0;
    uint32_t height = 0;
    std::vector<uint8_t> pixels;
};

struct BundleAssets {
    std::string vertex_shader_path;
    std::string fragment_shader_path;
    std::vector<uint8_t> vertex_constants;
    std::vector<uint8_t> pixel_constants;
    std::vector<BundleTexture> textures;
    BundleCube cube{};
    bool has_cube = false;
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

uint32_t read_u32(const std::vector<uint8_t>& data, size_t offset) {
    if (offset > data.size() || data.size() - offset < sizeof(uint32_t)) {
        throw std::runtime_error("bundle packet integer is out of bounds");
    }
    uint32_t value = 0;
    std::memcpy(&value, data.data() + offset, sizeof(value));
    return value;
}

bool file_contains(const std::string& path, const std::string& needle) { 
    std::ifstream file(path, std::ios::binary);
    if (!file) return false;
    const std::string contents(
        (std::istreambuf_iterator<char>(file)),
        std::istreambuf_iterator<char>());
    return contents.find(needle) != std::string::npos;
}

uint32_t json_u32_field(
    const std::string& path,
    const std::string& field) {
    std::ifstream file(path, std::ios::binary);
    if (!file) {
        throw std::runtime_error("cannot open JSON manifest: " + path);
    }
    const std::string text(
        (std::istreambuf_iterator<char>(file)),
        std::istreambuf_iterator<char>());
    const std::string key = "\""+field+"\"";
    const size_t key_pos = text.find(key);
    if (key_pos == std::string::npos) {
        throw std::runtime_error("manifest field is missing: " + field);
    }
    const size_t colon = text.find(':', key_pos + key.size());
    if (colon == std::string::npos) {
        throw std::runtime_error("manifest field has no value: " + field);
    }
    size_t cursor = colon + 1;
    while (cursor < text.size() &&
           std::isspace(static_cast<unsigned char>(text[cursor]))) {
        ++cursor;
    }
    if (cursor == text.size() || !std::isdigit(static_cast<unsigned char>(text[cursor]))) {
        throw std::runtime_error("manifest field is not a non-negative integer: " + field);
    }
    uint64_t value = 0;
    while (cursor < text.size() &&
           std::isdigit(static_cast<unsigned char>(text[cursor]))) {
        value = value * 10u + static_cast<unsigned>(text[cursor] - '0');
        if (value > UINT32_MAX) {
            throw std::runtime_error("manifest field exceeds uint32: " + field);
        }
        ++cursor;
    }
    return static_cast<uint32_t>(value);
}

shift::runtime::PhysicsWorkspaceBoundary load_physics_manifest(
    const std::string& path) {
    if (!file_contains(
            path,
            "\"format\": \"SHIFT.BMWM3VehiclePhysicsResourceManifest/1\"")) {
        throw std::runtime_error("unsupported native physics manifest");
    }
    shift::runtime::PhysicsWorkspaceBoundary workspace{};
    workspace.configure(
        json_u32_field(path, "body_count"),
        json_u32_field(path, "joint_hinge_count"),
        json_u32_field(path, "bar_count"));
    if (!workspace.ready || workspace.scalar_count != 40u) {
        throw std::runtime_error("BMW SDF manifest does not resolve to 40 solver scalars");
    }
    return workspace;
}

BundleAssets load_bundle_assets(const std::string& root) {
    if (!file_contains(
            root + "/vulkan_interface.json",
            "\"format\": \"SHIFT.BMWVulkanInterfaceGate/1\"") ||
        !file_contains(root + "/vulkan_interface.json", "\"ready\": true") ||
        !file_contains(root + "/spirv_report.json", "\"format\": \"SHIFT.VulkanBundleSPIRV/1\"") ||
        !file_contains(root + "/spirv_report.json", "\"ready\": true")) {
        throw std::runtime_error(
            "bundle shader/interface gate is missing or not ready");
    }

    BundleAssets out;
    out.vertex_shader_path = root + "/spirv/submesh_0.vertex.glsl.spv";
    out.fragment_shader_path = root + "/spirv/submesh_0.pixel.glsl.spv";
    if (!std::filesystem::is_regular_file(out.vertex_shader_path) ||
        !std::filesystem::is_regular_file(out.fragment_shader_path)) {
        throw std::runtime_error("bundle submesh-0 SPIR-V shader is missing");
    }

    const auto constants = read_file_bytes(root + "/constants.svcp");
    if (constants.size() != 28u + 2u * kBundleConstantBytes ||
        std::memcmp(constants.data(), "SVCP", 4) != 0 ||
        read_u32(constants, 4) != 1u ||
        read_u32(constants, 8) != 256u ||
        read_u32(constants, 12) != 16u) {
        throw std::runtime_error("unsupported bundle constant packet");
    }
    out.vertex_constants.assign(
        constants.begin() + 28,
        constants.begin() + 28 + kBundleConstantBytes);
    out.pixel_constants.assign(
        constants.begin() + 28 + kBundleConstantBytes,
        constants.end());

    const std::string textures_path = root + "/textures.svtp";
    if (std::filesystem::is_regular_file(textures_path)) {
        const auto data = read_file_bytes(textures_path);
        if (data.size() < 20u || std::memcmp(data.data(), "SVTP", 4) != 0 ||
            read_u32(data, 4) != 1u ||
            read_u32(data, 12) != 1u) {
            throw std::runtime_error("unsupported bundle texture packet");
        }
        const uint32_t count = read_u32(data, 8);
        if (count == 0 || count > 16) {
            throw std::runtime_error("invalid bundle texture count");
        }
        const size_t table_end = 20u + static_cast<size_t>(count) * 24u;
        if (table_end > data.size()) {
            throw std::runtime_error("bundle texture table truncated");
        }
        out.textures.resize(count);
        for (uint32_t i = 0; i < count; ++i) {
            const size_t offset = 20u + static_cast<size_t>(i) * 24u;
            const uint32_t reg = read_u32(data, offset);
            const uint32_t width = read_u32(data, offset + 4);
            const uint32_t height = read_u32(data, offset + 8);
            const uint32_t pixel_offset = read_u32(data, offset + 12);
            const uint32_t pixel_bytes = read_u32(data, offset + 16);
            const uint32_t sampler_mode = read_u32(data, offset + 20);
            const uint64_t expected = static_cast<uint64_t>(width) * height * 4u;
            if (reg > 15 || width == 0 || height == 0 ||
                expected != pixel_bytes || pixel_offset < table_end ||
                static_cast<uint64_t>(pixel_offset) + pixel_bytes > data.size() ||
                sampler_mode < 1 || sampler_mode > 4) {
                throw std::runtime_error("invalid bundle texture record");
            }
            BundleTexture& texture = out.textures[i];
            texture.register_index = reg;
            texture.width = width;
            texture.height = height;
            texture.sampler_mode = sampler_mode;
            texture.pixels.assign(
                data.begin() + static_cast<std::ptrdiff_t>(pixel_offset),
                data.begin() + static_cast<std::ptrdiff_t>(pixel_offset + pixel_bytes));
        }
    }

    const std::string cube_path = root + "/environment_cube.svcp";
    if (std::filesystem::is_regular_file(cube_path)) {
        const auto data = read_file_bytes(cube_path);
        if (data.size() < 28u || std::memcmp(data.data(), "SVCP", 4) != 0 ||
            read_u32(data, 4) != 1u ||
            read_u32(data, 8) != 3u ||
            read_u32(data, 20) != 6u) {
            throw std::runtime_error("unsupported bundle cube packet");
        }
        const uint32_t width = read_u32(data, 12);
        const uint32_t height = read_u32(data, 16);
        const uint32_t face_bytes = read_u32(data, 24);
        const uint64_t expected_face = static_cast<uint64_t>(width) * height * 4u;
        const uint64_t expected_total = expected_face * 6u;
        if (width == 0 || height == 0 || expected_face != face_bytes ||
            data.size() != 28u + expected_total) {
            throw std::runtime_error("bundle cube packet size mismatch");
        }
        out.has_cube = true;
        out.cube.width = width;
        out.cube.height = height;
        out.cube.pixels.assign(data.begin() + 28, data.end());
    }
    return out;
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
    out.stride = header.stride;
    out.attributes = attributes;
    out.vertex_bytes.assign(
        data.begin() + static_cast<std::ptrdiff_t>(vertex_base),
        data.begin() + static_cast<std::ptrdiff_t>(index_base));
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

struct InputState {
    bool throttle = false;
    bool brake = false;
    bool steer_left = false;
    bool steer_right = false;
};

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
            XCB_EVENT_MASK_KEY_PRESS |
            XCB_EVENT_MASK_KEY_RELEASE;

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

    void poll(bool& quit, InputState& input) {
        while (xcb_generic_event_t* raw = xcb_poll_for_event(connection)) {
            const uint8_t type = raw->response_type & 0x7f;
            if (type == XCB_KEY_PRESS || type == XCB_KEY_RELEASE) {
                const auto* event =
                    reinterpret_cast<const xcb_key_press_event_t*>(raw);
                const bool pressed = type == XCB_KEY_PRESS;
                switch (event->detail) {
                    case 9:
                    case 24:
                        if (pressed) quit = true;
                        break;
                    case 111:
                    case 25:
                        input.throttle = pressed;
                        break;
                    case 116:
                    case 39:
                        input.brake = pressed;
                        break;
                    case 113:
                    case 38:
                        input.steer_left = pressed;
                        break;
                    case 114:
                    case 40:
                        input.steer_right = pressed;
                        break;
                    default:
                        break;
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

struct Image {
    VkDevice device = VK_NULL_HANDLE;
    VkImage handle = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
    VkImageView view = VK_NULL_HANDLE;
    uint32_t layers = 1;

    void destroy() {
        if (device != VK_NULL_HANDLE) {
            if (view) vkDestroyImageView(device, view, nullptr);
            if (handle) vkDestroyImage(device, handle, nullptr);
            if (memory) vkFreeMemory(device, memory, nullptr);
        }
        device = VK_NULL_HANDLE;
        handle = VK_NULL_HANDLE;
        memory = VK_NULL_HANDLE;
        view = VK_NULL_HANDLE;
        layers = 1;
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
    uint32_t first_index = 0;

    bool material_mode = false;
    Buffer vertex_constants;
    Buffer pixel_constants;
    std::vector<Buffer> texture_staging;
    std::vector<Image> texture_images;
    std::vector<VkSampler> texture_samplers;
    Image cube_image;
    Buffer cube_staging;
    VkSampler cube_sampler = VK_NULL_HANDLE;
    VkDescriptorSetLayout set0_layout = VK_NULL_HANDLE;
    VkDescriptorSetLayout set1_layout = VK_NULL_HANDLE;
    VkDescriptorPool descriptor_pool = VK_NULL_HANDLE;
    VkDescriptorSet set0 = VK_NULL_HANDLE;
    VkDescriptorSet set1 = VK_NULL_HANDLE;

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

    void create_image(
        uint32_t width,
        uint32_t height,
        uint32_t layers,
        VkImageCreateFlags flags,
        Image& out) {
        VkImageCreateInfo create{};
        create.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
        create.flags = flags;
        create.imageType = VK_IMAGE_TYPE_2D;
        create.format = VK_FORMAT_R8G8B8A8_UNORM;
        create.extent = {width, height, 1};
        create.mipLevels = 1;
        create.arrayLayers = layers;
        create.samples = VK_SAMPLE_COUNT_1_BIT;
        create.tiling = VK_IMAGE_TILING_OPTIMAL;
        create.usage = VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_SAMPLED_BIT;
        create.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        vk_check(vkCreateImage(device, &create, nullptr, &out.handle),
                 "vkCreateImage failed");
        out.device = device;
        out.layers = layers;

        VkMemoryRequirements requirements{};
        vkGetImageMemoryRequirements(device, out.handle, &requirements);
        VkMemoryAllocateInfo allocate{};
        allocate.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
        allocate.allocationSize = requirements.size;
        allocate.memoryTypeIndex = find_memory_type(
            physical, requirements.memoryTypeBits,
            VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        vk_check(vkAllocateMemory(
                     device, &allocate, nullptr, &out.memory),
                 "vkAllocateMemory image failed");
        vk_check(vkBindImageMemory(
                     device, out.handle, out.memory, 0),
                 "vkBindImageMemory failed");

        VkImageViewCreateInfo view{};
        view.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
        view.image = out.handle;
        view.viewType = layers == 6 ? VK_IMAGE_VIEW_TYPE_CUBE : VK_IMAGE_VIEW_TYPE_2D;
        view.format = VK_FORMAT_R8G8B8A8_UNORM;
        view.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        view.subresourceRange.levelCount = 1;
        view.subresourceRange.layerCount = layers;
        vk_check(vkCreateImageView(
                     device, &view, nullptr, &out.view),
                 "vkCreateImageView resource failed");
    }

    VkSampler create_sampler(uint32_t mode) {
        const bool linear = mode == 2 || mode == 4;
        const bool clamp = mode == 3 || mode == 4;
        VkSamplerCreateInfo create{};
        create.sType = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO;
        create.magFilter = linear ? VK_FILTER_LINEAR : VK_FILTER_NEAREST;
        create.minFilter = linear ? VK_FILTER_LINEAR : VK_FILTER_NEAREST;
        create.mipmapMode = VK_SAMPLER_MIPMAP_MODE_NEAREST;
        create.addressModeU = clamp ? VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE :
                                      VK_SAMPLER_ADDRESS_MODE_REPEAT;
        create.addressModeV = clamp ? VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE :
                                      VK_SAMPLER_ADDRESS_MODE_REPEAT;
        create.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
        create.maxLod = 1.0f;
        VkSampler sampler = VK_NULL_HANDLE;
        vk_check(vkCreateSampler(
                     device, &create, nullptr, &sampler),
                 "vkCreateSampler failed");
        return sampler;
    }

    void create_material_resources(const BundleAssets& bundle) {
        if (bundle.vertex_constants.size() != kBundleConstantBytes ||
            bundle.pixel_constants.size() != kBundleConstantBytes) {
            throw std::runtime_error("bundle constants are incomplete");
        }

        create_buffer(
            bundle.vertex_constants.data(), kBundleConstantBytes,
            VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT, vertex_constants);
        create_buffer(
            bundle.pixel_constants.data(), kBundleConstantBytes,
            VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT, pixel_constants);

        texture_staging.resize(bundle.textures.size());
        texture_images.resize(bundle.textures.size());
        texture_samplers.resize(bundle.textures.size());
        for (size_t i = 0; i < bundle.textures.size(); ++i) {
            const BundleTexture& texture = bundle.textures[i];
            create_buffer(
                texture.pixels.data(),
                texture.pixels.size(),
                VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
                texture_staging[i]);
            create_image(
                texture.width, texture.height, 1, 0, texture_images[i]);
            texture_samplers[i] = create_sampler(texture.sampler_mode);
        }

        if (bundle.has_cube) {
            create_buffer(
                bundle.cube.pixels.data(),
                bundle.cube.pixels.size(),
                VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
                cube_staging);
            create_image(
                bundle.cube.width, bundle.cube.height, 6,
                VK_IMAGE_CREATE_CUBE_COMPATIBLE_BIT, cube_image);
            cube_sampler = create_sampler(4);
        }

        VkDescriptorSetLayoutBinding set0_bindings[2]{};
        set0_bindings[0].binding = 14;
        set0_bindings[0].descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
        set0_bindings[0].descriptorCount = 1;
        set0_bindings[0].stageFlags = VK_SHADER_STAGE_VERTEX_BIT;
        set0_bindings[1].binding = 15;
        set0_bindings[1].descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
        set0_bindings[1].descriptorCount = 1;
        set0_bindings[1].stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT;

        VkDescriptorSetLayoutCreateInfo set0_info{};
        set0_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
        set0_info.bindingCount = 2;
        set0_info.pBindings = set0_bindings;
        vk_check(vkCreateDescriptorSetLayout(
                     device, &set0_info, nullptr, &set0_layout),
                 "vkCreateDescriptorSetLayout set0 failed");

        std::map<uint32_t, VkDescriptorImageInfo> sampled;
        for (size_t i = 0; i < bundle.textures.size(); ++i) {
            const uint32_t reg = bundle.textures[i].register_index;
            VkDescriptorImageInfo info{};
            info.sampler = texture_samplers[i];
            info.imageView = texture_images[i].view;
            info.imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
            if (!sampled.emplace(reg, info).second) {
                throw std::runtime_error("duplicate bundle sampler register");
            }
        }
        if (bundle.has_cube) {
            VkDescriptorImageInfo info{};
            info.sampler = cube_sampler;
            info.imageView = cube_image.view;
            info.imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
            if (!sampled.emplace(bundle.cube.register_index, info).second) {
                throw std::runtime_error("cube sampler register collides with 2D texture");
            }
        }

        std::vector<VkDescriptorSetLayoutBinding> set1_bindings;
        set1_bindings.reserve(sampled.size());
        for (const auto& item : sampled) {
            VkDescriptorSetLayoutBinding binding{};
            binding.binding = item.first;
            binding.descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
            binding.descriptorCount = 1;
            binding.stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT;
            set1_bindings.push_back(binding);
        }

        VkDescriptorSetLayoutCreateInfo set1_info{};
        set1_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
        set1_info.bindingCount = static_cast<uint32_t>(set1_bindings.size());
        set1_info.pBindings = set1_bindings.empty() ? nullptr : set1_bindings.data();
        vk_check(vkCreateDescriptorSetLayout(
                     device, &set1_info, nullptr, &set1_layout),
                 "vkCreateDescriptorSetLayout set1 failed");

        std::vector<VkDescriptorPoolSize> pool_sizes;
        pool_sizes.push_back({VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, 2});
        if (!sampled.empty()) {
            pool_sizes.push_back({
                VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
                static_cast<uint32_t>(sampled.size())
            });
        }
        VkDescriptorPoolCreateInfo pool{};
        pool.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;
        pool.maxSets = 2;
        pool.poolSizeCount = static_cast<uint32_t>(pool_sizes.size());
        pool.pPoolSizes = pool_sizes.data();
        vk_check(vkCreateDescriptorPool(
                     device, &pool, nullptr, &descriptor_pool),
                 "vkCreateDescriptorPool failed");

        VkDescriptorSetAllocateInfo set0_alloc{};
        set0_alloc.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
        set0_alloc.descriptorPool = descriptor_pool;
        set0_alloc.descriptorSetCount = 1;
        set0_alloc.pSetLayouts = &set0_layout;
        vk_check(vkAllocateDescriptorSets(
                     device, &set0_alloc, &set0),
                 "vkAllocateDescriptorSets set0 failed");

        VkDescriptorBufferInfo vertex_info{vertex_constants.handle, 0, kBundleConstantBytes};
        VkDescriptorBufferInfo pixel_info{pixel_constants.handle, 0, kBundleConstantBytes};
        VkWriteDescriptorSet writes[2]{};
        writes[0].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
        writes[0].dstSet = set0;
        writes[0].dstBinding = 14;
        writes[0].descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
        writes[0].descriptorCount = 1;
        writes[0].pBufferInfo = &vertex_info;
        writes[1] = writes[0];
        writes[1].dstBinding = 15;
        writes[1].pBufferInfo = &pixel_info;
        vkUpdateDescriptorSets(device, 2, writes, 0, nullptr);

        if (!set1_bindings.empty()) {
            VkDescriptorSetAllocateInfo set1_alloc{};
            set1_alloc.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
            set1_alloc.descriptorPool = descriptor_pool;
            set1_alloc.descriptorSetCount = 1;
            set1_alloc.pSetLayouts = &set1_layout;
            vk_check(vkAllocateDescriptorSets(
                         device, &set1_alloc, &set1),
                     "vkAllocateDescriptorSets set1 failed");

            std::vector<VkWriteDescriptorSet> image_writes;
            image_writes.reserve(sampled.size());
            std::vector<VkDescriptorImageInfo> image_infos;
            image_infos.reserve(sampled.size());
            for (const auto& item : sampled) {
                image_infos.push_back(item.second);
            }
            size_t image_index = 0;
            for (const auto& item : sampled) {
                VkWriteDescriptorSet write{};
                write.sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
                write.dstSet = set1;
                write.dstBinding = item.first;
                write.descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
                write.descriptorCount = 1;
                write.pImageInfo = &image_infos[image_index++];
                image_writes.push_back(write);
            }
            vkUpdateDescriptorSets(
                device,
                static_cast<uint32_t>(image_writes.size()),
                image_writes.data(),
                0,
                nullptr);
        }
    }

    void upload_material_resources(const BundleAssets& bundle) {
        if (texture_staging.empty() && !cube_staging.handle) {
            return;
        }

        VkCommandBufferAllocateInfo allocate{};
        allocate.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
        allocate.commandPool = command_pool;
        allocate.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        allocate.commandBufferCount = 1;
        VkCommandBuffer command = VK_NULL_HANDLE;
        vk_check(vkAllocateCommandBuffers(
                     device, &allocate, &command),
                 "vkAllocateCommandBuffers resource upload failed");

        VkCommandBufferBeginInfo begin{};
        begin.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
        begin.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        vk_check(vkBeginCommandBuffer(command, &begin),
                 "vkBeginCommandBuffer resource upload failed");

        auto transition = [&](VkImage image, uint32_t layers,
                              VkImageLayout old_layout, VkImageLayout new_layout,
                              VkAccessFlags src_access, VkAccessFlags dst_access,
                              VkPipelineStageFlags src_stage, VkPipelineStageFlags dst_stage) {
            VkImageMemoryBarrier barrier{};
            barrier.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
            barrier.srcAccessMask = src_access;
            barrier.dstAccessMask = dst_access;
            barrier.oldLayout = old_layout;
            barrier.newLayout = new_layout;
            barrier.image = image;
            barrier.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
            barrier.subresourceRange.levelCount = 1;
            barrier.subresourceRange.layerCount = layers;
            vkCmdPipelineBarrier(
                command, src_stage, dst_stage, 0,
                0, nullptr, 0, nullptr, 1, &barrier);
        };

        for (size_t i = 0; i < texture_staging.size(); ++i) {
            transition(
                texture_images[i].handle, 1,
                VK_IMAGE_LAYOUT_UNDEFINED,
                VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                0, VK_ACCESS_TRANSFER_WRITE_BIT,
                VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                VK_PIPELINE_STAGE_TRANSFER_BIT);

            VkBufferImageCopy copy{};
            copy.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
            copy.imageSubresource.layerCount = 1;
            copy.imageExtent = {
                bundle.textures[i].width,
                bundle.textures[i].height,
                1
            };
            vkCmdCopyBufferToImage(
                command, texture_staging[i].handle,
                texture_images[i].handle,
                VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                1, &copy);

            transition(
                texture_images[i].handle, 1,
                VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                VK_ACCESS_TRANSFER_WRITE_BIT,
                VK_ACCESS_SHADER_READ_BIT,
                VK_PIPELINE_STAGE_TRANSFER_BIT,
                VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT);
        }

        if (cube_staging.handle) {
            transition(
                cube_image.handle, 6,
                VK_IMAGE_LAYOUT_UNDEFINED,
                VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                0, VK_ACCESS_TRANSFER_WRITE_BIT,
                VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                VK_PIPELINE_STAGE_TRANSFER_BIT);

            const VkDeviceSize face_bytes =
                static_cast<VkDeviceSize>(bundle.cube.width) *
                static_cast<VkDeviceSize>(bundle.cube.height) * 4u;
            for (uint32_t face = 0; face < 6; ++face) {
                VkBufferImageCopy copy{};
                copy.bufferOffset = static_cast<VkDeviceSize>(face) * face_bytes;
                copy.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
                copy.imageSubresource.baseArrayLayer = face;
                copy.imageSubresource.layerCount = 1;
                copy.imageExtent = {
                    bundle.cube.width,
                    bundle.cube.height,
                    1
                };
                vkCmdCopyBufferToImage(
                    command, cube_staging.handle,
                    cube_image.handle,
                    VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                    1, &copy);
            }

            transition(
                cube_image.handle, 6,
                VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                VK_ACCESS_TRANSFER_WRITE_BIT,
                VK_ACCESS_SHADER_READ_BIT,
                VK_PIPELINE_STAGE_TRANSFER_BIT,
                VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT);
        }

        vk_check(vkEndCommandBuffer(command),
                 "vkEndCommandBuffer resource upload failed");

        VkSubmitInfo submit{};
        submit.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
        submit.commandBufferCount = 1;
        submit.pCommandBuffers = &command;
        vk_check(vkQueueSubmit(
                     graphics_queue, 1, &submit, VK_NULL_HANDLE),
                 "vkQueueSubmit resource upload failed");
        vk_check(vkQueueWaitIdle(
                     graphics_queue),
                 "vkQueueWaitIdle resource upload failed");
        vkFreeCommandBuffers(device, command_pool, 1, &command);

        for (auto& staging : texture_staging) staging.destroy();
        texture_staging.clear();
        cube_staging.destroy();
    }

    void create_pipeline(
        const std::string& shader_dir,
        const PacketGeometry& geometry,
        const BundleAssets* bundle) {
        material_mode = bundle != nullptr;
        vertex_shader = load_shader(
            material_mode ? bundle->vertex_shader_path :
            shader_dir + "/runtime.vert.spv");
        fragment_shader = load_shader(
            material_mode ? bundle->fragment_shader_path :
            shader_dir + "/runtime.frag.spv");

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
        if (material_mode) {
            const VkDescriptorSetLayout sets[] = {set0_layout, set1_layout};
            layout.setLayoutCount = 2;
            layout.pSetLayouts = sets;
        } else {
            layout.pushConstantRangeCount = 1;
            layout.pPushConstantRanges = &push;
        }
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
        binding.stride = geometry.stride;
        binding.inputRate = VK_VERTEX_INPUT_RATE_VERTEX;

        auto vk_format = [](uint32_t format) -> VkFormat {
            switch (format) {
                case 1: return VK_FORMAT_R32G32_SFLOAT;
                case 2: return VK_FORMAT_R32G32B32_SFLOAT;
                case 3: return VK_FORMAT_R32G32B32A32_SFLOAT;
                case 4: return VK_FORMAT_R8G8B8A8_UNORM;
                case 5: return VK_FORMAT_R8G8B8A8_UINT;
                default: return VK_FORMAT_UNDEFINED;
            }
        };

        std::vector<VkVertexInputAttributeDescription> vertex_attributes;
        vertex_attributes.reserve(geometry.attributes.size());
        for (const auto& input : geometry.attributes) {
            VkVertexInputAttributeDescription attribute{};
            attribute.location = input.location;
            attribute.binding = 0;
            attribute.format = vk_format(input.format);
            attribute.offset = input.offset;
            if (attribute.format == VK_FORMAT_UNDEFINED) {
                throw std::runtime_error("unknown runtime vertex attribute format");
            }
            vertex_attributes.push_back(attribute);
        }
        if (vertex_attributes.empty()) {
            throw std::runtime_error("runtime geometry has no vertex attributes");
        }

        VkPipelineVertexInputStateCreateInfo vertex_input{};
        vertex_input.sType =
            VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO;
        vertex_input.vertexBindingDescriptionCount = 1;
        vertex_input.pVertexBindingDescriptions = &binding;
        vertex_input.vertexAttributeDescriptionCount =
            static_cast<uint32_t>(vertex_attributes.size());
        vertex_input.pVertexAttributeDescriptions = vertex_attributes.data();

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
        raster.cullMode = material_mode ? VK_CULL_MODE_NONE : VK_CULL_MODE_BACK_BIT;
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
        first_index = geometry.first_index;
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

        if (material_mode) {
            vkCmdBindDescriptorSets(
                command,
                VK_PIPELINE_BIND_POINT_GRAPHICS,
                pipeline_layout,
                0, 1, &set0, 0, nullptr);
            if (set1 != VK_NULL_HANDLE) {
                vkCmdBindDescriptorSets(
                    command,
                    VK_PIPELINE_BIND_POINT_GRAPHICS,
                    pipeline_layout,
                    1, 1, &set1, 0, nullptr);
            }
        } else {
            const std::array<float, 16> mvp = {
                1.05f, 0.0f, 0.0f, 0.0f,
                0.0f, -1.05f, 0.0f, 0.0f,
                0.0f, 0.0f, 0.8f, 0.0f,
                0.0f, 0.0f, 0.0f, 1.0f
            };
            vkCmdPushConstants(
                command, pipeline_layout, VK_SHADER_STAGE_VERTEX_BIT,
                0, sizeof(mvp), mvp.data());
        }

        vkCmdDrawIndexed(
            command, index_count, 1, first_index, 0, 0);
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
        vertex_constants.destroy();
        pixel_constants.destroy();
        for (auto& staging : texture_staging) staging.destroy();
        texture_staging.clear();
        cube_staging.destroy();
        for (VkSampler sampler : texture_samplers) {
            if (sampler && device) vkDestroySampler(device, sampler, nullptr);
        }
        texture_samplers.clear();
        for (auto& image : texture_images) image.destroy();
        texture_images.clear();
        if (cube_sampler && device) vkDestroySampler(device, cube_sampler, nullptr);
        cube_sampler = VK_NULL_HANDLE;
        cube_image.destroy();

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
        if (descriptor_pool && device) {
            vkDestroyDescriptorPool(device, descriptor_pool, nullptr);
        }
        if (set1_layout && device) {
            vkDestroyDescriptorSetLayout(device, set1_layout, nullptr);
        }
        if (set0_layout && device) {
            vkDestroyDescriptorSetLayout(device, set0_layout, nullptr);
        }
        descriptor_pool = VK_NULL_HANDLE;
        set1_layout = VK_NULL_HANDLE;
        set0_layout = VK_NULL_HANDLE;
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
    std::string physics_manifest;
    std::string shader_dir;
    int frames = kDefaultFrames;
};

Args parse_args(int argc, char** argv) {
    Args args;
    for (int i = 1; i < argc; ++i) {
        const std::string option = argv[i];
        if (option == "--mesh" || option == "--bundle" ||
            option == "--physics-manifest" || option == "--shader-dir" ||
            option == "--frames") {
            if (i + 1 >= argc) {
                throw std::runtime_error("missing value for " + option);
            }
            const std::string value = argv[++i];
            if (option == "--mesh") args.mesh = value;
            else if (option == "--bundle") args.bundle = value;
            else if (option == "--physics-manifest") args.physics_manifest = value;
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
            geometry.attributes = {{
                0, 2, 0, static_cast<uint32_t>(sizeof(float) * 3u)
            }};
            geometry.stride = sizeof(float) * 3u;
            geometry.source = "MGEO";
        }

        std::cout
            << "{\n"
            << "  \"format\": \"SHIFT.NativeRuntimeBootstrap/1\",\n"
            << "  \"geometry_source\": \"" << geometry.source << "\",\n"
            << "  \"geometry_vertices\": " << (geometry.positions.size() / 3u) << ",\n"
            << "  \"geometry_indices\": " << geometry.indices.size() << ",\n"
            << "  \"material_mode\": " << (!args.bundle.empty() ? "true" : "false") << ",\n"
            << "  \"frames_requested\": " << args.frames << "\n"
            << "}\n";

        window.create();
        runtime.window = &window;
        runtime.create_instance();
        runtime.create_surface();
        runtime.create_device();
        runtime.create_swapchain();
        BundleAssets bundle_assets{};
        const BundleAssets* bundle = nullptr;
        if (!args.bundle.empty()) {
            bundle_assets = load_bundle_assets(args.bundle);
            bundle = &bundle_assets;
            runtime.create_material_resources(bundle_assets);
        }
        runtime.create_pipeline(args.shader_dir, geometry, bundle);
        runtime.create_geometry(geometry);
        runtime.create_framebuffers();
        runtime.create_sync_and_commands();
        if (bundle) {
            runtime.upload_material_resources(bundle_assets);
        }

        int rendered = 0;
        uint64_t simulation_steps = 0;
        bool quit = false;
        InputState input{};
        shift::runtime::NativeRuntimeState native_state{};
        if (!args.physics_manifest.empty()) {
            native_state.physics.workspace =
                load_physics_manifest(args.physics_manifest);
        }
        const auto start = std::chrono::steady_clock::now();

        while (!quit && rendered < args.frames) {
            window.poll(quit, input);

            // Deterministic simulation boundary.
            shift::runtime::VehicleControlIntent intent{};
            intent.throttle = input.throttle;
            intent.brake = input.brake;
            intent.steer_left = input.steer_left;
            intent.steer_right = input.steer_right;
            native_state.fixed_step(intent);
            ++simulation_steps;

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
            << "  \"simulation_steps\": " << simulation_steps << ",\n"
            << "  \"fixed_dt\": " << kFixedDt << ",\n"
            << "  \"input_layer\": \"SHIFT.NativeRuntimeInput/1\",\n"
            << "  \"state_layer\": \"SHIFT.NativeRuntimeState/1\",\n"
            << "  \"camera_active_buffer\": " << native_state.camera.active_index << ",\n"
            << "  \"vehicle_control_steer_axis\": " << native_state.physics.last_input.steer_axis() << ",\n"
            << "  \"physics_participant_ready\": " << (native_state.physics.participant_ready ? "true" : "false") << ",\n"
            << "  \"physics_participant_index\": " << native_state.physics.participant_index << ",\n"
            << "  \"physics_participant_mode\": " << native_state.physics.participant_mode << ",\n"
            << "  \"physics_workspace_ready\": " << (native_state.physics.workspace.ready ? "true" : "false") << ",\n"
            << "  \"physics_workspace_scalars\": " << native_state.physics.workspace.scalar_count << ",\n"
            << "  \"physics_workspace_matrix_bytes\": " << native_state.physics.workspace.matrix_bytes << ",\n"
            << "  \"material_mode\": " << (runtime.material_mode ? "true" : "false") << ",\n"
            << "  \"bundle_2d_textures\": " << runtime.texture_images.size() << ",\n"
            << "  \"bundle_cube\": " << (!runtime.cube_image.handle ? "false" : "true") << ",\n"
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
