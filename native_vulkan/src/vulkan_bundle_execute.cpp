#include <vulkan/vulkan.h>
#include "shift_vulkan_validation.hpp"

#include <algorithm>
#include <cstdint>
#include <cmath>
#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

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
struct LegacyGeometryAttribute {
    uint32_t location;
    uint32_t format;
    uint32_t offset;
    uint32_t stride;
};
struct GeometryAttribute {
    uint32_t location;
    uint32_t format;
    uint32_t offset;
    uint32_t stride;
    uint32_t property_id;
};
struct CaptureGeometryMetadata {
    uint32_t index_format_bits;
    uint32_t draw_index_count;
    int32_t base_vertex;
    uint32_t vertex_buffer_offset;
};
struct ConstantHeader {
    char magic[4];
    uint32_t version;
    uint32_t max_registers;
    uint32_t register_bytes;
    uint32_t vertex_populated;
    uint32_t pixel_populated;
    uint32_t reserved;
};
struct TextureHeader {
    char magic[4];
    uint32_t version;
    uint32_t texture_count;
    uint32_t descriptor_set;
    uint32_t reserved;
};
struct TextureRecord {
    uint32_t register_index;
    uint32_t width;
    uint32_t height;
    uint32_t pixel_offset;
    uint32_t pixel_bytes;
    uint32_t sampler_mode;
};
struct CubeHeader {
    char magic[4];
    uint32_t version;
    uint32_t register_index;
    uint32_t width;
    uint32_t height;
    uint32_t face_count;
    uint32_t face_bytes;
};
struct WorldTransformHeader {
    char magic[4];
    uint32_t version;
    uint32_t convention;
    uint32_t matrix_bytes;
};
#pragma pack(pop)

static_assert(sizeof(GeometryHeader) == 44);
static_assert(sizeof(LegacyGeometryAttribute) == 16);
static_assert(sizeof(GeometryAttribute) == 20);
static_assert(sizeof(CaptureGeometryMetadata) == 16);
static_assert(sizeof(ConstantHeader) == 28);
static_assert(sizeof(TextureHeader) == 20);
static_assert(sizeof(TextureRecord) == 24);
static_assert(sizeof(CubeHeader) == 28);
static_assert(sizeof(WorldTransformHeader) == 16);

namespace {

constexpr uint32_t kConstantBytes = 4096;
constexpr uint32_t kDefaultRenderWidth = 800;
constexpr uint32_t kDefaultRenderHeight = 450;

struct PipelineState {
    VkCullModeFlags cull_mode = VK_CULL_MODE_NONE;
    VkBool32 depth_test_enable = VK_TRUE;
    VkBool32 depth_write_enable = VK_TRUE;
    VkCompareOp depth_compare_op = VK_COMPARE_OP_LESS_OR_EQUAL;
    VkBool32 blend_enable = VK_FALSE;
    VkBlendFactor src_color_blend_factor = VK_BLEND_FACTOR_ONE;
    VkBlendFactor dst_color_blend_factor = VK_BLEND_FACTOR_ZERO;
    VkBlendOp color_blend_op = VK_BLEND_OP_ADD;
    VkBlendFactor src_alpha_blend_factor = VK_BLEND_FACTOR_ONE;
    VkBlendFactor dst_alpha_blend_factor = VK_BLEND_FACTOR_ZERO;
    VkBlendOp alpha_blend_op = VK_BLEND_OP_ADD;
};

struct RenderTargetState {
    uint32_t width = kDefaultRenderWidth;
    uint32_t height = kDefaultRenderHeight;
    VkFormat color_format = VK_FORMAT_R8G8B8A8_UNORM;
    VkFormat depth_format = VK_FORMAT_D32_SFLOAT;
    VkImageAspectFlags depth_aspect = VK_IMAGE_ASPECT_DEPTH_BIT;
    uint32_t d3d_color_format = 0;
    uint32_t d3d_depth_format = 0;
    int32_t viewport_x = 0;
    int32_t viewport_y = 0;
    uint32_t viewport_width = kDefaultRenderWidth;
    uint32_t viewport_height = kDefaultRenderHeight;
    float min_depth = 0.0f;
    float max_depth = 1.0f;
    bool d3d9_y_down = false;
    bool captured = false;
    uint32_t clear_color_argb = 0;
    float clear_depth = 1.0f;
    uint32_t clear_stencil = 0;
    uint32_t clear_flags = 0;
};

void check(VkResult result, const char* message) {
    if (result != VK_SUCCESS) {
        throw std::runtime_error(
            std::string(message) + " (" + std::to_string(static_cast<int>(result)) + ")");
    }
}

uint32_t memory_type(
    VkPhysicalDevice physical,
    uint32_t bits,
    VkMemoryPropertyFlags required) {

    VkPhysicalDeviceMemoryProperties props{};
    vkGetPhysicalDeviceMemoryProperties(physical, &props);
    for (uint32_t i = 0; i < props.memoryTypeCount; ++i) {
        if ((bits & (1u << i)) != 0 &&
            (props.memoryTypes[i].propertyFlags & required) == required) {
            return i;
        }
    }
    throw std::runtime_error("no compatible Vulkan memory type");
}

struct Context {
    VkInstance instance = VK_NULL_HANDLE;
    VkPhysicalDevice physical = VK_NULL_HANDLE;
    VkDevice device = VK_NULL_HANDLE;
    VkQueue queue = VK_NULL_HANDLE;
    uint32_t queue_family = 0;
    VkCommandPool command_pool = VK_NULL_HANDLE;
};

struct Buffer {
    VkBuffer handle = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
};

struct Image {
    VkImage handle = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
    VkImageView view = VK_NULL_HANDLE;
};

struct Geometry {
    GeometryHeader header{};
    CaptureGeometryMetadata capture{};
    VkIndexType index_type = VK_INDEX_TYPE_UINT32;
    uint32_t draw_index_count = 0;
    std::vector<GeometryAttribute> attributes;
    std::vector<uint8_t> vertices;
    std::vector<uint8_t> index_data;
    std::vector<uint32_t> indices;
};

struct WorldTransformExecution {
    bool present = false;
    bool executed = false;
    std::string mode = "none";
    float translation[3] = {0.0f, 0.0f, 0.0f};
    float determinant = 1.0f;
    std::vector<uint32_t> transformed_properties;
    bool has_position_probe = false;
    bool has_normal_probe = false;
    bool has_tangent_probe = false;
    bool has_tangent2_probe = false;
    float position_probe[3] = {0.0f, 0.0f, 0.0f};
    float normal_probe[3] = {0.0f, 0.0f, 0.0f};
    float tangent_probe[3] = {0.0f, 0.0f, 0.0f};
    float tangent2_probe[3] = {0.0f, 0.0f, 0.0f};
};

struct Constants {
    ConstantHeader header{};
    std::vector<uint8_t> vertex;
    std::vector<uint8_t> pixel;
};

struct TextureResource {
    TextureRecord record{};
    Buffer staging{};
    Image image{};
    VkSampler sampler = VK_NULL_HANDLE;
};

struct CubeResource {
    CubeHeader header{};
    Buffer staging{};
    Image image{};
    VkSampler sampler = VK_NULL_HANDLE;
};

struct TexturePacket {
    TextureHeader header{};
    std::vector<TextureRecord> records;
    std::vector<uint8_t> bytes;
};

struct CubePacket {
    CubeHeader header{};
    std::vector<uint8_t> bytes;
};

void destroy(Context& context, shift::vulkan::Validation& validation) {
    if (context.device) {
        vkDeviceWaitIdle(context.device);
        if (context.command_pool) {
            vkDestroyCommandPool(context.device, context.command_pool, nullptr);
        }
        vkDestroyDevice(context.device, nullptr);
    }
    if (context.instance) {
        validation.detach(context.instance);
        vkDestroyInstance(context.instance, nullptr);
    }
    context = {};
}

void create_context(Context& context, shift::vulkan::Validation& validation) {
    VkApplicationInfo app{};
    app.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
    app.pApplicationName = "SHIFT Vulkan Bundle Execute";
    app.applicationVersion = 1;
    app.pEngineName = "SHIFT";
    app.engineVersion = 1;
    app.apiVersion = VK_API_VERSION_1_1;

    VkInstanceCreateInfo instance{};
    instance.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    instance.pApplicationInfo = &app;
    validation.create_instance(instance, {}, context.instance);

    uint32_t device_count = 0;
    check(vkEnumeratePhysicalDevices(context.instance, &device_count, nullptr),
          "vkEnumeratePhysicalDevices(count) failed");
    if (device_count == 0) {
        throw std::runtime_error("no Vulkan physical devices");
    }

    std::vector<VkPhysicalDevice> devices(device_count);
    check(vkEnumeratePhysicalDevices(
        context.instance, &device_count, devices.data()),
        "vkEnumeratePhysicalDevices(data) failed");

    for (VkPhysicalDevice candidate : devices) {
        VkPhysicalDeviceProperties properties{};
        vkGetPhysicalDeviceProperties(candidate, &properties);
        if (properties.apiVersion < VK_API_VERSION_1_1) continue;
        uint32_t family_count = 0;
        vkGetPhysicalDeviceQueueFamilyProperties(
            candidate, &family_count, nullptr);
        std::vector<VkQueueFamilyProperties> families(family_count);
        vkGetPhysicalDeviceQueueFamilyProperties(
            candidate, &family_count, families.data());
        for (uint32_t family = 0; family < family_count; ++family) {
            if ((families[family].queueFlags & VK_QUEUE_GRAPHICS_BIT) != 0) {
                context.physical = candidate;
                context.queue_family = family;
                break;
            }
        }
        if (context.physical) break;
    }

    if (!context.physical) {
        throw std::runtime_error("no graphics queue family");
    }

    float priority = 1.0f;
    VkDeviceQueueCreateInfo queue{};
    queue.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
    queue.queueFamilyIndex = context.queue_family;
    queue.queueCount = 1;
    queue.pQueuePriorities = &priority;

    VkDeviceCreateInfo device{};
    device.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
    device.queueCreateInfoCount = 1;
    device.pQueueCreateInfos = &queue;
    check(vkCreateDevice(context.physical, &device, nullptr, &context.device),
          "vkCreateDevice failed");

    vkGetDeviceQueue(context.device, context.queue_family, 0, &context.queue);

    VkCommandPoolCreateInfo pool{};
    pool.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
    pool.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
    pool.queueFamilyIndex = context.queue_family;
    check(vkCreateCommandPool(
        context.device, &pool, nullptr, &context.command_pool),
        "vkCreateCommandPool failed");
}

std::vector<uint8_t> read_bytes(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary | std::ios::ate);
    if (!input) {
        throw std::runtime_error("cannot open " + path.string());
    }
    const std::streamsize size = input.tellg();
    if (size <= 0) {
        throw std::runtime_error("empty " + path.string());
    }
    input.seekg(0);
    std::vector<uint8_t> data(static_cast<size_t>(size));
    input.read(reinterpret_cast<char*>(data.data()), size);
    if (!input) {
        throw std::runtime_error("failed to read " + path.string());
    }
    return data;
}

