#include <vulkan/vulkan.h>

#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>
#include <utility>
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

struct GeometryAttribute {
    uint32_t location;
    uint32_t format;
    uint32_t offset;
    uint32_t stride;
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
#pragma pack(pop)

static_assert(sizeof(GeometryHeader) == 44);
static_assert(sizeof(GeometryAttribute) == 16);
static_assert(sizeof(ConstantHeader) == 28);
static_assert(sizeof(TextureHeader) == 20);
static_assert(sizeof(TextureRecord) == 24);
static_assert(sizeof(CubeHeader) == 28);

namespace {

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
    std::vector<GeometryAttribute> attributes;
    std::vector<uint8_t> vertex_bytes;
    std::vector<uint32_t> indices;
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

struct TexturePacket {
    TextureHeader header{};
    std::vector<TextureRecord> records;
    std::vector<uint8_t> data;
};

struct CubeResource {
    CubeHeader header{};
    Buffer staging{};
    Image image{};
    VkSampler sampler = VK_NULL_HANDLE;
};

void destroy(Context& ctx) {
    if (ctx.device != VK_NULL_HANDLE) {
        vkDeviceWaitIdle(ctx.device);
        if (ctx.command_pool) vkDestroyCommandPool(ctx.device, ctx.command_pool, nullptr);
        vkDestroyDevice(ctx.device, nullptr);
    }
    if (ctx.instance) vkDestroyInstance(ctx.instance, nullptr);
}

Context create_context() {
    Context ctx{};
    VkApplicationInfo app{};
    app.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
    app.pApplicationName = "SHIFT Vulkan Bundle Runner";
    app.applicationVersion = 1;
    app.pEngineName = "SHIFT";
    app.engineVersion = 1;
    app.apiVersion = VK_API_VERSION_1_0;

    VkInstanceCreateInfo instance{};
    instance.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    instance.pApplicationInfo = &app;
    check(vkCreateInstance(&instance, nullptr, &ctx.instance), "vkCreateInstance failed");

    uint32_t count = 0;
    check(vkEnumeratePhysicalDevices(ctx.instance, &count, nullptr),
          "vkEnumeratePhysicalDevices(count) failed");
    if (count == 0) throw std::runtime_error("no Vulkan physical devices");

    std::vector<VkPhysicalDevice> devices(count);
    check(vkEnumeratePhysicalDevices(ctx.instance, &count, devices.data()),
          "vkEnumeratePhysicalDevices(data) failed");

    for (VkPhysicalDevice candidate : devices) {
        uint32_t family_count = 0;
        vkGetPhysicalDeviceQueueFamilyProperties(candidate, &family_count, nullptr);
        std::vector<VkQueueFamilyProperties> families(family_count);
        vkGetPhysicalDeviceQueueFamilyProperties(candidate, &family_count, families.data());
        for (uint32_t i = 0; i < family_count; ++i) {
            if (families[i].queueFlags & VK_QUEUE_GRAPHICS_BIT) {
                ctx.physical = candidate;
                ctx.queue_family = i;
                break;
            }
        }
        if (ctx.physical) break;
    }
    if (!ctx.physical) throw std::runtime_error("no graphics queue");

    float priority = 1.0f;
    VkDeviceQueueCreateInfo queue{};
    queue.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
    queue.queueFamilyIndex = ctx.queue_family;
    queue.queueCount = 1;
    queue.pQueuePriorities = &priority;
    VkDeviceCreateInfo device{};
    device.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
    device.queueCreateInfoCount = 1;
    device.pQueueCreateInfos = &queue;
    check(vkCreateDevice(ctx.physical, &device, nullptr, &ctx.device),
          "vkCreateDevice failed");
    vkGetDeviceQueue(ctx.device, ctx.queue_family, 0, &ctx.queue);

    VkCommandPoolCreateInfo pool{};
    pool.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
    pool.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
    pool.queueFamilyIndex = ctx.queue_family;
    check(vkCreateCommandPool(ctx.device, &pool, nullptr, &ctx.command_pool),
          "vkCreateCommandPool failed");
    return ctx;
}

std::vector<uint8_t> read_bytes(const std::string& path) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file) throw std::runtime_error("cannot open " + path);
    const std::streamsize size = file.tellg();
    if (size <= 0) throw std::runtime_error("empty input " + path);
    file.seekg(0);
    std::vector<uint8_t> data(static_cast<size_t>(size));
    file.read(reinterpret_cast<char*>(data.data()), size);
    if (!file) throw std::runtime_error("cannot read " + path);
    return data;
}

