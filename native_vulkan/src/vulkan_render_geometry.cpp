#include <vulkan/vulkan.h>

#include <cstdint>
#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

#pragma pack(push, 1)
struct PacketHeader {
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

struct PacketAttribute {
    uint32_t location;
    uint32_t format;
    uint32_t offset;
    uint32_t stride;
};
#pragma pack(pop)

static_assert(sizeof(PacketHeader) == 44, "unexpected geometry packet header size");
static_assert(sizeof(PacketAttribute) == 16, "unexpected geometry packet attribute size");

namespace {

[[noreturn]] void fail(const std::string& message, VkResult result) {
    throw std::runtime_error(message + " (" + std::to_string(static_cast<int>(result)) + ")");
}

void check(VkResult result, const char* message) {
    if (result != VK_SUCCESS) {
        fail(message, result);
    }
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

struct GeometryPacket {
    PacketHeader header{};
    std::vector<PacketAttribute> attributes;
    std::vector<uint8_t> vertex_bytes;
    std::vector<uint32_t> indices;
};

void destroy(Context& ctx) {
    if (ctx.device != VK_NULL_HANDLE) {
        vkDeviceWaitIdle(ctx.device);
        if (ctx.command_pool != VK_NULL_HANDLE) {
            vkDestroyCommandPool(ctx.device, ctx.command_pool, nullptr);
        }
        vkDestroyDevice(ctx.device, nullptr);
    }
    if (ctx.instance != VK_NULL_HANDLE) {
        vkDestroyInstance(ctx.instance, nullptr);
    }
}

Context create_context() {
    Context ctx{};

    VkApplicationInfo app{};
    app.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
    app.pApplicationName = "SHIFT Vulkan RenderCommand Geometry";
    app.applicationVersion = 1;
    app.pEngineName = "SHIFT";
    app.engineVersion = 1;
    app.apiVersion = VK_API_VERSION_1_0;

    VkInstanceCreateInfo instance_info{};
    instance_info.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    instance_info.pApplicationInfo = &app;
    check(vkCreateInstance(&instance_info, nullptr, &ctx.instance),
          "vkCreateInstance failed");

    uint32_t count = 0;
    check(vkEnumeratePhysicalDevices(ctx.instance, &count, nullptr),
          "vkEnumeratePhysicalDevices(count) failed");
    if (count == 0) {
        destroy(ctx);
        throw std::runtime_error("no Vulkan physical devices");
    }

    std::vector<VkPhysicalDevice> devices(count);
    check(vkEnumeratePhysicalDevices(ctx.instance, &count, devices.data()),
          "vkEnumeratePhysicalDevices(data) failed");

    for (VkPhysicalDevice candidate : devices) {
        uint32_t family_count = 0;
        vkGetPhysicalDeviceQueueFamilyProperties(candidate, &family_count, nullptr);
        std::vector<VkQueueFamilyProperties> families(family_count);
        vkGetPhysicalDeviceQueueFamilyProperties(candidate, &family_count, families.data());
        for (uint32_t i = 0; i < family_count; ++i) {
            if ((families[i].queueFlags & VK_QUEUE_GRAPHICS_BIT) != 0) {
                ctx.physical = candidate;
                ctx.queue_family = i;
                break;
            }
        }
        if (ctx.physical != VK_NULL_HANDLE) {
            break;
        }
    }
    if (ctx.physical == VK_NULL_HANDLE) {
        destroy(ctx);
        throw std::runtime_error("no graphics queue family");
    }

    float priority = 1.0f;
    VkDeviceQueueCreateInfo queue_info{};
    queue_info.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
    queue_info.queueFamilyIndex = ctx.queue_family;
    queue_info.queueCount = 1;
    queue_info.pQueuePriorities = &priority;

    VkDeviceCreateInfo device_info{};
    device_info.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
    device_info.queueCreateInfoCount = 1;
    device_info.pQueueCreateInfos = &queue_info;
    check(vkCreateDevice(ctx.physical, &device_info, nullptr, &ctx.device),
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

void create_buffer(
    Context& ctx,
    VkDeviceSize size,
    VkBufferUsageFlags usage,
    VkMemoryPropertyFlags memory_properties,
    Buffer& out) {

    VkBufferCreateInfo info{};
    info.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
    info.size = size;
    info.usage = usage;
    check(vkCreateBuffer(ctx.device, &info, nullptr, &out.handle),
          "vkCreateBuffer failed");

    VkMemoryRequirements requirements{};
    vkGetBufferMemoryRequirements(ctx.device, out.handle, &requirements);

    VkMemoryAllocateInfo allocation{};
    allocation.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    allocation.allocationSize = requirements.size;
    allocation.memoryTypeIndex = memory_type(
        ctx.physical, requirements.memoryTypeBits, memory_properties);
    check(vkAllocateMemory(ctx.device, &allocation, nullptr, &out.memory),
          "vkAllocateMemory(buffer) failed");
    check(vkBindBufferMemory(ctx.device, out.handle, out.memory, 0),
          "vkBindBufferMemory failed");
}

void create_image(
    Context& ctx,
    uint32_t width,
    uint32_t height,
    VkFormat format,
    VkImageUsageFlags usage,
    VkImageAspectFlags aspect,
    VkMemoryPropertyFlags memory_properties,
    Image& out) {

    VkImageCreateInfo info{};
    info.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
    info.imageType = VK_IMAGE_TYPE_2D;
    info.format = format;
    info.extent = {width, height, 1};
    info.mipLevels = 1;
    info.arrayLayers = 1;
    info.samples = VK_SAMPLE_COUNT_1_BIT;
    info.tiling = VK_IMAGE_TILING_OPTIMAL;
    info.usage = usage;
    info.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    check(vkCreateImage(ctx.device, &info, nullptr, &out.handle),
          "vkCreateImage failed");

    VkMemoryRequirements requirements{};
    vkGetImageMemoryRequirements(ctx.device, out.handle, &requirements);

    VkMemoryAllocateInfo allocation{};
    allocation.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    allocation.allocationSize = requirements.size;
    allocation.memoryTypeIndex = memory_type(
        ctx.physical, requirements.memoryTypeBits, memory_properties);
    check(vkAllocateMemory(ctx.device, &allocation, nullptr, &out.memory),
          "vkAllocateMemory(image) failed");
    check(vkBindImageMemory(ctx.device, out.handle, out.memory, 0),
          "vkBindImageMemory failed");

    VkImageViewCreateInfo view{};
    view.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
    view.image = out.handle;
    view.viewType = VK_IMAGE_VIEW_TYPE_2D;
    view.format = format;
    view.subresourceRange.aspectMask = aspect;
    view.subresourceRange.baseMipLevel = 0;
    view.subresourceRange.levelCount = 1;
    view.subresourceRange.baseArrayLayer = 0;
    view.subresourceRange.layerCount = 1;
    check(vkCreateImageView(ctx.device, &view, nullptr, &out.view),
          "vkCreateImageView failed");
}

VkFormat choose_depth_format(VkPhysicalDevice physical) {
    const VkFormat candidates[] = {
        VK_FORMAT_D32_SFLOAT,
        VK_FORMAT_D24_UNORM_S8_UINT,
        VK_FORMAT_D16_UNORM,
    };
    for (VkFormat format : candidates) {
        VkFormatProperties props{};
        vkGetPhysicalDeviceFormatProperties(physical, format, &props);
        if ((props.optimalTilingFeatures &
             VK_FORMAT_FEATURE_DEPTH_STENCIL_ATTACHMENT_BIT) != 0) {
            return format;
        }
    }
    throw std::runtime_error("no supported depth attachment format");
}

std::vector<uint8_t> read_file(const std::string& path) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file) {
        throw std::runtime_error("cannot open geometry packet: " + path);
    }
    const std::streamsize size = file.tellg();
    if (size <= 0) {
        throw std::runtime_error("geometry packet is empty");
    }
    file.seekg(0);
    std::vector<uint8_t> data(static_cast<size_t>(size));
    file.read(reinterpret_cast<char*>(data.data()), size);
    if (!file) {
        throw std::runtime_error("failed to read geometry packet");
    }
    return data;
}

GeometryPacket parse_packet(const std::string& path) {
    const std::vector<uint8_t> data = read_file(path);
    if (data.size() < sizeof(PacketHeader) + sizeof(PacketAttribute)) {
        throw std::runtime_error("geometry packet is truncated");
    }

    GeometryPacket packet{};
    std::memcpy(&packet.header, data.data(), sizeof(packet.header));
    if (std::memcmp(packet.header.magic, "SVGP", 4) != 0 ||
        (packet.header.version != 1 && packet.header.version != 2)) {
        throw std::runtime_error("unsupported SHIFT Vulkan geometry packet");
    }
    if (packet.header.vertex_count == 0 ||
        packet.header.index_count == 0 ||
        packet.header.stride == 0 ||
        packet.header.attribute_count == 0 ||
        packet.header.attribute_count > 16) {
        throw std::runtime_error("invalid geometry packet counts/stride/attribute count");
    }

    const size_t attribute_bytes =
        static_cast<size_t>(packet.header.attribute_count) * sizeof(PacketAttribute);
    if (sizeof(packet.header) + attribute_bytes > data.size()) {
        throw std::runtime_error("geometry packet attribute table is truncated");
    }
    packet.attributes.resize(packet.header.attribute_count);
    std::memcpy(
        packet.attributes.data(),
        data.data() + sizeof(packet.header),
        attribute_bytes);

    auto format_size = [](uint32_t format) -> uint32_t {
        switch (format) {
            case 1: return 8;
            case 2: return 12;
            case 3: return 16;
            case 4: return 4;
            case 5: return 4;
            default: return 0;
        }
    };

    bool position_seen = false;
    for (const PacketAttribute& attribute : packet.attributes) {
        const uint32_t bytes = format_size(attribute.format);
        if (bytes == 0 ||
            attribute.location > 15 ||
            attribute.offset + bytes > packet.header.stride ||
            attribute.stride != packet.header.stride) {
            throw std::runtime_error("unsupported Vulkan vertex attribute");
        }
        if (attribute.location == 0) {
            if (attribute.format != 2 || position_seen) {
                throw std::runtime_error("POSITION0 must be exactly one FLOAT3 attribute at location 0");
            }
            position_seen = true;
        }
    }
    if (!position_seen) {
        throw std::runtime_error("geometry packet has no POSITION0 at location 0");
    }
    if (packet.header.index_count % 3 != 0) {
        throw std::runtime_error("geometry packet is not triangle-list data");
    }

    const uint64_t vertex_bytes =
        static_cast<uint64_t>(packet.header.vertex_count) * packet.header.stride;
    const uint64_t index_bytes =
        static_cast<uint64_t>(packet.header.index_count) * sizeof(uint32_t);
    const uint64_t required =
        sizeof(packet.header) + attribute_bytes +
        vertex_bytes + index_bytes;
    if (required != data.size() ||
        vertex_bytes > std::numeric_limits<size_t>::max() ||
        index_bytes > std::numeric_limits<size_t>::max()) {
        throw std::runtime_error("geometry packet byte ranges are invalid");
    }

    const size_t vertex_offset =
        sizeof(packet.header) + attribute_bytes;
    const size_t index_offset =
        vertex_offset + static_cast<size_t>(vertex_bytes);
    packet.vertex_bytes.assign(
        data.begin() + static_cast<std::ptrdiff_t>(vertex_offset),
        data.begin() + static_cast<std::ptrdiff_t>(index_offset));
    packet.indices.resize(packet.header.index_count);
    std::memcpy(
        packet.indices.data(),
        data.data() + index_offset,
        static_cast<size_t>(index_bytes));

    for (uint32_t index : packet.indices) {
        if (index >= packet.header.vertex_count) {
            throw std::runtime_error("geometry packet index exceeds vertex count");
        }
    }
    if (packet.header.first_index != 0) {
        throw std::runtime_error("geometry packet must start at index 0");
    }
    return packet;
}

VkShaderModule shader_module(
    VkDevice device,
    const std::vector<uint32_t>& code) {

    VkShaderModuleCreateInfo info{};
    info.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
    info.codeSize = code.size() * sizeof(uint32_t);
    info.pCode = code.data();
    VkShaderModule module = VK_NULL_HANDLE;
    check(vkCreateShaderModule(device, &info, nullptr, &module),
          "vkCreateShaderModule failed");
    return module;
}

std::vector<uint32_t> read_spirv(const std::string& path) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file) {
        throw std::runtime_error("cannot open SPIR-V file: " + path);
    }
    const std::streamsize size = file.tellg();
    if (size <= 0 || size % 4 != 0) {
        throw std::runtime_error("invalid SPIR-V size: " + path);
    }
    file.seekg(0);
    std::vector<uint32_t> code(static_cast<size_t>(size) / 4);
    file.read(reinterpret_cast<char*>(code.data()), size);
    if (!file) {
        throw std::runtime_error("failed to read SPIR-V file");
    }
    return code;
}

void write_ppm(
    const std::string& path,
    const std::vector<uint8_t>& rgba,
    uint32_t width,
    uint32_t height) {

    if (rgba.size() != static_cast<size_t>(width) * height * 4) {
        throw std::runtime_error("unexpected readback size");
    }
    std::ofstream output(path, std::ios::binary);
    if (!output) {
        throw std::runtime_error("cannot open output PPM: " + path);
    }
    output << "P6\n" << width << " " << height << "\n255\n";
    for (size_t i = 0; i < rgba.size(); i += 4) {
        output.put(static_cast<char>(rgba[i]));
        output.put(static_cast<char>(rgba[i + 1]));
        output.put(static_cast<char>(rgba[i + 2]));
    }
}

void destroy_buffer(Context& ctx, Buffer& buffer) {
    if (buffer.handle != VK_NULL_HANDLE) {
        vkDestroyBuffer(ctx.device, buffer.handle, nullptr);
        buffer.handle = VK_NULL_HANDLE;
    }
    if (buffer.memory != VK_NULL_HANDLE) {
        vkFreeMemory(ctx.device, buffer.memory, nullptr);
        buffer.memory = VK_NULL_HANDLE;
    }
}

void destroy_image(Context& ctx, Image& image) {
    if (image.view != VK_NULL_HANDLE) {
        vkDestroyImageView(ctx.device, image.view, nullptr);
        image.view = VK_NULL_HANDLE;
    }
    if (image.handle != VK_NULL_HANDLE) {
        vkDestroyImage(ctx.device, image.handle, nullptr);
        image.handle = VK_NULL_HANDLE;
    }
    if (image.memory != VK_NULL_HANDLE) {
        vkFreeMemory(ctx.device, image.memory, nullptr);
        image.memory = VK_NULL_HANDLE;
    }
}

}  // namespace