Geometry load_geometry(const std::filesystem::path& path) {
    const auto data = read_bytes(path);
    if (data.size() < sizeof(GeometryHeader)) {
        throw std::runtime_error("geometry packet truncated");
    }

    Geometry geometry{};
    std::memcpy(&geometry.header, data.data(), sizeof(geometry.header));

    if (std::memcmp(geometry.header.magic, "SVGP", 4) != 0 ||
        (geometry.header.version != 1 &&
         geometry.header.version != 2 &&
         geometry.header.version != 3 &&
         geometry.header.version != 4)) {
        throw std::runtime_error("unsupported geometry packet");
    }
    if (geometry.header.vertex_count == 0 ||
        geometry.header.index_count == 0 ||
        geometry.header.stride == 0 ||
        geometry.header.attribute_count == 0 ||
        geometry.header.attribute_count > 16 ||
        (geometry.header.version != 4 &&
         geometry.header.index_count % 3 != 0)) {
        throw std::runtime_error("invalid geometry packet counts");
    }

    const size_t attribute_record_bytes =
        geometry.header.version >= 3
            ? sizeof(GeometryAttribute)
            : sizeof(LegacyGeometryAttribute);
    const size_t attribute_bytes =
        static_cast<size_t>(geometry.header.attribute_count) *
        attribute_record_bytes;
    const size_t metadata_offset = sizeof(GeometryHeader) + attribute_bytes;
    size_t metadata_bytes = 0;
    size_t index_element_bytes = sizeof(uint32_t);
    if (geometry.header.version == 4) {
        metadata_bytes = sizeof(CaptureGeometryMetadata);
        if (data.size() < metadata_offset + metadata_bytes) {
            throw std::runtime_error("capture geometry metadata truncated");
        }
        std::memcpy(
            &geometry.capture,
            data.data() + metadata_offset,
            sizeof(geometry.capture));
        if (geometry.capture.index_format_bits == 16u) {
            geometry.index_type = VK_INDEX_TYPE_UINT16;
            index_element_bytes = sizeof(uint16_t);
        } else if (geometry.capture.index_format_bits == 32u) {
            geometry.index_type = VK_INDEX_TYPE_UINT32;
        } else {
            throw std::runtime_error("unsupported capture index width");
        }
        if (geometry.capture.draw_index_count == 0u ||
            geometry.capture.draw_index_count % 3u != 0u ||
            geometry.header.first_index > geometry.header.index_count ||
            geometry.capture.draw_index_count >
                geometry.header.index_count - geometry.header.first_index) {
            throw std::runtime_error("invalid capture draw index range");
        }
        geometry.draw_index_count = geometry.capture.draw_index_count;
    } else {
        geometry.draw_index_count = geometry.header.index_count;
    }
    const size_t vertex_bytes =
        (static_cast<size_t>(geometry.header.vertex_count) *
             geometry.header.stride) +
        geometry.capture.vertex_buffer_offset;
    const size_t index_bytes =
        static_cast<size_t>(geometry.header.index_count) *
        index_element_bytes;
    const size_t expected =
        metadata_offset + metadata_bytes + vertex_bytes + index_bytes;
    if (expected != data.size()) {
        throw std::runtime_error("geometry packet size mismatch");
    }

    geometry.attributes.resize(geometry.header.attribute_count);
    if (geometry.header.version >= 3) {
        std::memcpy(
            geometry.attributes.data(),
            data.data() + sizeof(GeometryHeader),
            attribute_bytes);
    } else {
        for (uint32_t index = 0;
             index < geometry.header.attribute_count;
             ++index) {
            LegacyGeometryAttribute legacy{};
            std::memcpy(
                &legacy,
                data.data() + sizeof(GeometryHeader) +
                    static_cast<size_t>(index) *
                        sizeof(LegacyGeometryAttribute),
                sizeof(legacy));
            geometry.attributes[index] = {
                legacy.location,
                legacy.format,
                legacy.offset,
                legacy.stride,
                legacy.location == 0u ? 200u : 0u,
            };
        }
    }

    if (geometry.header.version == 1) {
        if (geometry.header.attribute_count != 1 ||
            geometry.attributes[0].format != 1) {
            throw std::runtime_error("invalid version-1 geometry packet");
        }
        // Version 1 used format code 1 for FLOAT3. Version 2 reserves code 1 for FLOAT2.
        geometry.attributes[0].format = 2;
    }

    const size_t vertices_offset = metadata_offset + metadata_bytes;
    const size_t indices_offset = vertices_offset + vertex_bytes;
    geometry.vertices.assign(
        data.begin() + static_cast<std::ptrdiff_t>(vertices_offset),
        data.begin() + static_cast<std::ptrdiff_t>(indices_offset));
    geometry.indices.resize(geometry.header.index_count);
    geometry.index_data.assign(
        data.begin() + static_cast<std::ptrdiff_t>(indices_offset), data.end());
    if (geometry.header.version == 4 &&
        geometry.capture.index_format_bits == 16u) {
        for (uint32_t index = 0;
             index < geometry.header.index_count;
             ++index) {
            uint16_t value = 0;
            std::memcpy(
                &value,
                geometry.index_data.data() +
                    static_cast<size_t>(index) * sizeof(value),
                sizeof(value));
            geometry.indices[index] = value;
        }
    } else {
        std::memcpy(
            geometry.indices.data(),
            geometry.index_data.data(),
            index_bytes);
    }

    bool position_seen = false;
    auto attribute_size = [](uint32_t format) -> uint32_t {
        switch (format) {
            case 1: return 8;
            case 2: return 12;
            case 3: return 16;
            case 4: return 4;
            case 5: return 4;
            default: return 0;
        }
    };
    for (const auto& attribute : geometry.attributes) {
        const uint32_t size = attribute_size(attribute.format);
        if (size == 0 ||
            attribute.location > 15 ||
            attribute.offset > geometry.header.stride ||
            size > geometry.header.stride - attribute.offset ||
            attribute.stride != geometry.header.stride) {
            throw std::runtime_error("invalid vertex attribute");
        }
        if (geometry.header.version == 3 &&
            attribute.property_id == 0u) {
            throw std::runtime_error(
                "SVGP v3 attribute is missing SHIFT property identity");
        }
        if (attribute.location == 0) {
            if (attribute.format != 2 || position_seen ||
                (geometry.header.version != 4 &&
                 attribute.property_id != 200u)) {
                throw std::runtime_error(
                    "POSITION0 must be FLOAT3 property 200 at location 0");
            }
            position_seen = true;
        }
    }
    if (!position_seen) {
        throw std::runtime_error("geometry packet has no POSITION0");
    }
    for (uint32_t draw_index = 0;
         draw_index < geometry.draw_index_count;
         ++draw_index) {
        const uint32_t index = geometry.indices[
            geometry.header.first_index + draw_index];
        const int64_t vertex =
            static_cast<int64_t>(index) + geometry.capture.base_vertex;
        if (vertex < 0 ||
            vertex >= static_cast<int64_t>(geometry.header.vertex_count)) {
            throw std::runtime_error("draw index exceeds vertex range");
        }
    }
    return geometry;
}

WorldTransformExecution apply_world_transform_affine(
    const std::filesystem::path& root,
    Geometry& geometry) {

    WorldTransformExecution result{};
    const std::filesystem::path path = root / "world_transform.svwt";
    if (!std::filesystem::is_regular_file(path)) {
        return result;
    }
    result.present = true;

    const auto data = read_bytes(path);
    if (data.size() != sizeof(WorldTransformHeader) + 16u * sizeof(float)) {
        throw std::runtime_error("SVWT packet size mismatch");
    }

    WorldTransformHeader header{};
    std::memcpy(&header, data.data(), sizeof(header));
    if (std::memcmp(header.magic, "SVWT", 4) != 0 ||
        header.version != 1u ||
        header.convention != 1u ||
        header.matrix_bytes != 16u * sizeof(float)) {
        throw std::runtime_error("unsupported SVWT packet");
    }

    float matrix[16]{};
    std::memcpy(matrix, data.data() + sizeof(header), sizeof(matrix));
    for (float value : matrix) {
        if (!std::isfinite(value)) {
            throw std::runtime_error("SVWT matrix contains non-finite scalar");
        }
    }

    constexpr float kTolerance = 1.0e-5f;
    constexpr float kSingularTolerance = 1.0e-8f;
    if (std::fabs(matrix[3]) > kTolerance ||
        std::fabs(matrix[7]) > kTolerance ||
        std::fabs(matrix[11]) > kTolerance ||
        std::fabs(matrix[15] - 1.0f) > kTolerance) {
        throw std::runtime_error("SVWT matrix is not affine D3D row-vector form");
    }

    const float a = matrix[0];
    const float b = matrix[1];
    const float c0 = matrix[2];
    const float d = matrix[4];
    const float e = matrix[5];
    const float f0 = matrix[6];
    const float g = matrix[8];
    const float h = matrix[9];
    const float i = matrix[10];

    const float determinant =
        a * (e * i - f0 * h) -
        b * (d * i - f0 * g) +
        c0 * (d * h - e * g);
    if (!std::isfinite(determinant) ||
        std::fabs(determinant) <= kSingularTolerance) {
        throw std::runtime_error(
            "SVWT affine linear transform is singular");
    }
    result.determinant = determinant;

    const bool linear_identity =
        std::fabs(a - 1.0f) <= kTolerance &&
        std::fabs(b) <= kTolerance &&
        std::fabs(c0) <= kTolerance &&
        std::fabs(d) <= kTolerance &&
        std::fabs(e - 1.0f) <= kTolerance &&
        std::fabs(f0) <= kTolerance &&
        std::fabs(g) <= kTolerance &&
        std::fabs(h) <= kTolerance &&
        std::fabs(i - 1.0f) <= kTolerance;

    if (!linear_identity &&
        geometry.header.version < 3u &&
        geometry.attributes.size() > 1u) {
        throw std::runtime_error(
            "SVWT affine execution requires SVGP v3 semantic IDs "
            "when legacy geometry contains non-position attributes");
    }

    const float inv_det = 1.0f / determinant;
    const float inverse[9] = {
        (e * i - f0 * h) * inv_det,
        (c0 * h - b * i) * inv_det,
        (b * f0 - c0 * e) * inv_det,
        (f0 * g - d * i) * inv_det,
        (a * i - c0 * g) * inv_det,
        (c0 * d - a * f0) * inv_det,
        (d * h - e * g) * inv_det,
        (b * g - a * h) * inv_det,
        (a * e - b * d) * inv_det,
    };

    const GeometryAttribute* position = nullptr;
    std::vector<const GeometryAttribute*> normals;
    std::vector<const GeometryAttribute*> tangents;
    std::vector<const GeometryAttribute*> tangents2;

    for (const auto& attribute : geometry.attributes) {
        switch (attribute.property_id) {
            case 200u:
                if (position != nullptr || attribute.format != 2u) {
                    throw std::runtime_error(
                        "SVWT execution requires one FLOAT3 POSITION property 200");
                }
                position = &attribute;
                break;
            case 220u:
                if (attribute.format != 2u) {
                    throw std::runtime_error(
                        "SVWT NORMAL property 220 must be FLOAT3");
                }
                normals.push_back(&attribute);
                break;
            case 240u:
                if (attribute.format != 2u) {
                    throw std::runtime_error(
                        "SVWT TANGENT property 240 must be FLOAT3");
                }
                tangents.push_back(&attribute);
                break;
            case 250u:
                if (attribute.format != 2u) {
                    throw std::runtime_error(
                        "SVWT TANGENT2 property 250 must be FLOAT3");
                }
                tangents2.push_back(&attribute);
                break;
            default:
                break;
        }
    }
    if (position == nullptr) {
        throw std::runtime_error(
            "SVWT execution requires POSITION property 200");
    }

    result.translation[0] = matrix[12];
    result.translation[1] = matrix[13];
    result.translation[2] = matrix[14];

    auto load_float3 = [&](uint32_t vertex,
                           const GeometryAttribute& attribute,
                           float out[3]) {
        const size_t offset =
            static_cast<size_t>(vertex) * geometry.header.stride +
            attribute.offset;
        if (offset + 3u * sizeof(float) > geometry.vertices.size()) {
            throw std::runtime_error(
                "SVWT semantic write exceeds vertex buffer");
        }
        std::memcpy(out, geometry.vertices.data() + offset, 3u * sizeof(float));
    };
    auto store_float3 = [&](uint32_t vertex,
                            const GeometryAttribute& attribute,
                            const float value[3]) {
        const size_t offset =
            static_cast<size_t>(vertex) * geometry.header.stride +
            attribute.offset;
        std::memcpy(
            geometry.vertices.data() + offset,
            value,
            3u * sizeof(float));
    };
    auto normalize = [&](float value[3], const char* semantic) {
        const float length_sq =
            value[0] * value[0] +
            value[1] * value[1] +
            value[2] * value[2];
        if (!std::isfinite(length_sq) ||
            length_sq <= kSingularTolerance * kSingularTolerance) {
            throw std::runtime_error(
                std::string("SVWT ") + semantic +
                " collapses under affine transform");
        }
        const float inv_length = 1.0f / std::sqrt(length_sq);
        value[0] *= inv_length;
        value[1] *= inv_length;
        value[2] *= inv_length;
    };
    auto transform_direction = [&](float value[3]) {
        const float x = value[0];
        const float y = value[1];
        const float z = value[2];
        value[0] = x * a + y * d + z * g;
        value[1] = x * b + y * e + z * h;
        value[2] = x * c0 + y * f0 + z * i;
    };
    auto transform_normal = [&](float value[3]) {
        const float x = value[0];
        const float y = value[1];
        const float z = value[2];
        // Row-vector normal transform: n' = n * transpose(inverse(A)).
        value[0] =
            x * inverse[0] + y * inverse[1] + z * inverse[2];
        value[1] =
            x * inverse[3] + y * inverse[4] + z * inverse[5];
        value[2] =
            x * inverse[6] + y * inverse[7] + z * inverse[8];
    };

    for (uint32_t vertex = 0; vertex < geometry.header.vertex_count; ++vertex) {
        float value[3]{};
        load_float3(vertex, *position, value);
        const float x = value[0];
        const float y = value[1];
        const float z = value[2];
        value[0] = x * a + y * d + z * g + result.translation[0];
        value[1] = x * b + y * e + z * h + result.translation[1];
        value[2] = x * c0 + y * f0 + z * i + result.translation[2];
        store_float3(vertex, *position, value);
        if (vertex == 0u) {
            result.has_position_probe = true;
            std::memcpy(
                result.position_probe,
                value,
                3u * sizeof(float));
        }

        for (const GeometryAttribute* attribute : normals) {
            load_float3(vertex, *attribute, value);
            transform_normal(value);
            normalize(value, "NORMAL");
            store_float3(vertex, *attribute, value);
            if (vertex == 0u && !result.has_normal_probe) {
                result.has_normal_probe = true;
                std::memcpy(
                    result.normal_probe,
                    value,
                    3u * sizeof(float));
            }
        }
        for (const GeometryAttribute* attribute : tangents) {
            load_float3(vertex, *attribute, value);
            transform_direction(value);
            normalize(value, "TANGENT");
            store_float3(vertex, *attribute, value);
            if (vertex == 0u && !result.has_tangent_probe) {
                result.has_tangent_probe = true;
                std::memcpy(
                    result.tangent_probe,
                    value,
                    3u * sizeof(float));
            }
        }
        for (const GeometryAttribute* attribute : tangents2) {
            load_float3(vertex, *attribute, value);
            transform_direction(value);
            normalize(value, "TANGENT2");
            store_float3(vertex, *attribute, value);
            if (vertex == 0u && !result.has_tangent2_probe) {
                result.has_tangent2_probe = true;
                std::memcpy(
                    result.tangent2_probe,
                    value,
                    3u * sizeof(float));
            }
        }
    }

    result.transformed_properties.push_back(200u);
    if (!normals.empty()) result.transformed_properties.push_back(220u);
    if (!tangents.empty()) result.transformed_properties.push_back(240u);
    if (!tangents2.empty()) result.transformed_properties.push_back(250u);
    result.mode = linear_identity
        ? "translation"
        : geometry.header.version >= 3u
            ? "affine-semantic-v3"
            : "affine-position-only-legacy";
    result.executed = true;
    return result;
}