Geometry load_geometry(const std::string& path) {
    const auto data = read_bytes(path);
    if (data.size() < sizeof(GeometryHeader)) throw std::runtime_error("geometry packet truncated");

    Geometry out{};
    std::memcpy(&out.header, data.data(), sizeof(out.header));
    if (std::memcmp(out.header.magic, "SVGP", 4) != 0 ||
        (out.header.version != 1 && out.header.version != 2)) {
        throw std::runtime_error("unsupported geometry packet");
    }
    if (!out.header.vertex_count || !out.header.index_count ||
        !out.header.stride || !out.header.attribute_count ||
        out.header.attribute_count > 16 ||
        out.header.index_count % 3 != 0) {
        throw std::runtime_error("invalid geometry header");
    }
    const size_t attr_bytes =
        static_cast<size_t>(out.header.attribute_count) * sizeof(GeometryAttribute);
    const size_t vertex_bytes =
        static_cast<size_t>(out.header.vertex_count) * out.header.stride;
    const size_t index_bytes =
        static_cast<size_t>(out.header.index_count) * sizeof(uint32_t);
    const size_t required = sizeof(GeometryHeader) + attr_bytes + vertex_bytes + index_bytes;
    if (required != data.size()) throw std::runtime_error("geometry packet size mismatch");

    out.attributes.resize(out.header.attribute_count);
    std::memcpy(out.attributes.data(), data.data() + sizeof(GeometryHeader), attr_bytes);
    size_t vertex_offset = sizeof(GeometryHeader) + attr_bytes;
    size_t index_offset = vertex_offset + vertex_bytes;
    out.vertex_bytes.assign(
        data.begin() + static_cast<std::ptrdiff_t>(vertex_offset),
        data.begin() + static_cast<std::ptrdiff_t>(index_offset));
    out.indices.resize(out.header.index_count);
    std::memcpy(out.indices.data(), data.data() + index_offset, index_bytes);
    for (const auto& attribute : out.attributes) {
        if (attribute.location > 15 || attribute.offset >= out.header.stride ||
            attribute.stride != out.header.stride) {
            throw std::runtime_error("invalid geometry attribute");
        }
        if (attribute.location == 0 && attribute.format != 2) {
            throw std::runtime_error("POSITION0 must be FLOAT3");
        }
    }
    return out;
}

Constants load_constants(const std::string& path) {
    const auto data = read_bytes(path);
    if (data.size() != sizeof(ConstantHeader) + 8192) {
        throw std::runtime_error("constant packet size mismatch");
    }
    Constants out{};
    std::memcpy(&out.header, data.data(), sizeof(out.header));
    if (std::memcmp(out.header.magic, "SVCP", 4) != 0 ||
        out.header.version != 1 || out.header.max_registers != 256 ||
        out.header.register_bytes != 16) {
        throw std::runtime_error("unsupported constant packet");
    }
    out.vertex.assign(data.begin() + sizeof(ConstantHeader),
                      data.begin() + sizeof(ConstantHeader) + 4096);
    out.pixel.assign(data.begin() + sizeof(ConstantHeader) + 4096, data.end());
    return out;
}

TexturePacket load_textures(const std::string& path) {
    const auto data = read_bytes(path);
    if (data.size() < sizeof(TextureHeader)) throw std::runtime_error("texture packet truncated");
    TexturePacket out{};
    std::memcpy(&out.header, data.data(), sizeof(out.header));
    if (std::memcmp(out.header.magic, "SVTP", 4) != 0 ||
        out.header.version != 1 || out.header.descriptor_set != 1 ||
        !out.header.texture_count || out.header.texture_count > 16) {
        throw std::runtime_error("unsupported texture packet");
    }
    const size_t records_bytes =
        static_cast<size_t>(out.header.texture_count) * sizeof(TextureRecord);
    if (sizeof(TextureHeader) + records_bytes > data.size()) {
        throw std::runtime_error("texture record table truncated");
    }
    out.records.resize(out.header.texture_count);
    std::memcpy(out.records.data(), data.data() + sizeof(TextureHeader), records_bytes);
    out.data = data;
    return out;
}

bool file_exists(const std::string& path) {
    std::ifstream file(path, std::ios::binary);
    return static_cast<bool>(file);
}

std::vector<uint32_t> read_spirv(const std::string& path) {
    const auto data = read_bytes(path);
    if (data.size() % 4 != 0) throw std::runtime_error("SPIR-V size is not aligned");
    std::vector<uint32_t> words(data.size() / 4);
    std::memcpy(words.data(), data.data(), data.size());
    return words;
}