int main(int argc, char** argv) {
    const std::string packet_path =
        argc >= 2 ? argv[1] : "shift_vulkan_geometry.svpk";
    const std::string output =
        argc >= 3 ? argv[2] : "shift_vulkan_geometry.ppm";
    const std::string shader_dir =
        argc >= 4 ? argv[3] : "shaders";

    constexpr uint32_t width = 800;
    constexpr uint32_t height = 450;
    constexpr VkFormat color_format = VK_FORMAT_R8G8B8A8_UNORM;

    Context ctx{};
    Buffer vertex_buffer{};
    Buffer index_buffer{};
    Buffer staging{};
    Image color_image{};
    Image depth_image{};
    VkRenderPass render_pass = VK_NULL_HANDLE;
    VkFramebuffer framebuffer = VK_NULL_HANDLE;
    VkPipelineLayout pipeline_layout = VK_NULL_HANDLE;
    VkPipeline pipeline = VK_NULL_HANDLE;
    VkShaderModule vertex_shader = VK_NULL_HANDLE;
    VkShaderModule fragment_shader = VK_NULL_HANDLE;

    void* mapped = nullptr;

    try {
        const GeometryPacket packet = parse_packet(packet_path);
        ctx = create_context();

        VkFormatProperties color_props{};
        vkGetPhysicalDeviceFormatProperties(ctx.physical, color_format, &color_props);
        if ((color_props.optimalTilingFeatures &
             (VK_FORMAT_FEATURE_COLOR_ATTACHMENT_BIT |
              VK_FORMAT_FEATURE_TRANSFER_SRC_BIT)) !=
            (VK_FORMAT_FEATURE_COLOR_ATTACHMENT_BIT |
             VK_FORMAT_FEATURE_TRANSFER_SRC_BIT)) {
            throw std::runtime_error("R8G8B8A8_UNORM lacks required color features");
        }
        const VkFormat depth_format = choose_depth_format(ctx.physical);

        create_buffer(
            ctx,
            packet.vertex_bytes.size(),
            VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
            vertex_buffer);
        create_buffer(
            ctx,
            packet.indices.size() * sizeof(uint32_t),
            VK_BUFFER_USAGE_INDEX_BUFFER_BIT,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
            index_buffer);

        void* mapped = nullptr;
        check(vkMapMemory(
            ctx.device, vertex_buffer.memory, 0,
            packet.vertex_bytes.size(), 0, &mapped),
            "vkMapMemory(vertex) failed");
        std::memcpy(mapped, packet.vertex_bytes.data(), packet.vertex_bytes.size());
        vkUnmapMemory(ctx.device, vertex_buffer.memory);

        check(vkMapMemory(
            ctx.device, index_buffer.memory, 0,
            packet.indices.size() * sizeof(uint32_t), 0, &mapped),
            "vkMapMemory(index) failed");
        std::memcpy(
            mapped,
            packet.indices.data(),
            packet.indices.size() * sizeof(uint32_t));
        vkUnmapMemory(ctx.device, index_buffer.memory);

        create_image(
            ctx, width, height, color_format,
            VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT,
            VK_IMAGE_ASPECT_COLOR_BIT,
            VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT,
            color_image);
        create_image(
            ctx, width, height, depth_format,
            VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT,
            VK_IMAGE_ASPECT_DEPTH_BIT,
            VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT,
            depth_image);

        const std::vector<uint32_t> vertex_spirv =
            read_spirv(shader_dir + "/geometry.vert.spv");
        const std::vector<uint32_t> fragment_spirv =
            read_spirv(shader_dir + "/geometry.frag.spv");
        vertex_shader = shader_module(ctx.device, vertex_spirv);
        fragment_shader = shader_module(ctx.device, fragment_spirv);

        VkAttachmentDescription attachments[2]{};
        attachments[0].format = color_format;
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
        dependencies[0].dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT |
                                       VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT;
        dependencies[0].dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT |
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
        check(vkCreateRenderPass(ctx.device, &render_pass_info, nullptr, &render_pass),
              "vkCreateRenderPass failed");

        VkImageView views[2] = {color_image.view, depth_image.view};
        VkFramebufferCreateInfo framebuffer_info{};
        framebuffer_info.sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
        framebuffer_info.renderPass = render_pass;
        framebuffer_info.attachmentCount = 2;
        framebuffer_info.pAttachments = views;
        framebuffer_info.width = width;
        framebuffer_info.height = height;
        framebuffer_info.layers = 1;
        check(vkCreateFramebuffer(ctx.device, &framebuffer_info, nullptr, &framebuffer),
              "vkCreateFramebuffer failed");

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
        binding.stride = packet.header.stride;
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
        attributes.reserve(packet.attributes.size());
        for (const PacketAttribute& input : packet.attributes) {
            VkVertexInputAttributeDescription output{};
            output.location = input.location;
            output.binding = 0;
            output.format = vk_format(input.format);
            output.offset = input.offset;
            if (output.format == VK_FORMAT_UNDEFINED) {
                throw std::runtime_error("geometry packet contains unknown Vulkan attribute format");
            }
            attributes.push_back(output);
        }

        VkPipelineVertexInputStateCreateInfo vertex_input{};
        vertex_input.sType = VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO;
        vertex_input.vertexBindingDescriptionCount = 1;
        vertex_input.pVertexBindingDescriptions = &binding;
        vertex_input.vertexAttributeDescriptionCount = static_cast<uint32_t>(attributes.size());
        vertex_input.pVertexAttributeDescriptions = attributes.data();

        VkPipelineInputAssemblyStateCreateInfo input_assembly{};
        input_assembly.sType = VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO;
        input_assembly.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;

        VkViewport viewport{};
        viewport.width = static_cast<float>(width);
        viewport.height = static_cast<float>(height);
        viewport.minDepth = 0.0f;
        viewport.maxDepth = 1.0f;

        VkRect2D scissor{};
        scissor.extent = {width, height};

        VkPipelineViewportStateCreateInfo viewport_state{};
        viewport_state.sType = VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO;
        viewport_state.viewportCount = 1;
        viewport_state.pViewports = &viewport;
        viewport_state.scissorCount = 1;
        viewport_state.pScissors = &scissor;

        VkPipelineRasterizationStateCreateInfo rasterization{};
        rasterization.sType = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO;
        rasterization.polygonMode = VK_POLYGON_MODE_FILL;
        rasterization.cullMode = VK_CULL_MODE_NONE;
        rasterization.frontFace = VK_FRONT_FACE_COUNTER_CLOCKWISE;
        rasterization.lineWidth = 1.0f;

        VkPipelineMultisampleStateCreateInfo multisample{};
        multisample.sType = VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO;
        multisample.rasterizationSamples = VK_SAMPLE_COUNT_1_BIT;

        VkPipelineDepthStencilStateCreateInfo depth_stencil{};
        depth_stencil.sType = VK_STRUCTURE_TYPE_PIPELINE_DEPTH_STENCIL_STATE_CREATE_INFO;
        depth_stencil.depthTestEnable = VK_TRUE;
        depth_stencil.depthWriteEnable = VK_TRUE;
        depth_stencil.depthCompareOp = VK_COMPARE_OP_LESS_OR_EQUAL;

        VkPipelineColorBlendAttachmentState blend_attachment{};
        blend_attachment.blendEnable = VK_FALSE;
        blend_attachment.colorWriteMask =
            VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
            VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT;

        VkPipelineColorBlendStateCreateInfo blend{};
        blend.sType = VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO;
        blend.attachmentCount = 1;
        blend.pAttachments = &blend_attachment;

        VkPushConstantRange push_constant{};
        push_constant.stageFlags = VK_SHADER_STAGE_VERTEX_BIT;
        push_constant.offset = 0;
        push_constant.size = 16;

        VkPipelineLayoutCreateInfo layout_info{};
        layout_info.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
        layout_info.pushConstantRangeCount = 1;
        layout_info.pPushConstantRanges = &push_constant;
        check(vkCreatePipelineLayout(ctx.device, &layout_info, nullptr, &pipeline_layout),
              "vkCreatePipelineLayout failed");

        VkGraphicsPipelineCreateInfo pipeline_info{};
        pipeline_info.sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO;
        pipeline_info.stageCount = 2;
        pipeline_info.pStages = stages;
        pipeline_info.pVertexInputState = &vertex_input;
        pipeline_info.pInputAssemblyState = &input_assembly;
        pipeline_info.pViewportState = &viewport_state;
        pipeline_info.pRasterizationState = &rasterization;
        pipeline_info.pMultisampleState = &multisample;
        pipeline_info.pDepthStencilState = &depth_stencil;
        pipeline_info.pColorBlendState = &blend;
        pipeline_info.layout = pipeline_layout;
        pipeline_info.renderPass = render_pass;
        pipeline_info.subpass = 0;
        check(vkCreateGraphicsPipelines(
            ctx.device, VK_NULL_HANDLE, 1, &pipeline_info, nullptr, &pipeline),
            "vkCreateGraphicsPipelines failed");

        create_buffer(
            ctx,
            static_cast<VkDeviceSize>(width) * height * 4,
            VK_BUFFER_USAGE_TRANSFER_DST_BIT,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
            staging);

        VkCommandBufferAllocateInfo command_alloc{};
        command_alloc.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
        command_alloc.commandPool = ctx.command_pool;
        command_alloc.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        command_alloc.commandBufferCount = 1;
        VkCommandBuffer command = VK_NULL_HANDLE;
        check(vkAllocateCommandBuffers(
            ctx.device, &command_alloc, &command),
            "vkAllocateCommandBuffers failed");

        VkCommandBufferBeginInfo begin{};
        begin.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
        check(vkBeginCommandBuffer(command, &begin), "vkBeginCommandBuffer failed");

        VkRenderPassBeginInfo begin_pass{};
        begin_pass.sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
        begin_pass.renderPass = render_pass;
        begin_pass.framebuffer = framebuffer;
        begin_pass.renderArea.extent = {width, height};

        VkClearValue clear_values[2]{};
        clear_values[0].color.float32[0] = 0.02f;
        clear_values[0].color.float32[1] = 0.02f;
        clear_values[0].color.float32[2] = 0.02f;
        clear_values[0].color.float32[3] = 1.0f;
        clear_values[1].depthStencil.depth = 1.0f;
        clear_values[1].depthStencil.stencil = 0;
        begin_pass.clearValueCount = 2;
        begin_pass.pClearValues = clear_values;

        vkCmdBeginRenderPass(command, &begin_pass, VK_SUBPASS_CONTENTS_INLINE);
        vkCmdBindPipeline(command, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline);

        VkDeviceSize vertex_offset = 0;
        vkCmdBindVertexBuffers(command, 0, 1, &vertex_buffer.handle, &vertex_offset);
        vkCmdBindIndexBuffer(command, index_buffer.handle, 0, VK_INDEX_TYPE_UINT32);

        const float push_values[4] = {
            packet.header.center_x,
            packet.header.center_y,
            packet.header.center_z,
            packet.header.scale,
        };
        vkCmdPushConstants(
            command, pipeline_layout, VK_SHADER_STAGE_VERTEX_BIT,
            0, sizeof(push_values), push_values);

        vkCmdDrawIndexed(
            command,
            packet.header.index_count,
            1,
            packet.header.first_index,
            0,
            0);
        vkCmdEndRenderPass(command);

        VkBufferImageCopy copy{};
        copy.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        copy.imageSubresource.layerCount = 1;
        copy.imageExtent = {width, height, 1};
        vkCmdCopyImageToBuffer(
            command,
            color_image.handle,
            VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
            staging.handle,
            1,
            &copy);

        check(vkEndCommandBuffer(command), "vkEndCommandBuffer failed");

        VkSubmitInfo submit{};
        submit.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
        submit.commandBufferCount = 1;
        submit.pCommandBuffers = &command;
        check(vkQueueSubmit(ctx.queue, 1, &submit, VK_NULL_HANDLE),
              "vkQueueSubmit failed");
        check(vkQueueWaitIdle(ctx.queue), "vkQueueWaitIdle failed");

        check(vkMapMemory(
            ctx.device, staging.memory, 0,
            static_cast<VkDeviceSize>(width) * height * 4,
            0, &mapped),
            "vkMapMemory(staging) failed");
        std::vector<uint8_t> rgba(
            static_cast<size_t>(width) * height * 4);
        std::memcpy(rgba.data(), mapped, rgba.size());
        vkUnmapMemory(ctx.device, staging.memory);

        write_ppm(output, rgba, width, height);

        VkPhysicalDeviceProperties props{};
        vkGetPhysicalDeviceProperties(ctx.physical, &props);
        std::cout << "{\n";
        std::cout << "  \"format\": \"SHIFT.VulkanRenderCommandGeometry/1\",\n";
        std::cout << "  \"device\": \"" << props.deviceName << "\",\n";
        std::cout << "  \"queue_family\": " << ctx.queue_family << ",\n";
        std::cout << "  \"width\": " << width << ",\n";
        std::cout << "  \"height\": " << height << ",\n";
        std::cout << "  \"vertex_count\": " << packet.header.vertex_count << ",\n";
        std::cout << "  \"index_count\": " << packet.header.index_count << ",\n";
        std::cout << "  \"stride\": " << packet.header.stride << ",\n";
        std::cout << "  \"attribute_count\": " << packet.attributes.size() << ",\n";
        std::cout << "  \"depth_format\": " << static_cast<int>(depth_format) << ",\n";
        std::cout << "  \"output\": \"" << output << "\"\n";
        std::cout << "}\n";

        vkFreeCommandBuffers(ctx.device, ctx.command_pool, 1, &command);
        destroy_buffer(ctx, staging);
        destroy_buffer(ctx, index_buffer);
        destroy_buffer(ctx, vertex_buffer);
        vkDestroyPipeline(ctx.device, pipeline, nullptr);
        vkDestroyPipelineLayout(ctx.device, pipeline_layout, nullptr);
        vkDestroyFramebuffer(ctx.device, framebuffer, nullptr);
        vkDestroyRenderPass(ctx.device, render_pass, nullptr);
        vkDestroyShaderModule(ctx.device, vertex_shader, nullptr);
        vkDestroyShaderModule(ctx.device, fragment_shader, nullptr);
        destroy_image(ctx, depth_image);
        destroy_image(ctx, color_image);
        destroy(ctx);
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "shift_vulkan_render_geometry: " << error.what() << "\n";
        if (ctx.device != VK_NULL_HANDLE) {
            destroy_buffer(ctx, staging);
            destroy_buffer(ctx, index_buffer);
            destroy_buffer(ctx, vertex_buffer);
            if (pipeline != VK_NULL_HANDLE) vkDestroyPipeline(ctx.device, pipeline, nullptr);
            if (pipeline_layout != VK_NULL_HANDLE) vkDestroyPipelineLayout(ctx.device, pipeline_layout, nullptr);
            if (framebuffer != VK_NULL_HANDLE) vkDestroyFramebuffer(ctx.device, framebuffer, nullptr);
            if (render_pass != VK_NULL_HANDLE) vkDestroyRenderPass(ctx.device, render_pass, nullptr);
            if (vertex_shader != VK_NULL_HANDLE) vkDestroyShaderModule(ctx.device, vertex_shader, nullptr);
            if (fragment_shader != VK_NULL_HANDLE) vkDestroyShaderModule(ctx.device, fragment_shader, nullptr);
            destroy_image(ctx, depth_image);
            destroy_image(ctx, color_image);
        }
        destroy(ctx);
        return EXIT_FAILURE;
    }
}