Constants load_constants(const std::filesystem::path& path) {
    const auto data = read_bytes(path);
    if (data.size() != sizeof(ConstantHeader) + 2u * kConstantBytes) {
        throw std::runtime_error("constant packet size mismatch");
    }

    Constants constants{};
    std::memcpy(&constants.header, data.data(), sizeof(constants.header));
    if (std::memcmp(constants.header.magic, "SVCP", 4) != 0 ||
        constants.header.version != 1 ||
        constants.header.max_registers != 256 ||
        constants.header.register_bytes != 16) {
        throw std::runtime_error("unsupported constant packet");
    }

    const size_t body = sizeof(ConstantHeader);
    constants.vertex.assign(
        data.begin() + static_cast<std::ptrdiff_t>(body),
        data.begin() + static_cast<std::ptrdiff_t>(body + kConstantBytes));
    constants.pixel.assign(
        data.begin() + static_cast<std::ptrdiff_t>(body + kConstantBytes),
        data.end());
    return constants;
}

TexturePacket load_texture_packet(const std::filesystem::path& path) {
    const auto data = read_bytes(path);
    if (data.size() < sizeof(TextureHeader)) {
        throw std::runtime_error("texture packet truncated");
    }

    TexturePacket packet{};
    std::memcpy(&packet.header, data.data(), sizeof(packet.header));
    if (std::memcmp(packet.header.magic, "SVTP", 4) != 0 ||
        packet.header.version != 1 ||
        packet.header.descriptor_set != 1 ||
        packet.header.texture_count == 0 ||
        packet.header.texture_count > 16) {
        throw std::runtime_error("unsupported texture packet");
    }

    const size_t records =
        static_cast<size_t>(packet.header.texture_count) *
        sizeof(TextureRecord);
    const size_t pixels = sizeof(TextureHeader) + records;
    if (data.size() < pixels) {
        throw std::runtime_error("texture packet record table truncated");
    }
    packet.records.resize(packet.header.texture_count);
    std::memcpy(
        packet.records.data(), data.data() + sizeof(TextureHeader), records);
    for (const auto& record : packet.records) {
        const uint64_t expected_pixels =
            static_cast<uint64_t>(record.width) *
            static_cast<uint64_t>(record.height) * 4u;
        if (record.register_index > 15 ||
            record.width == 0 || record.height == 0 ||
            expected_pixels > std::numeric_limits<uint32_t>::max() ||
            record.pixel_bytes != static_cast<uint32_t>(expected_pixels) ||
            record.pixel_offset < pixels ||
            static_cast<uint64_t>(record.pixel_offset) + record.pixel_bytes > data.size() ||
            record.sampler_mode < 1 || record.sampler_mode > 4) {
            throw std::runtime_error("invalid texture packet record");
        }
    }
    packet.bytes = data;
    return packet;
}

CubePacket load_cube_packet(const std::filesystem::path& path) {
    const auto data = read_bytes(path);
    if (data.size() < sizeof(CubeHeader)) {
        throw std::runtime_error("cube packet truncated");
    }
    CubePacket packet{};
    std::memcpy(&packet.header, data.data(), sizeof(packet.header));
    if (std::memcmp(packet.header.magic, "SVCP", 4) != 0 ||
        packet.header.version != 1 ||
        packet.header.register_index != 3 ||
        packet.header.face_count != 6) {
        throw std::runtime_error("unsupported cube packet");
    }
    const uint64_t face_bytes =
        static_cast<uint64_t>(packet.header.width) *
        static_cast<uint64_t>(packet.header.height) * 4u;
    const uint64_t total = face_bytes * 6u;
    if (packet.header.width == 0 || packet.header.height == 0 ||
        face_bytes > std::numeric_limits<uint32_t>::max() ||
        total > std::numeric_limits<size_t>::max() ||
        packet.header.face_bytes != static_cast<uint32_t>(face_bytes) ||
        data.size() != sizeof(CubeHeader) + static_cast<size_t>(total)) {
        throw std::runtime_error("cube packet size mismatch");
    }
    packet.bytes.assign(
        data.begin() + sizeof(CubeHeader),
        data.end());
    return packet;
}

std::filesystem::path find_shader(
    const std::filesystem::path& root,
    const std::string& needle) {

    const auto shader_root = root / "spirv";
    if (!std::filesystem::is_directory(shader_root)) {
        throw std::runtime_error("bundle SPIR-V directory is missing");
    }
    std::filesystem::path selected;
    for (const auto& entry : std::filesystem::directory_iterator(shader_root)) {
        if (!entry.is_regular_file()) continue;
        const std::string name = entry.path().filename().string();
        if (name.find(needle) != std::string::npos) {
            if (!selected.empty()) {
                throw std::runtime_error("multiple SPIR-V files match " + needle);
            }
            selected = entry.path();
        }
    }
    if (selected.empty()) {
        throw std::runtime_error("SPIR-V shader not found: " + needle);
    }
    return selected;
}

VkShaderModule make_shader(
    Context& ctx,
    const std::filesystem::path& path) {

    const auto data = read_bytes(path);
    if (data.size() % 4 != 0) {
        throw std::runtime_error("SPIR-V is not word aligned: " + path.string());
    }
    VkShaderModuleCreateInfo info{};
    info.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
    info.codeSize = data.size();
    info.pCode = reinterpret_cast<const uint32_t*>(data.data());
    VkShaderModule module = VK_NULL_HANDLE;
    check(vkCreateShaderModule(
        ctx.device, &info, nullptr, &module),
        "vkCreateShaderModule failed");
    return module;
}

void create_buffer(
    Context& ctx,
    VkDeviceSize size,
    VkBufferUsageFlags usage,
    VkMemoryPropertyFlags properties,
    Buffer& out) {

    VkBufferCreateInfo info{};
    info.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
    info.size = size;
    info.usage = usage;
    check(vkCreateBuffer(ctx.device, &info, nullptr, &out.handle),
          "vkCreateBuffer failed");

    VkMemoryRequirements req{};
    vkGetBufferMemoryRequirements(ctx.device, out.handle, &req);

    VkMemoryAllocateInfo alloc{};
    alloc.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    alloc.allocationSize = req.size;
    alloc.memoryTypeIndex = memory_type(
        ctx.physical, req.memoryTypeBits, properties);
    check(vkAllocateMemory(
        ctx.device, &alloc, nullptr, &out.memory),
        "vkAllocateMemory buffer failed");
    check(vkBindBufferMemory(ctx.device, out.handle, out.memory, 0),
          "vkBindBufferMemory failed");
}