VkShaderModule shader(Context& ctx, const std::string& path) {
    auto words = read_spirv(path);
    VkShaderModuleCreateInfo info{};
    info.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
    info.codeSize = words.size() * 4;
    info.pCode = words.data();
    VkShaderModule module = VK_NULL_HANDLE;
    check(vkCreateShaderModule(ctx.device, &info, nullptr, &module),
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
    alloc.memoryTypeIndex = memory_type(ctx.physical, req.memoryTypeBits, properties);
    check(vkAllocateMemory(ctx.device, &alloc, nullptr, &out.memory),
          "vkAllocateMemory buffer failed");
    check(vkBindBufferMemory(ctx.device, out.handle, out.memory, 0),
          "vkBindBufferMemory buffer failed");
}

void create_color_image(Context& ctx, uint32_t width, uint32_t height, Image& out) {
    VkImageCreateInfo info{};
    info.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
    info.imageType = VK_IMAGE_TYPE_2D;
    info.format = VK_FORMAT_R8G8B8A8_UNORM;
    info.extent = {width, height, 1};
    info.mipLevels = 1;
    info.arrayLayers = 1;
    info.samples = VK_SAMPLE_COUNT_1_BIT;
    info.tiling = VK_IMAGE_TILING_OPTIMAL;
    info.usage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
    check(vkCreateImage(ctx.device, &info, nullptr, &out.handle),
          "vkCreateImage color failed");
    VkMemoryRequirements req{};
    vkGetImageMemoryRequirements(ctx.device, out.handle, &req);
    VkMemoryAllocateInfo alloc{};
    alloc.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    alloc.allocationSize = req.size;
    alloc.memoryTypeIndex = memory_type(
        ctx.physical, req.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    check(vkAllocateMemory(ctx.device, &alloc, nullptr, &out.memory),
          "vkAllocateMemory color failed");
    check(vkBindImageMemory(ctx.device, out.handle, out.memory, 0),
          "vkBindImageMemory color failed");
    VkImageViewCreateInfo view{};
    view.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
    view.image = out.handle;
    view.viewType = VK_IMAGE_VIEW_TYPE_2D;
    view.format = VK_FORMAT_R8G8B8A8_UNORM;
    view.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    view.subresourceRange.levelCount = 1;
    view.subresourceRange.layerCount = 1;
    check(vkCreateImageView(ctx.device, &view, nullptr, &out.view),
          "vkCreateImageView color failed");
}

void upload_uniform(Context& ctx, const std::vector<uint8_t>& data, Buffer& out) {
    create_buffer(
        ctx, data.size(), VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT,
        VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, out);
    void* mapped = nullptr;
    check(vkMapMemory(ctx.device, out.memory, 0, data.size(), 0, &mapped),
          "vkMapMemory uniform failed");
    std::memcpy(mapped, data.data(), data.size());
    vkUnmapMemory(ctx.device, out.memory);
}

VkFormat attribute_format(uint32_t format) {
    switch (format) {
        case 1: return VK_FORMAT_R32G32_SFLOAT;
        case 2: return VK_FORMAT_R32G32B32_SFLOAT;
        case 3: return VK_FORMAT_R32G32B32A32_SFLOAT;
        case 4: return VK_FORMAT_R8G8B8A8_UNORM;
        case 5: return VK_FORMAT_R8G8B8A8_UINT;
        default: return VK_FORMAT_UNDEFINED;
    }
}

void transition(
    VkCommandBuffer cmd,
    VkImage image,
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
    barrier.subresourceRange.layerCount = 1;
    vkCmdPipelineBarrier(cmd, src_stage, dst_stage, 0,
                         0, nullptr, 0, nullptr, 1, &barrier);
}

void write_ppm(const std::string& path, const std::vector<uint8_t>& rgba) {
    std::ofstream out(path, std::ios::binary);
    if (!out) throw std::runtime_error("cannot open output PPM");
    const uint32_t side = 256;
    out << "P6\n" << side << " " << side << "\n255\n";
    for (size_t i = 0; i < rgba.size(); i += 4) {
        out.put(static_cast<char>(rgba[i]));
        out.put(static_cast<char>(rgba[i + 1]));
        out.put(static_cast<char>(rgba[i + 2]));
    }
}

} // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "usage: shift_vulkan_bundle_runner <bundle_dir> [output.ppm]\n";
        return EXIT_FAILURE;
    }

    const std::string root = argv[1];
    const std::string output = argc >= 3 ? argv[2] : root + "/vulkan_output.ppm";

    const std::string geometry_path = root + "/geometry.svpk";
    const std::string constants_path = root + "/constants.svcp";
    const std::string texture_path = root + "/textures.svtp";
    const std::string cube_path = root + "/environment_cube.svcp";

    try {
        const Geometry geometry = load_geometry(geometry_path);
        const Constants constants = load_constants(constants_path);
        const bool has_textures = file_exists(texture_path);
        const bool has_cube = file_exists(cube_path);
        if (!has_textures && !has_cube) {
            throw std::runtime_error("bundle has no sampled texture resource packet");
        }
        const TexturePacket texture_packet = has_textures ? load_textures(texture_path) : TexturePacket{};
        (void)texture_packet;
        throw std::runtime_error(
            "Phase 218 native bundle execution currently requires shader reflection for mixed "
            "2D/cube descriptor bindings; use individual resource checkpoints until reflection "
            "is implemented");
    } catch (const std::exception& error) {
        std::cerr << "shift_vulkan_bundle_runner: " << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
