#include <vulkan/vulkan.h>

#include <cstdint>
#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
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

constexpr uint32_t kConstantBytes = 4096;
constexpr uint32_t kRenderWidth = 800;
constexpr uint32_t kRenderHeight = 450;

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
    std::vector<uint8_t> vertices;
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

void destroy(Context& context) {
    if (context.device) {
        vkDeviceWaitIdle(context.device);
        if (context.command_pool) {
            vkDestroyCommandPool(context.device, context.command_pool, nullptr);
        }
        vkDestroyDevice(context.device, nullptr);
    }
    if (context.instance) {
        vkDestroyInstance(context.instance, nullptr);
    }
}

Context create_context() {
    Context context{};

    VkApplicationInfo app{};
    app.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
    app.pApplicationName = "SHIFT Vulkan Bundle Execute";
    app.applicationVersion = 1;
    app.pEngineName = "SHIFT";
    app.engineVersion = 1;
    app.apiVersion = VK_API_VERSION_1_0;

    VkInstanceCreateInfo instance{};
    instance.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    instance.pApplicationInfo = &app;
    check(vkCreateInstance(&instance, nullptr, &context.instance),
          "vkCreateInstance failed");

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

    return context;
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
        (geometry.header.version != 1 && geometry.header.version != 2)) {
        throw std::runtime_error("unsupported geometry packet");
    }
    if (geometry.header.vertex_count == 0 ||
        geometry.header.index_count == 0 ||
        geometry.header.stride == 0 ||
        geometry.header.attribute_count == 0 ||
        geometry.header.attribute_count > 16 ||
        geometry.header.index_count % 3 != 0) {
        throw std::runtime_error("invalid geometry packet counts");
    }

    const size_t attribute_bytes =
        static_cast<size_t>(geometry.header.attribute_count) *
        sizeof(GeometryAttribute);
    const size_t vertex_bytes =
        static_cast<size_t>(geometry.header.vertex_count) *
        geometry.header.stride;
    const size_t index_bytes =
        static_cast<size_t>(geometry.header.index_count) *
        sizeof(uint32_t);
    const size_t expected =
        sizeof(GeometryHeader) + attribute_bytes + vertex_bytes + index_bytes;
    if (expected != data.size()) {
        throw std::runtime_error("geometry packet size mismatch");
    }

    geometry.attributes.resize(geometry.header.attribute_count);
    std::memcpy(
        geometry.attributes.data(),
        data.data() + sizeof(GeometryHeader),
        attribute_bytes);

    const size_t vertices_offset =
        sizeof(GeometryHeader) + attribute_bytes;
    const size_t indices_offset = vertices_offset + vertex_bytes;
    geometry.vertices.assign(
        data.begin() + static_cast<std::ptrdiff_t>(vertices_offset),
        data.begin() + static_cast<std::ptrdiff_t>(indices_offset));
    geometry.indices.resize(geometry.header.index_count);
    std::memcpy(
        geometry.indices.data(),
        data.data() + indices_offset,
        index_bytes);

    bool position_seen = false;
    for (const auto& attribute : geometry.attributes) {
        if (attribute.location > 15 ||
            attribute.offset >= geometry.header.stride ||
            attribute.stride != geometry.header.stride) {
            throw std::runtime_error("invalid vertex attribute");
        }
        if (attribute.location == 0) {
            if (attribute.format != 2 || position_seen) {
                throw std::runtime_error("POSITION0 must be exactly FLOAT3 at location 0");
            }
            position_seen = true;
        }
        if (attribute.offset > geometry.header.stride - 4) {
            throw std::runtime_error("vertex attribute offset is out of range");
        }
    }
    if (!position_seen) {
        throw std::runtime_error("geometry packet has no POSITION0");
    }
    for (uint32_t index : geometry.indices) {
        if (index >= geometry.header.vertex_count) {
            throw std::runtime_error("geometry index exceeds vertex count");
        }
    }
    return geometry;
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
    VkImageCreateFlags flags,
    VkImageUsageFlags usage,
    Image& out) {

    VkImageCreateInfo info{};
    info.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
    info.flags = flags;
    info.imageType = VK_IMAGE_TYPE_2D;
    info.format = VK_FORMAT_R8G8B8A8_UNORM;
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
    view.format = VK_FORMAT_R8G8B8A8_UNORM;
    view.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
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

void write_ppm(
    const std::filesystem::path& path,
    const std::vector<uint8_t>& rgba) {

    if (rgba.size() != static_cast<size_t>(kRenderWidth) * kRenderHeight * 4) {
        throw std::runtime_error("readback size mismatch");
    }
    std::ofstream output(path, std::ios::binary);
    if (!output) throw std::runtime_error("cannot open output PPM");
    output << "P6\n" << kRenderWidth << " " << kRenderHeight << "\n255\n";
    for (size_t i = 0; i < rgba.size(); i += 4) {
        output.put(static_cast<char>(rgba[i]));
        output.put(static_cast<char>(rgba[i + 1]));
        output.put(static_cast<char>(rgba[i + 2]));
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
            << "usage: shift_vulkan_bundle_execute <bundle_dir> [output.ppm]\n";
        return EXIT_FAILURE;
    }

    const std::filesystem::path root = argv[1];
    const std::filesystem::path output =
        argc >= 3 ? std::filesystem::path(argv[2]) :
                    root / "vulkan_render.ppm";

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
        const Geometry geometry = load_geometry(root / "geometry.svpk");
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

        ctx = create_context();

        create_buffer(
            ctx, geometry.vertices.size(), VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
            vertex_buffer);
        create_buffer(
            ctx, geometry.indices.size() * sizeof(uint32_t),
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
            geometry.indices.size() * sizeof(uint32_t), 0, &mapped),
            "map index buffer failed");
        std::memcpy(
            mapped,
            geometry.indices.data(),
            geometry.indices.size() * sizeof(uint32_t));
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
                ctx, record.width, record.height, 1, 0,
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

            std::vector<VkDescriptorImageInfo> image_infos;
            std::vector<VkWriteDescriptorSet> writes;
            image_infos.reserve(sampled_bindings.size());
            writes.reserve(sampled_bindings.size());

            for (const auto& texture : textures) {
                VkDescriptorImageInfo info{};
                info.sampler = texture.sampler;
                info.imageView = texture.image.view;
                info.imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
                image_infos.push_back(info);
            }
            if (has_cube) {
                VkDescriptorImageInfo info{};
                info.sampler = cube.sampler;
                info.imageView = cube.image.view;
                info.imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
                image_infos.push_back(info);
            }

            size_t image_index = 0;
            for (const auto& item : sampled_bindings) {
                VkWriteDescriptorSet write{};
                write.sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
                write.dstSet = set1;
                write.dstBinding = item.first;
                write.descriptorCount = 1;
                write.descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
                write.pImageInfo = &image_infos[image_index++];
                writes.push_back(write);
            }
            vkUpdateDescriptorSets(
                ctx.device,
                static_cast<uint32_t>(writes.size()),
                writes.data(),
                0,
                nullptr);
        }

        create_color_image:
        create_image(
            ctx, kRenderWidth, kRenderHeight, 1, 0,
            VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT,
            color);

        const VkFormat depth_format = VK_FORMAT_D32_SFLOAT;
        VkFormatProperties depth_props{};
        vkGetPhysicalDeviceFormatProperties(
            ctx.physical, depth_format, &depth_props);
        if ((depth_props.optimalTilingFeatures &
             VK_FORMAT_FEATURE_DEPTH_STENCIL_ATTACHMENT_BIT) == 0) {
            throw std::runtime_error("VK_FORMAT_D32_SFLOAT depth attachment unsupported");
        }
        create_image(
            ctx, kRenderWidth, kRenderHeight, 1, 0,
            VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT,
            depth);

        VkImageViewCreateInfo depth_view{};
        depth_view.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
        depth_view.image = depth.handle;
        depth_view.viewType = VK_IMAGE_VIEW_TYPE_2D;
        depth_view.format = depth_format;
        depth_view.subresourceRange.aspectMask = VK_IMAGE_ASPECT_DEPTH_BIT;
        depth_view.subresourceRange.levelCount = 1;
        depth_view.subresourceRange.layerCount = 1;
        vkDestroyImageView(ctx.device, depth.view, nullptr);
        depth.view = VK_NULL_HANDLE;
        check(vkCreateImageView(
            ctx.device, &depth_view, nullptr, &depth.view),
            "vkCreateImageView depth failed");

        VkAttachmentDescription attachments[2]{};
        attachments[0].format = VK_FORMAT_R8G8B8A8_UNORM;
        attachments[0].samples = VK_SAMPLE_COUNT_1_BIT;
        attachments[0].loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
        attachments[0].storeOp = VK_ATTACHMENT_STORE_OP_STORE;
        attachments[0].initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        attachments[0].finalLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
        attachments[1].format = depth_format;
        attachments[1].samples = VK_SAMPLE_COUNT_1_BIT;
        attachments[1].loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
        attachments[1].storeOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
        attachments[1].stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
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
        framebuffer_info.width = kRenderWidth;
        framebuffer_info.height = kRenderHeight;
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
        viewport.width = static_cast<float>(kRenderWidth);
        viewport.height = static_cast<float>(kRenderHeight);
        viewport.maxDepth = 1.0f;

        VkRect2D scissor{};
        scissor.extent = {kRenderWidth, kRenderHeight};

        VkPipelineViewportStateCreateInfo viewport_state{};
        viewport_state.sType = VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO;
        viewport_state.viewportCount = 1;
        viewport_state.pViewports = &viewport;
        viewport_state.scissorCount = 1;
        viewport_state.pScissors = &scissor;

        VkPipelineRasterizationStateCreateInfo raster{};
        raster.sType = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO;
        raster.polygonMode = VK_POLYGON_MODE_FILL;
        raster.cullMode = VK_CULL_MODE_NONE;
        raster.frontFace = VK_FRONT_FACE_COUNTER_CLOCKWISE;
        raster.lineWidth = 1.0f;

        VkPipelineMultisampleStateCreateInfo multisample{};
        multisample.sType = VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO;
        multisample.rasterizationSamples = VK_SAMPLE_COUNT_1_BIT;

        VkPipelineDepthStencilStateCreateInfo depth_state{};
        depth_state.sType = VK_STRUCTURE_TYPE_PIPELINE_DEPTH_STENCIL_STATE_CREATE_INFO;
        depth_state.depthTestEnable = VK_TRUE;
        depth_state.depthWriteEnable = VK_TRUE;
        depth_state.depthCompareOp = VK_COMPARE_OP_LESS_OR_EQUAL;

        VkPipelineColorBlendAttachmentState blend_attachment{};
        blend_attachment.blendEnable = VK_FALSE;
        blend_attachment.colorWriteMask =
            VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
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

        create_buffer(
            ctx, static_cast<VkDeviceSize>(kRenderWidth) * kRenderHeight * 4u,
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
        pass.renderArea.extent = {kRenderWidth, kRenderHeight};

        VkClearValue clear[2]{};
        clear[0].color.float32[0] = 0.02f;
        clear[0].color.float32[1] = 0.02f;
        clear[0].color.float32[2] = 0.02f;
        clear[0].color.float32[3] = 1.0f;
        clear[1].depthStencil.depth = 1.0f;
        pass.clearValueCount = 2;
        pass.pClearValues = clear;

        vkCmdBeginRenderPass(command, &pass, VK_SUBPASS_CONTENTS_INLINE);
        vkCmdBindPipeline(
            command, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline);
        VkDeviceSize offset = 0;
        vkCmdBindVertexBuffers(
            command, 0, 1, &vertex_buffer.handle, &offset);
        vkCmdBindIndexBuffer(
            command, index_buffer.handle, 0, VK_INDEX_TYPE_UINT32);
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
            geometry.header.index_count,
            1,
            geometry.header.first_index,
            0,
            0);
        vkCmdEndRenderPass(command);

        VkBufferImageCopy read{};
        read.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        read.imageSubresource.layerCount = 1;
        read.imageExtent = {kRenderWidth, kRenderHeight, 1};
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

        std::vector<uint8_t> rgba(
            static_cast<size_t>(kRenderWidth) * kRenderHeight * 4u);
        check(vkMapMemory(
            ctx.device, readback.memory, 0, rgba.size(), 0, &mapped),
            "map readback failed");
        std::memcpy(rgba.data(), mapped, rgba.size());
        vkUnmapMemory(ctx.device, readback.memory);
        output.parent_path().empty()
            ? void()
            : std::filesystem::create_directories(output.parent_path());
        write_ppm(output, rgba);

        VkPhysicalDeviceProperties props{};
        vkGetPhysicalDeviceProperties(ctx.physical, &props);
        std::cout << "{\n";
        std::cout << "  \"format\": \"SHIFT.VulkanBundleExecution/1\",\n";
        std::cout << "  \"device\": \"" << props.deviceName << "\",\n";
        std::cout << "  \"vertex_count\": " << geometry.header.vertex_count << ",\n";
        std::cout << "  \"index_count\": " << geometry.header.index_count << ",\n";
        std::cout << "  \"texture_count\": " << textures.size() << ",\n";
        std::cout << "  \"has_cube\": " << (has_cube ? "true" : "false") << ",\n";
        std::cout << "  \"output\": \"" << output.string() << "\"\n";
        std::cout << "}\n";

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
        destroy(ctx);
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
        destroy(ctx);
        return EXIT_FAILURE;
    }
}