void create_image(
    Context& ctx,
    uint32_t width,
    uint32_t height,
    uint32_t layers,
    VkFormat format,
    VkImageCreateFlags flags,
    VkImageUsageFlags usage,
    Image& out,
    VkImageAspectFlags aspect = VK_IMAGE_ASPECT_COLOR_BIT) {

    VkImageCreateInfo info{};
    info.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
    info.flags = flags;
    info.imageType = VK_IMAGE_TYPE_2D;
    info.format = format;
    info.extent = {width, height, 1};
    info.mipLevels = 1;
    info.arrayLayers = layers;
    info.samples = VK_SAMPLE_COUNT_1_BIT;
    info.tiling = VK_IMAGE_TILING_OPTIMAL;
    info.usage = usage;
    info.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    check(vkCreateImage(ctx.device, &info, nullptr, &out.handle),
          "vkCreateImage failed");

    VkMemoryRequirements req{};
    vkGetImageMemoryRequirements(ctx.device, out.handle, &req);

    VkMemoryAllocateInfo alloc{};
    alloc.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    alloc.allocationSize = req.size;
    alloc.memoryTypeIndex = memory_type(
        ctx.physical, req.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    check(vkAllocateMemory(ctx.device, &alloc, nullptr, &out.memory),
          "vkAllocateMemory image failed");
    check(vkBindImageMemory(ctx.device, out.handle, out.memory, 0),
          "vkBindImageMemory failed");

    VkImageViewCreateInfo view{};
    view.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
    view.image = out.handle;
    view.viewType = layers == 6 ? VK_IMAGE_VIEW_TYPE_CUBE : VK_IMAGE_VIEW_TYPE_2D;
    view.format = format;
    view.subresourceRange.aspectMask = aspect;
    view.subresourceRange.levelCount = 1;
    view.subresourceRange.layerCount = layers;
    check(vkCreateImageView(ctx.device, &view, nullptr, &out.view),
          "vkCreateImageView failed");
}

VkSampler sampler_for_mode(Context& ctx, uint32_t mode) {
    const bool linear = mode == 2 || mode == 4;
    const bool clamp = mode == 3 || mode == 4;

    VkSamplerCreateInfo info{};
    info.sType = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO;
    info.magFilter = linear ? VK_FILTER_LINEAR : VK_FILTER_NEAREST;
    info.minFilter = linear ? VK_FILTER_LINEAR : VK_FILTER_NEAREST;
    info.mipmapMode = VK_SAMPLER_MIPMAP_MODE_NEAREST;
    info.addressModeU = clamp ? VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE :
                                VK_SAMPLER_ADDRESS_MODE_REPEAT;
    info.addressModeV = clamp ? VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE :
                                VK_SAMPLER_ADDRESS_MODE_REPEAT;
    info.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    info.maxLod = 1.0f;

    VkSampler sampler = VK_NULL_HANDLE;
    check(vkCreateSampler(ctx.device, &info, nullptr, &sampler),
          "vkCreateSampler failed");
    return sampler;
}

void transition(
    VkCommandBuffer cmd,
    VkImage image,
    uint32_t layer_count,
    VkImageLayout old_layout,
    VkImageLayout new_layout,
    VkAccessFlags src_access,
    VkAccessFlags dst_access,
    VkPipelineStageFlags src_stage,
    VkPipelineStageFlags dst_stage) {

    VkImageMemoryBarrier barrier{};
    barrier.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
    barrier.srcAccessMask = src_access;
    barrier.dstAccessMask = dst_access;
    barrier.oldLayout = old_layout;
    barrier.newLayout = new_layout;
    barrier.image = image;
    barrier.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    barrier.subresourceRange.levelCount = 1;
    barrier.subresourceRange.layerCount = layer_count;
    vkCmdPipelineBarrier(
        cmd, src_stage, dst_stage, 0,
        0, nullptr, 0, nullptr, 1, &barrier);
}

void require_native_submission_gate(const std::filesystem::path& root) {
    const std::filesystem::path gate_path = root / "native_submission_gate.json";
    if (!std::filesystem::is_regular_file(gate_path)) {
        throw std::runtime_error(
            "native submission gate missing: " + gate_path.string());
    }

    std::ifstream gate(gate_path, std::ios::binary);
    if (!gate) {
        throw std::runtime_error(
            "cannot open native submission gate: " + gate_path.string());
    }
    const std::string contents(
        (std::istreambuf_iterator<char>(gate)),
        std::istreambuf_iterator<char>());

    if (contents.find("\"format\": \"SHIFT.NativeSubmissionGate/1\"") ==
            std::string::npos ||
        contents.find("\"ready\": true") == std::string::npos ||
        contents.find("\"blocking_reasons\": []") == std::string::npos) {
        throw std::runtime_error(
            "native submission gate is not ready");
    }
}

double json_number(const std::string& contents, const char* field) {
    const std::string key = "\"" + std::string(field) + "\"";
    const size_t key_pos = contents.find(key);
    if (key_pos == std::string::npos) {
        throw std::runtime_error(
            "render target field is missing: " + std::string(field));
    }
    const size_t colon = contents.find(':', key_pos + key.size());
    if (colon == std::string::npos) {
        throw std::runtime_error("invalid render target JSON");
    }
    size_t end = 0;
    const double value = std::stod(contents.substr(colon + 1), &end);
    if (end == 0 || !std::isfinite(value)) {
        throw std::runtime_error(
            "invalid render target number: " + std::string(field));
    }
    return value;
}

uint32_t json_u32(const std::string& contents, const char* field) {
    const double value = json_number(contents, field);
    if (value < 0.0 || value > std::numeric_limits<uint32_t>::max() ||
        std::floor(value) != value) {
        throw std::runtime_error(
            "invalid render target integer: " + std::string(field));
    }
    return static_cast<uint32_t>(value);
}

int32_t json_i32(const std::string& contents, const char* field) {
    const double value = json_number(contents, field);
    if (value < std::numeric_limits<int32_t>::min() ||
        value > std::numeric_limits<int32_t>::max() ||
        std::floor(value) != value) {
        throw std::runtime_error(
            "invalid render target integer: " + std::string(field));
    }
    return static_cast<int32_t>(value);
}

RenderTargetState load_render_target(
    const std::filesystem::path& root) {
    RenderTargetState out{};
    out.viewport_width = out.width;
    out.viewport_height = out.height;
    const std::filesystem::path state_path = root / "render_target.json";
    if (!std::filesystem::is_regular_file(state_path)) return out;

    std::ifstream input(state_path, std::ios::binary);
    if (!input) {
        throw std::runtime_error(
            "cannot open render target state: " + state_path.string());
    }
    const std::string contents(
        (std::istreambuf_iterator<char>(input)),
        std::istreambuf_iterator<char>());
    if (contents.find("\"format\": \"SHIFT.D3D9CaptureRenderTarget/1\"") ==
            std::string::npos ||
        contents.find("\"ready\": true") == std::string::npos ||
        contents.find("\"d3d9_y_down\": true") == std::string::npos) {
        throw std::runtime_error("capture render target state is invalid");
    }
    out.width = json_u32(contents, "target_width");
    out.height = json_u32(contents, "target_height");
    out.viewport_x = json_i32(contents, "viewport_x");
    out.viewport_y = json_i32(contents, "viewport_y");
    out.viewport_width = json_u32(contents, "viewport_width");
    out.viewport_height = json_u32(contents, "viewport_height");
    out.d3d_color_format = json_u32(contents, "surface_format");
    if (out.d3d_color_format == 21u) {
        out.color_format = VK_FORMAT_B8G8R8A8_UNORM;
    } else if (out.d3d_color_format == 113u) {
        out.color_format = VK_FORMAT_R16G16B16A16_SFLOAT;
    } else if (out.d3d_color_format == 114u) {
        out.color_format = VK_FORMAT_R32_SFLOAT;
    } else {
        throw std::runtime_error(
            "unsupported captured D3D9 render-target format: " +
            std::to_string(out.d3d_color_format));
    }
    out.d3d_depth_format = json_u32(contents, "depth_surface_format");
    if (out.d3d_depth_format == 75u) {
        out.depth_format = VK_FORMAT_D24_UNORM_S8_UINT;
        out.depth_aspect =
            VK_IMAGE_ASPECT_DEPTH_BIT | VK_IMAGE_ASPECT_STENCIL_BIT;
    } else if (out.d3d_depth_format == 80u) {
        out.depth_format = VK_FORMAT_D16_UNORM;
        out.depth_aspect = VK_IMAGE_ASPECT_DEPTH_BIT;
    } else if (out.d3d_depth_format != 0u) {
        throw std::runtime_error(
            "unsupported captured D3D9 depth format: " +
            std::to_string(out.d3d_depth_format));
    }
    if (out.d3d_depth_format != 0u &&
        (json_u32(contents, "depth_surface_width") != out.width ||
         json_u32(contents, "depth_surface_height") != out.height)) {
        throw std::runtime_error(
            "captured color and depth surface dimensions do not match");
    }
    out.min_depth = static_cast<float>(json_number(contents, "min_depth"));
    out.max_depth = static_cast<float>(json_number(contents, "max_depth"));
    out.d3d9_y_down = true;
    out.captured = true;
    out.clear_color_argb = json_u32(contents, "clear_color_argb");
    out.clear_depth = static_cast<float>(json_number(contents, "clear_depth"));
    out.clear_stencil = json_u32(contents, "clear_stencil");
    out.clear_flags = json_u32(contents, "clear_flags");
    if (out.width == 0 || out.height == 0 ||
        out.viewport_width == 0 || out.viewport_height == 0 ||
        out.viewport_x < 0 || out.viewport_y < 0 ||
        static_cast<uint64_t>(out.viewport_x) + out.viewport_width > out.width ||
        static_cast<uint64_t>(out.viewport_y) + out.viewport_height > out.height ||
        out.min_depth < 0.0f || out.max_depth > 1.0f ||
        out.min_depth > out.max_depth ||
        out.clear_depth < 0.0f || out.clear_depth > 1.0f ||
        (out.clear_flags & 0x3u) != 0x3u ||
        out.width > static_cast<uint32_t>(std::numeric_limits<int32_t>::max()) ||
        out.height > static_cast<uint32_t>(std::numeric_limits<int32_t>::max()) ||
        out.viewport_height > static_cast<uint32_t>(std::numeric_limits<int32_t>::max())) {
        throw std::runtime_error("capture render target bounds are invalid");
    }
    return out;
}

PipelineState load_pipeline_state(
    const std::filesystem::path& root) {
    PipelineState out{};
    const std::filesystem::path state_path =
        root / "pipeline_state.json";
    if (!std::filesystem::is_regular_file(state_path)) {
        return out;
    }
    std::ifstream state(state_path, std::ios::binary);
    if (!state) {
        throw std::runtime_error(
            "cannot open pipeline state: " + state_path.string());
    }
    const std::string contents(
        (std::istreambuf_iterator<char>(state)),
        std::istreambuf_iterator<char>());

    const bool legacy =
        contents.find("\"format\": \"SHIFT.MaterialCullState/1\"") !=
        std::string::npos;
    const bool pipeline =
        contents.find("\"format\": \"SHIFT.MaterialPipelineState/1\"") !=
        std::string::npos;
    if ((!legacy && !pipeline) ||
        contents.find("\"ready\": true") == std::string::npos) {
        throw std::runtime_error(
            "bundle pipeline state is invalid or blocked");
    }

    auto has = [&](const std::string& value) {
        return contents.find(value) != std::string::npos;
    };
    auto required_bool = [&](const char* field) -> VkBool32 {
        const std::string prefix = "\"" + std::string(field) + "\": ";
        if (has(prefix + "true")) return VK_TRUE;
        if (has(prefix + "false")) return VK_FALSE;
        throw std::runtime_error(
            "bundle pipeline boolean is missing: " +
            std::string(field));
    };
    auto require_token = [&](const char* field,
                             const std::vector<std::pair<std::string, int>>& values)
        -> int {
        for (const auto& row : values) {
            const std::string needle =
                "\"" + std::string(field) + "\": \"" +
                row.first + "\"";
            if (has(needle)) return row.second;
        }
        throw std::runtime_error(
            "bundle pipeline enum is missing/unsupported: " +
            std::string(field));
    };

    if (has("\"vulkan_cull_mode\": \"VK_CULL_MODE_NONE\"") ||
        has("\"cull_mode\": \"VK_CULL_MODE_NONE\"")) {
        out.cull_mode = VK_CULL_MODE_NONE;
    } else if (
        has("\"vulkan_cull_mode\": \"VK_CULL_MODE_BACK_BIT\"") ||
        has("\"cull_mode\": \"VK_CULL_MODE_BACK_BIT\"")) {
        out.cull_mode = VK_CULL_MODE_BACK_BIT;
    } else if (
        has("\"vulkan_cull_mode\": \"VK_CULL_MODE_FRONT_BIT\"") ||
        has("\"cull_mode\": \"VK_CULL_MODE_FRONT_BIT\"")) {
        out.cull_mode = VK_CULL_MODE_FRONT_BIT;
    } else {
        throw std::runtime_error(
            "bundle pipeline state has unsupported cull mode");
    }

    if (legacy) return out;

    out.depth_test_enable = required_bool("depth_test_enable");
    out.depth_write_enable = required_bool("depth_write_enable");
    out.blend_enable = required_bool("blend_enable");
    out.depth_compare_op = static_cast<VkCompareOp>(require_token(
        "depth_compare_op",
        {
            {"VK_COMPARE_OP_NEVER", VK_COMPARE_OP_NEVER},
            {"VK_COMPARE_OP_LESS", VK_COMPARE_OP_LESS},
            {"VK_COMPARE_OP_EQUAL", VK_COMPARE_OP_EQUAL},
            {"VK_COMPARE_OP_LESS_OR_EQUAL", VK_COMPARE_OP_LESS_OR_EQUAL},
            {"VK_COMPARE_OP_GREATER", VK_COMPARE_OP_GREATER},
            {"VK_COMPARE_OP_NOT_EQUAL", VK_COMPARE_OP_NOT_EQUAL},
            {"VK_COMPARE_OP_GREATER_OR_EQUAL", VK_COMPARE_OP_GREATER_OR_EQUAL},
            {"VK_COMPARE_OP_ALWAYS", VK_COMPARE_OP_ALWAYS},
        }));
    const std::vector<std::pair<std::string, int>> factors = {
        {"VK_BLEND_FACTOR_ZERO", VK_BLEND_FACTOR_ZERO},
        {"VK_BLEND_FACTOR_ONE", VK_BLEND_FACTOR_ONE},
        {"VK_BLEND_FACTOR_SRC_COLOR", VK_BLEND_FACTOR_SRC_COLOR},
        {"VK_BLEND_FACTOR_ONE_MINUS_SRC_COLOR", VK_BLEND_FACTOR_ONE_MINUS_SRC_COLOR},
        {"VK_BLEND_FACTOR_SRC_ALPHA", VK_BLEND_FACTOR_SRC_ALPHA},
        {"VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA", VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA},
        {"VK_BLEND_FACTOR_DST_ALPHA", VK_BLEND_FACTOR_DST_ALPHA},
        {"VK_BLEND_FACTOR_ONE_MINUS_DST_ALPHA", VK_BLEND_FACTOR_ONE_MINUS_DST_ALPHA},
        {"VK_BLEND_FACTOR_DST_COLOR", VK_BLEND_FACTOR_DST_COLOR},
        {"VK_BLEND_FACTOR_ONE_MINUS_DST_COLOR", VK_BLEND_FACTOR_ONE_MINUS_DST_COLOR},
        {"VK_BLEND_FACTOR_SRC_ALPHA_SATURATE", VK_BLEND_FACTOR_SRC_ALPHA_SATURATE},
    };
    const std::vector<std::pair<std::string, int>> ops = {
        {"VK_BLEND_OP_ADD", VK_BLEND_OP_ADD},
        {"VK_BLEND_OP_SUBTRACT", VK_BLEND_OP_SUBTRACT},
        {"VK_BLEND_OP_REVERSE_SUBTRACT", VK_BLEND_OP_REVERSE_SUBTRACT},
        {"VK_BLEND_OP_MIN", VK_BLEND_OP_MIN},
        {"VK_BLEND_OP_MAX", VK_BLEND_OP_MAX},
    };
    out.src_color_blend_factor = static_cast<VkBlendFactor>(
        require_token("src_color_blend_factor", factors));
    out.dst_color_blend_factor = static_cast<VkBlendFactor>(
        require_token("dst_color_blend_factor", factors));
    out.color_blend_op = static_cast<VkBlendOp>(
        require_token("color_blend_op", ops));
    out.src_alpha_blend_factor = static_cast<VkBlendFactor>(
        require_token("src_alpha_blend_factor", factors));
    out.dst_alpha_blend_factor = static_cast<VkBlendFactor>(
        require_token("dst_alpha_blend_factor", factors));
    out.alpha_blend_op = static_cast<VkBlendOp>(
        require_token("alpha_blend_op", ops));
    return out;
}

VkCullModeFlags load_pipeline_cull_mode(
    const std::filesystem::path& root) {
    return load_pipeline_state(root).cull_mode;
}

uint32_t readback_bytes_per_pixel(VkFormat format) {
    switch (format) {
    case VK_FORMAT_R32_SFLOAT:
    case VK_FORMAT_R8G8B8A8_UNORM:
    case VK_FORMAT_B8G8R8A8_UNORM:
        return 4;
    case VK_FORMAT_R16G16B16A16_SFLOAT:
        return 8;
    default:
        throw std::runtime_error("unsupported render-target readback format");
    }
}

const char* render_target_format_name(VkFormat format) {
    switch (format) {
    case VK_FORMAT_R32_SFLOAT: return "VK_FORMAT_R32_SFLOAT";
    case VK_FORMAT_R8G8B8A8_UNORM: return "VK_FORMAT_R8G8B8A8_UNORM";
    case VK_FORMAT_B8G8R8A8_UNORM: return "VK_FORMAT_B8G8R8A8_UNORM";
    case VK_FORMAT_R16G16B16A16_SFLOAT:
        return "VK_FORMAT_R16G16B16A16_SFLOAT";
    default: return "VK_FORMAT_UNDEFINED";
    }
}

const char* depth_format_name(VkFormat format) {
    switch (format) {
    case VK_FORMAT_D32_SFLOAT: return "VK_FORMAT_D32_SFLOAT";
    case VK_FORMAT_D24_UNORM_S8_UINT: return "VK_FORMAT_D24_UNORM_S8_UINT";
    case VK_FORMAT_D16_UNORM: return "VK_FORMAT_D16_UNORM";
    default: return "VK_FORMAT_UNDEFINED";
    }
}

float half_to_float(uint16_t half) {
    const float sign = (half & 0x8000u) != 0 ? -1.0f : 1.0f;
    const uint32_t exponent = (half >> 10) & 0x1fu;
    const uint32_t mantissa = half & 0x03ffu;
    if (exponent == 0) {
        return sign * std::ldexp(static_cast<float>(mantissa), -24);
    }
    if (exponent == 0x1fu) {
        return mantissa == 0
            ? sign * std::numeric_limits<float>::infinity()
            : std::numeric_limits<float>::quiet_NaN();
    }
    return sign * std::ldexp(
        static_cast<float>(0x0400u + mantissa),
        static_cast<int>(exponent) - 25);
}

uint8_t display_channel(float value) {
    return std::isfinite(value)
        ? static_cast<uint8_t>(std::lround(
              std::clamp(value, 0.0f, 1.0f) * 255.0f))
        : 0u;
}

void write_ppm(
    const std::filesystem::path& path,
    const std::vector<uint8_t>& texels,
    uint32_t width,
    uint32_t height,
    VkFormat format) {

    const size_t pixel_count = static_cast<size_t>(width) * height;
    if (texels.size() != pixel_count * readback_bytes_per_pixel(format)) {
        throw std::runtime_error("readback size mismatch");
    }
    std::ofstream output(path, std::ios::binary);
    if (!output) throw std::runtime_error("cannot open output PPM");
    output << "P6\n" << width << " " << height << "\n255\n";
    if (format == VK_FORMAT_R32_SFLOAT) {
        for (size_t i = 0; i < pixel_count; ++i) {
            float value = 0.0f;
            std::memcpy(&value, texels.data() + i * sizeof(float), sizeof(value));
            const uint8_t display = display_channel(value);
            output.put(static_cast<char>(display));
            output.put(static_cast<char>(display));
            output.put(static_cast<char>(display));
        }
        return;
    }
    for (size_t pixel = 0; pixel < pixel_count; ++pixel) {
        if (format == VK_FORMAT_R16G16B16A16_SFLOAT) {
            const auto offset = texels.data() + pixel * 8;
            for (size_t channel = 0; channel < 3; ++channel) {
                uint16_t half = 0;
                std::memcpy(&half, offset + channel * sizeof(half), sizeof(half));
                output.put(static_cast<char>(display_channel(half_to_float(half))));
            }
        } else {
            const auto offset = texels.data() + pixel * 4;
            const bool bgra = format == VK_FORMAT_B8G8R8A8_UNORM;
            output.put(static_cast<char>(offset[bgra ? 2 : 0]));
            output.put(static_cast<char>(offset[1]));
            output.put(static_cast<char>(offset[bgra ? 0 : 2]));
        }
    }
}

void destroy_buffer(Context& ctx, Buffer& buffer) {
    if (buffer.handle) vkDestroyBuffer(ctx.device, buffer.handle, nullptr);
    if (buffer.memory) vkFreeMemory(ctx.device, buffer.memory, nullptr);
    buffer.handle = VK_NULL_HANDLE;
    buffer.memory = VK_NULL_HANDLE;
}

void destroy_image(Context& ctx, Image& image) {
    if (image.view) vkDestroyImageView(ctx.device, image.view, nullptr);
    if (image.handle) vkDestroyImage(ctx.device, image.handle, nullptr);
    if (image.memory) vkFreeMemory(ctx.device, image.memory, nullptr);
    image.view = VK_NULL_HANDLE;
    image.handle = VK_NULL_HANDLE;
    image.memory = VK_NULL_HANDLE;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr
            << "usage: shift_vulkan_bundle_execute <bundle_dir> [output.ppm] [--validation]\n";
        return EXIT_FAILURE;
    }

    const std::filesystem::path root = argv[1];
    std::filesystem::path output = root / "vulkan_render.ppm";
    shift::vulkan::Validation validation;
    bool has_output = false;
    for (int i = 2; i < argc; ++i) {
        if (std::string(argv[i]) == "--validation") {
            validation.enabled = true;
        } else if (!has_output && argv[i][0] != '-') {
            output = argv[i];
            has_output = true;
        } else {
            std::cerr << "unexpected argument: " << argv[i] << "\n";
            return EXIT_FAILURE;
        }
    }

    Context ctx{};
    Buffer vertex_buffer{};
    Buffer index_buffer{};
    Buffer vertex_constants{};
    Buffer pixel_constants{};
    Buffer readback{};
    Image color{};
    Image depth{};
    std::vector<TextureResource> textures;
    CubeResource cube{};
    bool has_cube = false;

    VkDescriptorSetLayout set0_layout = VK_NULL_HANDLE;
    VkDescriptorSetLayout set1_layout = VK_NULL_HANDLE;
    VkDescriptorPool descriptor_pool = VK_NULL_HANDLE;
    VkDescriptorSet set0 = VK_NULL_HANDLE;
    VkDescriptorSet set1 = VK_NULL_HANDLE;
    VkRenderPass render_pass = VK_NULL_HANDLE;
    VkFramebuffer framebuffer = VK_NULL_HANDLE;
    VkPipelineLayout pipeline_layout = VK_NULL_HANDLE;
    VkPipeline pipeline = VK_NULL_HANDLE;
    VkShaderModule vertex_shader = VK_NULL_HANDLE;
    VkShaderModule pixel_shader = VK_NULL_HANDLE;
    VkCommandBuffer command = VK_NULL_HANDLE;

    try {
        require_native_submission_gate(root);
        const PipelineState pipeline_state =
            load_pipeline_state(root);
        const RenderTargetState render_target = load_render_target(root);
        Geometry geometry = load_geometry(root / "geometry.svpk");
        const WorldTransformExecution world_transform =
            apply_world_transform_affine(root, geometry);
        const Constants constants = load_constants(root / "constants.svcp");

        TexturePacket texture_packet{};
        const bool has_textures =
            std::filesystem::is_regular_file(root / "textures.svtp");
        if (has_textures) {
            texture_packet = load_texture_packet(root / "textures.svtp");
        }

        CubePacket cube_packet{};
        has_cube =
            std::filesystem::is_regular_file(root / "environment_cube.svcp");
        if (has_cube) {
            cube_packet = load_cube_packet(root / "environment_cube.svcp");
        }

        const auto vertex_spirv = find_shader(root, ".vertex.glsl.spv");
        const auto pixel_spirv = find_shader(root, ".pixel.glsl.spv");

        create_context(ctx, validation);

        create_buffer(
            ctx, geometry.vertices.size(), VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
            vertex_buffer);
        create_buffer(
            ctx, geometry.index_data.size(),
            VK_BUFFER_USAGE_INDEX_BUFFER_BIT,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
            index_buffer);
        create_buffer(
            ctx, kConstantBytes, VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
            vertex_constants);
        create_buffer(
            ctx, kConstantBytes, VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
            pixel_constants);

        void* mapped = nullptr;
        check(vkMapMemory(ctx.device, vertex_buffer.memory, 0,
                          geometry.vertices.size(), 0, &mapped),
              "map vertex buffer failed");
        std::memcpy(mapped, geometry.vertices.data(), geometry.vertices.size());
        vkUnmapMemory(ctx.device, vertex_buffer.memory);

        check(vkMapMemory(
            ctx.device, index_buffer.memory, 0,
            geometry.index_data.size(), 0, &mapped),
            "map index buffer failed");
        std::memcpy(
            mapped, geometry.index_data.data(), geometry.index_data.size());
        vkUnmapMemory(ctx.device, index_buffer.memory);

        check(vkMapMemory(
            ctx.device, vertex_constants.memory, 0, kConstantBytes, 0, &mapped),
            "map vertex constants failed");
        std::memcpy(mapped, constants.vertex.data(), kConstantBytes);
        vkUnmapMemory(ctx.device, vertex_constants.memory);

        check(vkMapMemory(
            ctx.device, pixel_constants.memory, 0, kConstantBytes, 0, &mapped),
            "map pixel constants failed");
        std::memcpy(mapped, constants.pixel.data(), kConstantBytes);
        vkUnmapMemory(ctx.device, pixel_constants.memory);

        textures.resize(has_textures ? texture_packet.records.size() : 0);
        for (size_t i = 0; i < textures.size(); ++i) {
            const auto record = texture_packet.records[i];
            const size_t pixels_offset = record.pixel_offset;
            const uint8_t* pixels =
                texture_packet.bytes.data() + pixels_offset;

            create_buffer(
                ctx, record.pixel_bytes, VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
                VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
                textures[i].staging);
            check(vkMapMemory(
                ctx.device, textures[i].staging.memory, 0,
                record.pixel_bytes, 0, &mapped),
                "map texture staging failed");
            std::memcpy(mapped, pixels, record.pixel_bytes);
            vkUnmapMemory(ctx.device, textures[i].staging.memory);

            textures[i].record = record;
            create_image(
                ctx, record.width, record.height, 1, VK_FORMAT_R8G8B8A8_UNORM, 0,
                VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_SAMPLED_BIT,
                textures[i].image);
            textures[i].sampler = sampler_for_mode(ctx, record.sampler_mode);
        }

        if (has_cube) {
            create_buffer(
                ctx, cube_packet.bytes.size(), VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
                VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
                cube.staging);
            check(vkMapMemory(
                ctx.device, cube.staging.memory, 0,
                cube_packet.bytes.size(), 0, &mapped),
                "map cube staging failed");
            std::memcpy(
                mapped, cube_packet.bytes.data(), cube_packet.bytes.size());
            vkUnmapMemory(ctx.device, cube.staging.memory);

            cube.header = cube_packet.header;
            create_image(
                ctx, cube.header.width, cube.header.height, 6,
                VK_FORMAT_R8G8B8A8_UNORM,
                VK_IMAGE_CREATE_CUBE_COMPATIBLE_BIT,
                VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_SAMPLED_BIT,
                cube.image);

            VkSamplerCreateInfo sampler{};
            sampler.sType = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO;
            sampler.magFilter = VK_FILTER_LINEAR;
            sampler.minFilter = VK_FILTER_LINEAR;
            sampler.mipmapMode = VK_SAMPLER_MIPMAP_MODE_NEAREST;
            sampler.addressModeU = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
            sampler.addressModeV = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
            sampler.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
            sampler.maxLod = 1.0f;
            check(vkCreateSampler(
                ctx.device, &sampler, nullptr, &cube.sampler),
                "vkCreateSampler cube failed");
        }

        vertex_shader = make_shader(ctx, vertex_spirv);
        pixel_shader = make_shader(ctx, pixel_spirv);

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
        check(vkCreateDescriptorSetLayout(
            ctx.device, &set0_info, nullptr, &set0_layout),
            "vkCreateDescriptorSetLayout set0 failed");

        std::map<uint32_t, VkDescriptorType> sampled_bindings;
        for (const auto& texture : textures) {
            const uint32_t reg = texture.record.register_index;
            auto [it, inserted] = sampled_bindings.emplace(
                reg, VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER);
            if (!inserted && it->second != VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER) {
                throw std::runtime_error("sampler descriptor collision");
            }
        }
        if (has_cube) {
            const uint32_t reg = cube.header.register_index;
            auto [it, inserted] = sampled_bindings.emplace(
                reg, VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER);
            if (!inserted) {
                throw std::runtime_error(
                    "2D and cube resources collide at the same sampler register");
            }
        }

        std::vector<VkDescriptorSetLayoutBinding> set1_bindings;
        for (const auto& item : sampled_bindings) {
            VkDescriptorSetLayoutBinding binding{};
            binding.binding = item.first;
            binding.descriptorType = item.second;
            binding.descriptorCount = 1;
            binding.stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT;
            set1_bindings.push_back(binding);
        }

        VkDescriptorSetLayoutCreateInfo set1_info{};
        set1_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
        set1_info.bindingCount = static_cast<uint32_t>(set1_bindings.size());
        set1_info.pBindings =
            set1_bindings.empty() ? nullptr : set1_bindings.data();
        check(vkCreateDescriptorSetLayout(
            ctx.device, &set1_info, nullptr, &set1_layout),
            "vkCreateDescriptorSetLayout set1 failed");

        std::vector<VkDescriptorPoolSize> pool_sizes;
        pool_sizes.push_back({
            VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, 2
        });
        if (!sampled_bindings.empty()) {
            pool_sizes.push_back({
                VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
                static_cast<uint32_t>(sampled_bindings.size())
            });
        }

        VkDescriptorPoolCreateInfo pool_info{};
        pool_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;
        pool_info.maxSets = 2;
        pool_info.poolSizeCount = static_cast<uint32_t>(pool_sizes.size());
        pool_info.pPoolSizes = pool_sizes.data();
        check(vkCreateDescriptorPool(
            ctx.device, &pool_info, nullptr, &descriptor_pool),
            "vkCreateDescriptorPool failed");

        VkDescriptorSetLayout sets[2] = {set0_layout, set1_layout};
        VkDescriptorSetAllocateInfo set0_alloc{};
        set0_alloc.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
        set0_alloc.descriptorPool = descriptor_pool;
        set0_alloc.descriptorSetCount = 1;
        set0_alloc.pSetLayouts = &set0_layout;
        check(vkAllocateDescriptorSets(
            ctx.device, &set0_alloc, &set0),
            "vkAllocateDescriptorSets set0 failed");

        VkDescriptorBufferInfo vertex_info{vertex_constants.handle, 0, kConstantBytes};
        VkDescriptorBufferInfo pixel_info{pixel_constants.handle, 0, kConstantBytes};
        VkWriteDescriptorSet constant_writes[2]{};
        constant_writes[0].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
        constant_writes[0].dstSet = set0;
        constant_writes[0].dstBinding = 14;
        constant_writes[0].descriptorCount = 1;
        constant_writes[0].descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
        constant_writes[0].pBufferInfo = &vertex_info;
        constant_writes[1] = constant_writes[0];
        constant_writes[1].dstBinding = 15;
        constant_writes[1].pBufferInfo = &pixel_info;
        vkUpdateDescriptorSets(
            ctx.device, 2, constant_writes, 0, nullptr);

        if (!set1_bindings.empty()) {
            VkDescriptorSetAllocateInfo set1_alloc{};
            set1_alloc.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
            set1_alloc.descriptorPool = descriptor_pool;
            set1_alloc.descriptorSetCount = 1;
            set1_alloc.pSetLayouts = &set1_layout;
            check(vkAllocateDescriptorSets(
                ctx.device, &set1_alloc, &set1),
                "vkAllocateDescriptorSets set1 failed");

            std::map<uint32_t, VkDescriptorImageInfo> image_infos_by_register;
            std::vector<VkDescriptorImageInfo> image_infos;
            std::vector<VkWriteDescriptorSet> writes;
            image_infos.reserve(sampled_bindings.size());
            writes.reserve(sampled_bindings.size());

            for (const auto& texture : textures) {
                VkDescriptorImageInfo info{};
                info.sampler = texture.sampler;
                info.imageView = texture.image.view;
                info.imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
                if (!image_infos_by_register.emplace(texture.record.register_index, info).second) {
                    throw std::runtime_error("duplicate 2D sampler register");
                }
            }
            if (has_cube) {
                VkDescriptorImageInfo info{};
                info.sampler = cube.sampler;
                info.imageView = cube.image.view;
                info.imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
                if (!image_infos_by_register.emplace(cube.header.register_index, info).second) {
                    throw std::runtime_error("cube sampler register collides with 2D resource");
                }
            }

            for (const auto& item : sampled_bindings) {
                auto found = image_infos_by_register.find(item.first);
                if (found == image_infos_by_register.end()) {
                    throw std::runtime_error("descriptor register has no resource");
                }
                image_infos.push_back(found->second);
            }
            for (size_t image_index = 0; image_index < sampled_bindings.size(); ++image_index) {
                auto item = std::next(sampled_bindings.begin(), static_cast<std::ptrdiff_t>(image_index));
                VkWriteDescriptorSet write{};
                write.sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
                write.dstSet = set1;
                write.dstBinding = item->first;
                write.descriptorCount = 1;
                write.descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
                write.pImageInfo = &image_infos[image_index];
                writes.push_back(write);
            }
            vkUpdateDescriptorSets(
                ctx.device,
                static_cast<uint32_t>(writes.size()),
                writes.data(),
                0,
                nullptr);
        }

        VkFormatProperties color_props{};
        vkGetPhysicalDeviceFormatProperties(
            ctx.physical, render_target.color_format, &color_props);
        const VkFormatFeatureFlags color_features =
            VK_FORMAT_FEATURE_COLOR_ATTACHMENT_BIT |
            VK_FORMAT_FEATURE_TRANSFER_SRC_BIT;
        if ((color_props.optimalTilingFeatures & color_features) !=
            color_features) {
            throw std::runtime_error(
                "captured color format lacks attachment/readback support");
        }
        create_image(
            ctx, render_target.width, render_target.height, 1,
            render_target.color_format, 0,
            VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT,
            color);

        VkFormatProperties depth_props{};
        vkGetPhysicalDeviceFormatProperties(
            ctx.physical, render_target.depth_format, &depth_props);
        if ((depth_props.optimalTilingFeatures &
             VK_FORMAT_FEATURE_DEPTH_STENCIL_ATTACHMENT_BIT) == 0) {
            throw std::runtime_error(
                "captured depth format is not a supported attachment");
        }
        create_image(
            ctx, render_target.width, render_target.height, 1,
            render_target.depth_format, 0,
            VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT,
            depth, render_target.depth_aspect);

        VkAttachmentDescription attachments[2]{};
        attachments[0].format = render_target.color_format;
        attachments[0].samples = VK_SAMPLE_COUNT_1_BIT;
        attachments[0].loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
        attachments[0].storeOp = VK_ATTACHMENT_STORE_OP_STORE;
        attachments[0].initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        attachments[0].finalLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
        attachments[1].format = render_target.depth_format;
        attachments[1].samples = VK_SAMPLE_COUNT_1_BIT;
        attachments[1].loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
        attachments[1].storeOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
        attachments[1].stencilLoadOp =
            (render_target.depth_aspect & VK_IMAGE_ASPECT_STENCIL_BIT) != 0 &&
                    (render_target.clear_flags & 4u) != 0
                ? VK_ATTACHMENT_LOAD_OP_CLEAR
                : VK_ATTACHMENT_LOAD_OP_DONT_CARE;
        attachments[1].stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
        attachments[1].initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        attachments[1].finalLayout = VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;

        VkAttachmentReference color_ref{};
        color_ref.attachment = 0;
        color_ref.layout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
        VkAttachmentReference depth_ref{};
        depth_ref.attachment = 1;
        depth_ref.layout = VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;

        VkSubpassDescription subpass{};
        subpass.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
        subpass.colorAttachmentCount = 1;
        subpass.pColorAttachments = &color_ref;
        subpass.pDepthStencilAttachment = &depth_ref;

        VkSubpassDependency dependencies[2]{};
        dependencies[0].srcSubpass = VK_SUBPASS_EXTERNAL;
        dependencies[0].dstSubpass = 0;
        dependencies[0].srcStageMask = VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT;
        dependencies[0].dstStageMask =
            VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT |
            VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT;
        dependencies[0].dstAccessMask =
            VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT |
            VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT;
        dependencies[1].srcSubpass = 0;
        dependencies[1].dstSubpass = VK_SUBPASS_EXTERNAL;
        dependencies[1].srcStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
        dependencies[1].srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
        dependencies[1].dstStageMask = VK_PIPELINE_STAGE_TRANSFER_BIT;
        dependencies[1].dstAccessMask = VK_ACCESS_TRANSFER_READ_BIT;

        VkRenderPassCreateInfo render_pass_info{};
        render_pass_info.sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
        render_pass_info.attachmentCount = 2;
        render_pass_info.pAttachments = attachments;
        render_pass_info.subpassCount = 1;
        render_pass_info.pSubpasses = &subpass;
        render_pass_info.dependencyCount = 2;
        render_pass_info.pDependencies = dependencies;
        check(vkCreateRenderPass(
            ctx.device, &render_pass_info, nullptr, &render_pass),
            "vkCreateRenderPass failed");

        VkImageView framebuffer_attachments[2] = {color.view, depth.view};
        VkFramebufferCreateInfo framebuffer_info{};
        framebuffer_info.sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
        framebuffer_info.renderPass = render_pass;
        framebuffer_info.attachmentCount = 2;
        framebuffer_info.pAttachments = framebuffer_attachments;
        framebuffer_info.width = render_target.width;
        framebuffer_info.height = render_target.height;
        framebuffer_info.layers = 1;
        check(vkCreateFramebuffer(
            ctx.device, &framebuffer_info, nullptr, &framebuffer),
            "vkCreateFramebuffer failed");

        VkPipelineShaderStageCreateInfo stages[2]{};
        stages[0].sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module = vertex_shader;
        stages[0].pName = "main";
        stages[1].sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module = pixel_shader;
        stages[1].pName = "main";

        VkVertexInputBindingDescription binding{};
        binding.binding = 0;
        binding.stride = geometry.header.stride;
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

        std::vector<VkVertexInputAttributeDescription> attributes;
        for (const auto& input : geometry.attributes) {
            VkVertexInputAttributeDescription attribute{};
            attribute.location = input.location;
            attribute.binding = 0;
            attribute.format = vk_format(input.format);
            attribute.offset = input.offset;
            if (attribute.format == VK_FORMAT_UNDEFINED) {
                throw std::runtime_error("unknown geometry packet attribute format");
            }
            attributes.push_back(attribute);
        }

        VkPipelineVertexInputStateCreateInfo vertex_input{};
        vertex_input.sType = VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO;
        vertex_input.vertexBindingDescriptionCount = 1;
        vertex_input.pVertexBindingDescriptions = &binding;
        vertex_input.vertexAttributeDescriptionCount =
            static_cast<uint32_t>(attributes.size());
        vertex_input.pVertexAttributeDescriptions = attributes.data();

        VkPipelineInputAssemblyStateCreateInfo input_assembly{};
        input_assembly.sType = VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO;
        input_assembly.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;

        VkViewport viewport{};
        viewport.x = static_cast<float>(render_target.viewport_x);
        viewport.y = static_cast<float>(
            render_target.viewport_y +
            (render_target.d3d9_y_down
                 ? static_cast<int32_t>(render_target.viewport_height)
                 : 0));
        viewport.width = static_cast<float>(render_target.viewport_width);
        viewport.height = static_cast<float>(render_target.d3d9_y_down
            ? -static_cast<int32_t>(render_target.viewport_height)
            : static_cast<int32_t>(render_target.viewport_height));
        viewport.minDepth = render_target.min_depth;
        viewport.maxDepth = render_target.max_depth;

        VkRect2D scissor{};
        scissor.offset = {
            render_target.viewport_x,
            render_target.viewport_y,
        };
        scissor.extent = {
            render_target.viewport_width,
            render_target.viewport_height,
        };

        VkPipelineViewportStateCreateInfo viewport_state{};
        viewport_state.sType = VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO;
        viewport_state.viewportCount = 1;
        viewport_state.pViewports = &viewport;
        viewport_state.scissorCount = 1;
        viewport_state.pScissors = &scissor;

        VkPipelineRasterizationStateCreateInfo raster{};
        raster.sType = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO;
        raster.polygonMode = VK_POLYGON_MODE_FILL;
        raster.cullMode = pipeline_state.cull_mode;
        raster.frontFace = VK_FRONT_FACE_COUNTER_CLOCKWISE;
        raster.lineWidth = 1.0f;

        VkPipelineMultisampleStateCreateInfo multisample{};
        multisample.sType = VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO;
        multisample.rasterizationSamples = VK_SAMPLE_COUNT_1_BIT;

        VkPipelineDepthStencilStateCreateInfo depth_state{};
        depth_state.sType = VK_STRUCTURE_TYPE_PIPELINE_DEPTH_STENCIL_STATE_CREATE_INFO;
        depth_state.depthTestEnable = pipeline_state.depth_test_enable;
        depth_state.depthWriteEnable = pipeline_state.depth_write_enable;
        depth_state.depthCompareOp = pipeline_state.depth_compare_op;

        VkPipelineColorBlendAttachmentState blend_attachment{};
        blend_attachment.blendEnable = pipeline_state.blend_enable;
        blend_attachment.srcColorBlendFactor =
            pipeline_state.src_color_blend_factor;
        blend_attachment.dstColorBlendFactor =
            pipeline_state.dst_color_blend_factor;
        blend_attachment.colorBlendOp = pipeline_state.color_blend_op;
        blend_attachment.srcAlphaBlendFactor =
            pipeline_state.src_alpha_blend_factor;
        blend_attachment.dstAlphaBlendFactor =
            pipeline_state.dst_alpha_blend_factor;
        blend_attachment.alphaBlendOp = pipeline_state.alpha_blend_op;
        blend_attachment.colorWriteMask =
            render_target.color_format == VK_FORMAT_R32_SFLOAT
                ? VK_COLOR_COMPONENT_R_BIT
                : VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
                      VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT;

        VkPipelineColorBlendStateCreateInfo blend{};
        blend.sType = VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO;
        blend.attachmentCount = 1;
        blend.pAttachments = &blend_attachment;

        VkPipelineLayoutCreateInfo pipeline_layout_info{};
        pipeline_layout_info.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
        pipeline_layout_info.setLayoutCount = 2;
        pipeline_layout_info.pSetLayouts = sets;
        check(vkCreatePipelineLayout(
            ctx.device, &pipeline_layout_info, nullptr, &pipeline_layout),
            "vkCreatePipelineLayout failed");

        VkGraphicsPipelineCreateInfo pipeline_info{};
        pipeline_info.sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO;
        pipeline_info.stageCount = 2;
        pipeline_info.pStages = stages;
        pipeline_info.pVertexInputState = &vertex_input;
        pipeline_info.pInputAssemblyState = &input_assembly;
        pipeline_info.pViewportState = &viewport_state;
        pipeline_info.pRasterizationState = &raster;
        pipeline_info.pMultisampleState = &multisample;
        pipeline_info.pDepthStencilState = &depth_state;
        pipeline_info.pColorBlendState = &blend;
        pipeline_info.layout = pipeline_layout;
        pipeline_info.renderPass = render_pass;
        pipeline_info.subpass = 0;
        check(vkCreateGraphicsPipelines(
            ctx.device, VK_NULL_HANDLE, 1, &pipeline_info, nullptr, &pipeline),
            "vkCreateGraphicsPipelines failed");

        const VkDeviceSize readback_size =
            static_cast<VkDeviceSize>(render_target.width) * render_target.height *
            readback_bytes_per_pixel(render_target.color_format);
        create_buffer(
            ctx, readback_size,
            VK_BUFFER_USAGE_TRANSFER_DST_BIT,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
            readback);

        VkCommandBufferAllocateInfo command_alloc{};
        command_alloc.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
        command_alloc.commandPool = ctx.command_pool;
        command_alloc.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        command_alloc.commandBufferCount = 1;
        check(vkAllocateCommandBuffers(
            ctx.device, &command_alloc, &command),
            "vkAllocateCommandBuffers failed");

        VkCommandBufferBeginInfo begin{};
        begin.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
        check(vkBeginCommandBuffer(command, &begin), "vkBeginCommandBuffer failed");

        for (auto& texture : textures) {
            transition(
                command, texture.image.handle, 1,
                VK_IMAGE_LAYOUT_UNDEFINED,
                VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                0,
                VK_ACCESS_TRANSFER_WRITE_BIT,
                VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                VK_PIPELINE_STAGE_TRANSFER_BIT);

            VkBufferImageCopy copy{};
            copy.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
            copy.imageSubresource.layerCount = 1;
            copy.imageExtent = {
                texture.record.width, texture.record.height, 1
            };
            vkCmdCopyBufferToImage(
                command,
                texture.staging.handle,
                texture.image.handle,
                VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                1,
                &copy);

            transition(
                command, texture.image.handle, 1,
                VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                VK_ACCESS_TRANSFER_WRITE_BIT,
                VK_ACCESS_SHADER_READ_BIT,
                VK_PIPELINE_STAGE_TRANSFER_BIT,
                VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT);
        }

        if (has_cube) {
            transition(
                command, cube.image.handle, 6,
                VK_IMAGE_LAYOUT_UNDEFINED,
                VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                0,
                VK_ACCESS_TRANSFER_WRITE_BIT,
                VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                VK_PIPELINE_STAGE_TRANSFER_BIT);

            for (uint32_t face = 0; face < 6; ++face) {
                VkBufferImageCopy copy{};
                copy.bufferOffset =
                    static_cast<VkDeviceSize>(face) * cube.header.face_bytes;
                copy.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
                copy.imageSubresource.baseArrayLayer = face;
                copy.imageSubresource.layerCount = 1;
                copy.imageExtent = {
                    cube.header.width, cube.header.height, 1
                };
                vkCmdCopyBufferToImage(
                    command,
                    cube.staging.handle,
                    cube.image.handle,
                    VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                    1,
                    &copy);
            }

            transition(
                command, cube.image.handle, 6,
                VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                VK_ACCESS_TRANSFER_WRITE_BIT,
                VK_ACCESS_SHADER_READ_BIT,
                VK_PIPELINE_STAGE_TRANSFER_BIT,
                VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT);
        }

        VkRenderPassBeginInfo pass{};
        pass.sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
        pass.renderPass = render_pass;
        pass.framebuffer = framebuffer;
        pass.renderArea.extent = {render_target.width, render_target.height};

        VkClearValue clear[2]{};
        if (render_target.captured) {
            clear[0].color.float32[0] =
                static_cast<float>((render_target.clear_color_argb >> 16) & 0xffu) / 255.0f;
            clear[0].color.float32[1] =
                static_cast<float>((render_target.clear_color_argb >> 8) & 0xffu) / 255.0f;
            clear[0].color.float32[2] =
                static_cast<float>(render_target.clear_color_argb & 0xffu) / 255.0f;
            clear[0].color.float32[3] =
                static_cast<float>((render_target.clear_color_argb >> 24) & 0xffu) / 255.0f;
        } else {
            clear[0].color.float32[0] = 0.02f;
            clear[0].color.float32[1] = 0.02f;
            clear[0].color.float32[2] = 0.02f;
            clear[0].color.float32[3] = 1.0f;
        }
        clear[1].depthStencil.depth = render_target.clear_depth;
        clear[1].depthStencil.stencil = render_target.clear_stencil;
        pass.clearValueCount = 2;
        pass.pClearValues = clear;

        vkCmdBeginRenderPass(command, &pass, VK_SUBPASS_CONTENTS_INLINE);
        vkCmdBindPipeline(
            command, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline);
        VkDeviceSize offset = geometry.capture.vertex_buffer_offset;
        vkCmdBindVertexBuffers(
            command, 0, 1, &vertex_buffer.handle, &offset);
        vkCmdBindIndexBuffer(
            command, index_buffer.handle, 0, geometry.index_type);
        vkCmdBindDescriptorSets(
            command, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline_layout,
            0, 1, &set0, 0, nullptr);
        if (set1 != VK_NULL_HANDLE) {
            vkCmdBindDescriptorSets(
                command, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline_layout,
                1, 1, &set1, 0, nullptr);
        }
        vkCmdDrawIndexed(
            command,
            geometry.draw_index_count,
            1,
            geometry.header.first_index,
            geometry.capture.base_vertex,
            0);
        vkCmdEndRenderPass(command);

        VkBufferImageCopy read{};
        read.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        read.imageSubresource.layerCount = 1;
        read.imageExtent = {render_target.width, render_target.height, 1};
        vkCmdCopyImageToBuffer(
            command,
            color.handle,
            VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
            readback.handle,
            1,
            &read);

        check(vkEndCommandBuffer(command), "vkEndCommandBuffer failed");
        VkSubmitInfo submit{};
        submit.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
        submit.commandBufferCount = 1;
        submit.pCommandBuffers = &command;
        check(vkQueueSubmit(
            ctx.queue, 1, &submit, VK_NULL_HANDLE),
            "vkQueueSubmit failed");
        check(vkQueueWaitIdle(ctx.queue), "vkQueueWaitIdle failed");

        std::vector<uint8_t> readback_bytes(static_cast<size_t>(readback_size));
        check(vkMapMemory(
            ctx.device, readback.memory, 0, readback_size, 0, &mapped),
            "map readback failed");
        std::memcpy(readback_bytes.data(), mapped, readback_bytes.size());
        vkUnmapMemory(ctx.device, readback.memory);
        if (!output.parent_path().empty()) {
            std::filesystem::create_directories(output.parent_path());
        }
        write_ppm(
            output, readback_bytes, render_target.width, render_target.height,
            render_target.color_format);

        VkPhysicalDeviceProperties props{};
        vkGetPhysicalDeviceProperties(ctx.physical, &props);

        if (command) vkFreeCommandBuffers(ctx.device, ctx.command_pool, 1, &command);
        destroy_buffer(ctx, readback);
        if (pipeline) vkDestroyPipeline(ctx.device, pipeline, nullptr);
        if (pipeline_layout) vkDestroyPipelineLayout(ctx.device, pipeline_layout, nullptr);
        if (framebuffer) vkDestroyFramebuffer(ctx.device, framebuffer, nullptr);
        if (render_pass) vkDestroyRenderPass(ctx.device, render_pass, nullptr);
        if (descriptor_pool) vkDestroyDescriptorPool(ctx.device, descriptor_pool, nullptr);
        if (set1_layout) vkDestroyDescriptorSetLayout(ctx.device, set1_layout, nullptr);
        if (set0_layout) vkDestroyDescriptorSetLayout(ctx.device, set0_layout, nullptr);
        if (vertex_shader) vkDestroyShaderModule(ctx.device, vertex_shader, nullptr);
        if (pixel_shader) vkDestroyShaderModule(ctx.device, pixel_shader, nullptr);
        destroy_image(ctx, depth);
        destroy_image(ctx, color);
        if (has_cube) {
            if (cube.sampler) vkDestroySampler(ctx.device, cube.sampler, nullptr);
            destroy_image(ctx, cube.image);
            destroy_buffer(ctx, cube.staging);
        }
        for (auto& texture : textures) {
            if (texture.sampler) vkDestroySampler(ctx.device, texture.sampler, nullptr);
            destroy_image(ctx, texture.image);
            destroy_buffer(ctx, texture.staging);
        }
        destroy_buffer(ctx, pixel_constants);
        destroy_buffer(ctx, vertex_constants);
        destroy_buffer(ctx, index_buffer);
        destroy_buffer(ctx, vertex_buffer);
        destroy(ctx, validation);
        if (validation.error_count() != 0) {
            std::cerr << "Vulkan validation failed: " << validation.error_count()
                      << " error(s)\n";
            return EXIT_FAILURE;
        }
        std::cout << "{\n";
        std::cout << "  \"format\": \"SHIFT.VulkanBundleExecution/1\",\n";
        std::cout << "  \"device\": \"" << props.deviceName << "\",\n";
        std::cout << "  \"vertex_count\": " << geometry.header.vertex_count << ",\n";
        std::cout << "  \"index_count\": " << geometry.header.index_count << ",\n";
        std::cout << "  \"draw_index_count\": " << geometry.draw_index_count << ",\n";
        std::cout << "  \"index_type\": \""
                  << (geometry.index_type == VK_INDEX_TYPE_UINT16
                          ? "VK_INDEX_TYPE_UINT16"
                          : "VK_INDEX_TYPE_UINT32") << "\",\n";
        std::cout << "  \"first_index\": " << geometry.header.first_index << ",\n";
        std::cout << "  \"base_vertex\": " << geometry.capture.base_vertex << ",\n";
        std::cout << "  \"render_target_width\": " << render_target.width << ",\n";
        std::cout << "  \"render_target_height\": " << render_target.height << ",\n";
        std::cout << "  \"d3d_render_target_format\": "
                  << render_target.d3d_color_format << ",\n";
        std::cout << "  \"render_target_format\": \""
                  << render_target_format_name(render_target.color_format) << "\",\n";
        std::cout << "  \"d3d_depth_format\": "
                  << render_target.d3d_depth_format << ",\n";
        std::cout << "  \"depth_attachment_format\": \""
                  << depth_format_name(render_target.depth_format) << "\",\n";
        std::cout << "  \"texture_count\": " << textures.size() << ",\n";
        std::cout << "  \"has_cube\": " << (has_cube ? "true" : "false") << ",\n";
        std::cout << "  \"world_transform_present\": "
                  << (world_transform.present ? "true" : "false") << ",\n";
        std::cout << "  \"world_transform_executed\": "
                  << (world_transform.executed ? "true" : "false") << ",\n";
        std::cout << "  \"world_transform_mode\": \""
                  << world_transform.mode << "\",\n";
        std::cout << "  \"world_transform_determinant\": "
                  << world_transform.determinant << ",\n";
        std::cout << "  \"world_translation_xyz\": ["
                  << world_transform.translation[0] << ", "
                  << world_transform.translation[1] << ", "
                  << world_transform.translation[2] << "],\n";
        std::cout << "  \"world_transformed_properties\": [";
        for (size_t index = 0;
             index < world_transform.transformed_properties.size();
             ++index) {
            if (index != 0) std::cout << ", ";
            std::cout << world_transform.transformed_properties[index];
        }
        std::cout << "],\n";
        auto print_probe = [&](const char* name,
                               bool present,
                               const float value[3]) {
            std::cout << "  \"" << name << "\": ";
            if (!present) {
                std::cout << "null,\n";
                return;
            }
            std::cout << "["
                      << value[0] << ", "
                      << value[1] << ", "
                      << value[2] << "],\n";
        };
        print_probe(
            "world_probe_position_xyz",
            world_transform.has_position_probe,
            world_transform.position_probe);
        print_probe(
            "world_probe_normal_xyz",
            world_transform.has_normal_probe,
            world_transform.normal_probe);
        print_probe(
            "world_probe_tangent_xyz",
            world_transform.has_tangent_probe,
            world_transform.tangent_probe);
        print_probe(
            "world_probe_tangent2_xyz",
            world_transform.has_tangent2_probe,
            world_transform.tangent2_probe);
        std::cout << "  \"validation_enabled\": " << (validation.enabled ? "true" : "false") << ",\n";
        std::cout << "  \"validation_errors\": " << validation.error_count() << ",\n";
        std::cout << "  \"output\": \"" << output.string() << "\"\n";
        std::cout << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "shift_vulkan_bundle_execute: " << error.what() << "\n";
        if (ctx.device != VK_NULL_HANDLE) {
            if (command) vkFreeCommandBuffers(ctx.device, ctx.command_pool, 1, &command);
            destroy_buffer(ctx, readback);
            if (pipeline) vkDestroyPipeline(ctx.device, pipeline, nullptr);
            if (pipeline_layout) vkDestroyPipelineLayout(ctx.device, pipeline_layout, nullptr);
            if (framebuffer) vkDestroyFramebuffer(ctx.device, framebuffer, nullptr);
            if (render_pass) vkDestroyRenderPass(ctx.device, render_pass, nullptr);
            if (descriptor_pool) vkDestroyDescriptorPool(ctx.device, descriptor_pool, nullptr);
            if (set1_layout) vkDestroyDescriptorSetLayout(ctx.device, set1_layout, nullptr);
            if (set0_layout) vkDestroyDescriptorSetLayout(ctx.device, set0_layout, nullptr);
            if (vertex_shader) vkDestroyShaderModule(ctx.device, vertex_shader, nullptr);
            if (pixel_shader) vkDestroyShaderModule(ctx.device, pixel_shader, nullptr);
            destroy_image(ctx, depth);
            destroy_image(ctx, color);
            if (has_cube) {
                if (cube.sampler) vkDestroySampler(ctx.device, cube.sampler, nullptr);
                destroy_image(ctx, cube.image);
                destroy_buffer(ctx, cube.staging);
            }
            for (auto& texture : textures) {
                if (texture.sampler) vkDestroySampler(ctx.device, texture.sampler, nullptr);
                destroy_image(ctx, texture.image);
                destroy_buffer(ctx, texture.staging);
            }
            destroy_buffer(ctx, pixel_constants);
            destroy_buffer(ctx, vertex_constants);
            destroy_buffer(ctx, index_buffer);
            destroy_buffer(ctx, vertex_buffer);
        }
        destroy(ctx, validation);
        return EXIT_FAILURE;
    }
}
