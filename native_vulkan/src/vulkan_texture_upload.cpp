#include <vulkan/vulkan.h>

#include <cstdint>
#include <cstdlib>
#include <limits>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#pragma pack(push, 1)
struct PacketHeader {
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
#pragma pack(pop)

static_assert(sizeof(PacketHeader) == 20, "unexpected texture header size");
static_assert(sizeof(TextureRecord) == 24, "unexpected texture record size");

namespace {

[[noreturn]] void fail(const std::string& message, VkResult result) {
    throw std::runtime_error(message + " (" + std::to_string(static_cast<int>(result)) + ")");
}

void check(VkResult result, const char* message) {
    if (result != VK_SUCCESS) fail(message, result);
}

uint32_t memory_type(VkPhysicalDevice physical, uint32_t bits, VkMemoryPropertyFlags required) {
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

struct Texture {
    VkImage image = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
    VkImageView view = VK_NULL_HANDLE;
    VkSampler sampler = VK_NULL_HANDLE;
    Buffer staging{};
    uint32_t width = 0;
    uint32_t height = 0;
    uint32_t mode = 0;
    uint32_t reg = 0;
};

struct Packet {
    PacketHeader header{};
    std::vector<TextureRecord> records;
    std::vector<uint8_t> bytes;
};

void destroy(Context& ctx) {
    if (ctx.device != VK_NULL_HANDLE) {
        vkDeviceWaitIdle(ctx.device);
        if (ctx.command_pool != VK_NULL_HANDLE) {
            vkDestroyCommandPool(ctx.device, ctx.command_pool, nullptr);
        }
        vkDestroyDevice(ctx.device, nullptr);
    }
    if (ctx.instance != VK_NULL_HANDLE) vkDestroyInstance(ctx.instance, nullptr);
}

Context create_context() {
    Context ctx{};

    VkApplicationInfo app{};
    app.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
    app.pApplicationName = "SHIFT Vulkan Texture Upload";
    app.applicationVersion = 1;
    app.pEngineName = "SHIFT";
    app.engineVersion = 1;
    app.apiVersion = VK_API_VERSION_1_0;

    VkInstanceCreateInfo instance_info{};
    instance_info.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    instance_info.pApplicationInfo = &app;
    check(vkCreateInstance(&instance_info, nullptr, &ctx.instance), "vkCreateInstance failed");

    uint32_t count = 0;
    check(vkEnumeratePhysicalDevices(ctx.instance, &count, nullptr),
          "vkEnumeratePhysicalDevices(count) failed");
    if (!count) throw std::runtime_error("no Vulkan physical devices");
    std::vector<VkPhysicalDevice> devices(count);
    check(vkEnumeratePhysicalDevices(ctx.instance, &count, devices.data()),
          "vkEnumeratePhysicalDevices(data) failed");

    for (VkPhysicalDevice candidate : devices) {
        uint32_t families_count = 0;
        vkGetPhysicalDeviceQueueFamilyProperties(candidate, &families_count, nullptr);
        std::vector<VkQueueFamilyProperties> families(families_count);
        vkGetPhysicalDeviceQueueFamilyProperties(candidate, &families_count, families.data());
        for (uint32_t i = 0; i < families_count; ++i) {
            if (families[i].queueFlags & VK_QUEUE_GRAPHICS_BIT) {
                ctx.physical = candidate;
                ctx.queue_family = i;
                break;
            }
        }
        if (ctx.physical != VK_NULL_HANDLE) break;
    }
    if (ctx.physical == VK_NULL_HANDLE) throw std::runtime_error("no graphics queue");

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

std::vector<uint8_t> read_file(const std::string& path) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file) throw std::runtime_error("cannot open texture packet: " + path);
    const std::streamsize size = file.tellg();
    if (size <= 0) throw std::runtime_error("texture packet empty");
    file.seekg(0);
    std::vector<uint8_t> data(static_cast<size_t>(size));
    file.read(reinterpret_cast<char*>(data.data()), size);
    if (!file) throw std::runtime_error("texture packet read failed");
    return data;
}

Packet parse_packet(const std::string& path) {
    const auto data = read_file(path);
    if (data.size() < sizeof(PacketHeader)) throw std::runtime_error("texture packet truncated");

    Packet packet{};
    std::memcpy(&packet.header, data.data(), sizeof(packet.header));
    if (std::memcmp(packet.header.magic, "SVTP", 4) != 0 || packet.header.version != 1) {
        throw std::runtime_error("unsupported SHIFT Vulkan texture packet");
    }
    if (packet.header.descriptor_set != 1 || packet.header.texture_count == 0 ||
        packet.header.texture_count > 16) {
        throw std::runtime_error("invalid texture packet descriptor set/count");
    }

    const size_t records_bytes =
        static_cast<size_t>(packet.header.texture_count) * sizeof(TextureRecord);
    const size_t pixel_base = sizeof(PacketHeader) + records_bytes;
    if (data.size() < pixel_base) throw std::runtime_error("texture packet record table truncated");

    packet.records.resize(packet.header.texture_count);
    std::memcpy(packet.records.data(), data.data() + sizeof(PacketHeader), records_bytes);
    bool sampler_s1_seen = false;
    for (const auto& record : packet.records) {
        const uint64_t expected_bytes =
            static_cast<uint64_t>(record.width) * static_cast<uint64_t>(record.height) * 4u;
        if (record.register_index > 15 ||
            record.width == 0 || record.height == 0 ||
            expected_bytes > std::numeric_limits<uint32_t>::max() ||
            record.pixel_bytes != static_cast<uint32_t>(expected_bytes) ||
            record.pixel_offset < pixel_base ||
            static_cast<uint64_t>(record.pixel_offset) + record.pixel_bytes > data.size() ||
            record.sampler_mode < 1 || record.sampler_mode > 4) {
            throw std::runtime_error("invalid texture packet record");
        }
        if (record.register_index == 1) sampler_s1_seen = true;
    }
    if (!sampler_s1_seen) {
        throw std::runtime_error("Phase 214 texture shader requires sampler register s1");
    }
    packet.bytes = data;
    return packet;
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
    check(vkCreateBuffer(ctx.device, &info, nullptr, &out.handle), "vkCreateBuffer failed");

    VkMemoryRequirements req{};
    vkGetBufferMemoryRequirements(ctx.device, out.handle, &req);

    VkMemoryAllocateInfo alloc{};
    alloc.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    alloc.allocationSize = req.size;
    alloc.memoryTypeIndex = memory_type(ctx.physical, req.memoryTypeBits, properties);
    check(vkAllocateMemory(ctx.device, &alloc, nullptr, &out.memory),
          "vkAllocateMemory buffer failed");
    check(vkBindBufferMemory(ctx.device, out.handle, out.memory, 0),
          "vkBindBufferMemory failed");
}

void create_texture(Context& ctx, const TextureRecord& record, const Packet& packet, Texture& out) {
    out.width = record.width;
    out.height = record.height;
    out.mode = record.sampler_mode;
    out.reg = record.register_index;

    const size_t size = record.pixel_bytes;
    const uint8_t* pixels = packet.bytes.data() + record.pixel_offset;
    create_buffer(
        ctx, static_cast<VkDeviceSize>(size),
        VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
        VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
        out.staging);

    void* mapped = nullptr;
    check(vkMapMemory(ctx.device, out.staging.memory, 0, size, 0, &mapped),
          "vkMapMemory(texture staging) failed");
    std::memcpy(mapped, pixels, size);
    vkUnmapMemory(ctx.device, out.staging.memory);

    VkImageCreateInfo info{};
    info.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
    info.imageType = VK_IMAGE_TYPE_2D;
    info.format = VK_FORMAT_R8G8B8A8_UNORM;
    info.extent = {out.width, out.height, 1};
    info.mipLevels = 1;
    info.arrayLayers = 1;
    info.samples = VK_SAMPLE_COUNT_1_BIT;
    info.tiling = VK_IMAGE_TILING_OPTIMAL;
    info.usage = VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_SAMPLED_BIT;
    info.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    check(vkCreateImage(ctx.device, &info, nullptr, &out.image), "vkCreateImage texture failed");

    VkMemoryRequirements req{};
    vkGetImageMemoryRequirements(ctx.device, out.image, &req);
    VkMemoryAllocateInfo alloc{};
    alloc.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    alloc.allocationSize = req.size;
    alloc.memoryTypeIndex = memory_type(
        ctx.physical, req.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    check(vkAllocateMemory(ctx.device, &alloc, nullptr, &out.memory),
          "vkAllocateMemory texture failed");
    check(vkBindImageMemory(ctx.device, out.image, out.memory, 0),
          "vkBindImageMemory texture failed");

    VkImageViewCreateInfo view{};
    view.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
    view.image = out.image;
    view.viewType = VK_IMAGE_VIEW_TYPE_2D;
    view.format = VK_FORMAT_R8G8B8A8_UNORM;
    view.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    view.subresourceRange.levelCount = 1;
    view.subresourceRange.layerCount = 1;
    check(vkCreateImageView(ctx.device, &view, nullptr, &out.view),
          "vkCreateImageView texture failed");

    VkSamplerCreateInfo sampler{};
    sampler.sType = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO;
    const bool linear = record.sampler_mode == 2 || record.sampler_mode == 4;
    const bool clamp = record.sampler_mode == 3 || record.sampler_mode == 4;
    sampler.magFilter = linear ? VK_FILTER_LINEAR : VK_FILTER_NEAREST;
    sampler.minFilter = linear ? VK_FILTER_LINEAR : VK_FILTER_NEAREST;
    sampler.mipmapMode = VK_SAMPLER_MIPMAP_MODE_NEAREST;
    sampler.addressModeU = clamp ? VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE : VK_SAMPLER_ADDRESS_MODE_REPEAT;
    sampler.addressModeV = clamp ? VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE : VK_SAMPLER_ADDRESS_MODE_REPEAT;
    sampler.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    sampler.maxLod = 1.0f;
    check(vkCreateSampler(ctx.device, &sampler, nullptr, &out.sampler),
          "vkCreateSampler failed");
}

void transition_texture(
    VkCommandBuffer command,
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

    vkCmdPipelineBarrier(
        command, src_stage, dst_stage, 0,
        0, nullptr, 0, nullptr, 1, &barrier);
}

void destroy_buffer(Context& ctx, Buffer& buffer) {
    if (buffer.handle) vkDestroyBuffer(ctx.device, buffer.handle, nullptr);
    if (buffer.memory) vkFreeMemory(ctx.device, buffer.memory, nullptr);
    buffer.handle = VK_NULL_HANDLE;
    buffer.memory = VK_NULL_HANDLE;
}

void destroy_texture(Context& ctx, Texture& texture) {
    if (texture.sampler) vkDestroySampler(ctx.device, texture.sampler, nullptr);
    if (texture.view) vkDestroyImageView(ctx.device, texture.view, nullptr);
    if (texture.image) vkDestroyImage(ctx.device, texture.image, nullptr);
    if (texture.memory) vkFreeMemory(ctx.device, texture.memory, nullptr);
    destroy_buffer(ctx, texture.staging);
}

void write_ppm(const std::string& path, const std::vector<uint8_t>& rgba) {
    std::ofstream out(path, std::ios::binary);
    if (!out) throw std::runtime_error("cannot open output PPM");
    out << "P6\n256 256\n255\n";
    for (size_t i = 0; i < rgba.size(); i += 4) {
        out.put(static_cast<char>(rgba[i]));
        out.put(static_cast<char>(rgba[i + 1]));
        out.put(static_cast<char>(rgba[i + 2]));
    }
}

std::vector<uint32_t> read_spirv(const std::string& path) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file) throw std::runtime_error("cannot open SPIR-V: " + path);
    const std::streamsize size = file.tellg();
    if (size <= 0 || size % 4 != 0) throw std::runtime_error("invalid SPIR-V");
    file.seekg(0);
    std::vector<uint32_t> code(static_cast<size_t>(size) / 4);
    file.seekg(0);
    file.read(reinterpret_cast<char*>(code.data()), size);
    return code;
}

VkShaderModule make_shader(Context& ctx, const std::string& path) {
    const auto code = read_spirv(path);
    VkShaderModuleCreateInfo info{};
    info.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
    info.codeSize = code.size() * sizeof(uint32_t);
    info.pCode = code.data();
    VkShaderModule module = VK_NULL_HANDLE;
    check(vkCreateShaderModule(ctx.device, &info, nullptr, &module), "vkCreateShaderModule failed");
    return module;
}

}  // namespace

int main(int argc, char** argv) {
    const std::string packet_path = argc >= 2 ? argv[1] : "shift_vulkan_texture.svtp";
    const std::string output = argc >= 3 ? argv[2] : "shift_vulkan_texture.ppm";
    const std::string shader_dir = argc >= 4 ? argv[3] : "shaders";

    Context ctx{};
    std::vector<Texture> textures;
    VkDescriptorSetLayout empty_set_layout = VK_NULL_HANDLE;
    VkDescriptorSetLayout set_layout = VK_NULL_HANDLE;
    VkDescriptorPool pool = VK_NULL_HANDLE;
    VkDescriptorSet set = VK_NULL_HANDLE;
    VkShaderModule vert = VK_NULL_HANDLE;
    VkShaderModule frag = VK_NULL_HANDLE;
    VkRenderPass render_pass = VK_NULL_HANDLE;
    VkFramebuffer framebuffer = VK_NULL_HANDLE;
    VkPipelineLayout pipeline_layout = VK_NULL_HANDLE;
    VkPipeline pipeline = VK_NULL_HANDLE;
    Image dummy{};
    Image color{};
    Buffer staging{};
    VkCommandBuffer command = VK_NULL_HANDLE;

    try {
        const Packet packet = parse_packet(packet_path);
        ctx = create_context();
        textures.resize(packet.records.size());
        for (size_t i = 0; i < packet.records.size(); ++i) {
            create_texture(ctx, packet.records[i], packet, textures[i]);
        }

        std::vector<VkDescriptorSetLayoutBinding> bindings;
        bindings.reserve(textures.size());
        for (const Texture& texture : textures) {
            VkDescriptorSetLayoutBinding binding{};
            binding.binding = texture.reg;
            binding.descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
            binding.descriptorCount = 1;
            binding.stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT;
            bindings.push_back(binding);
        }
        VkDescriptorSetLayoutCreateInfo empty_set_info{};
        empty_set_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
        check(vkCreateDescriptorSetLayout(
            ctx.device, &empty_set_info, nullptr, &empty_set_layout),
            "vkCreateDescriptorSetLayout(empty set) failed");

        VkDescriptorSetLayoutCreateInfo set_info{};
        set_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
        set_info.bindingCount = static_cast<uint32_t>(bindings.size());
        set_info.pBindings = bindings.data();
        check(vkCreateDescriptorSetLayout(ctx.device, &set_info, nullptr, &set_layout),
              "vkCreateDescriptorSetLayout failed");

        VkDescriptorPoolSize pool_size{};
        pool_size.type = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
        pool_size.descriptorCount = static_cast<uint32_t>(textures.size());
        VkDescriptorPoolCreateInfo pool_info{};
        pool_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;
        pool_info.maxSets = 1;
        pool_info.poolSizeCount = 1;
        pool_info.pPoolSizes = &pool_size;
        check(vkCreateDescriptorPool(ctx.device, &pool_info, nullptr, &pool),
              "vkCreateDescriptorPool failed");

        VkDescriptorSetAllocateInfo set_alloc{};
        set_alloc.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
        set_alloc.descriptorPool = pool;
        set_alloc.descriptorSetCount = 1;
        set_alloc.pSetLayouts = &set_layout;
        check(vkAllocateDescriptorSets(ctx.device, &set_alloc, &set),
              "vkAllocateDescriptorSets failed");

        std::vector<VkDescriptorImageInfo> descriptor_images(textures.size());
        std::vector<VkWriteDescriptorSet> writes(textures.size());
        for (size_t i = 0; i < textures.size(); ++i) {
            descriptor_images[i].sampler = textures[i].sampler;
            descriptor_images[i].imageView = textures[i].view;
            descriptor_images[i].imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
            writes[i].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
            writes[i].dstSet = set;
            writes[i].dstBinding = textures[i].reg;
            writes[i].descriptorCount = 1;
            writes[i].descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
            writes[i].pImageInfo = &descriptor_images[i];
        }
        vkUpdateDescriptorSets(ctx.device, static_cast<uint32_t>(writes.size()), writes.data(), 0, nullptr);

        vert = make_shader(ctx, shader_dir + "/texture.vert.spv");
        frag = make_shader(ctx, shader_dir + "/texture.frag.spv");

        create_image_placeholder:
        {
            VkImageCreateInfo info{};
            info.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
            info.imageType = VK_IMAGE_TYPE_2D;
            info.format = VK_FORMAT_R8G8B8A8_UNORM;
            info.extent = {256,256,1};
            info.mipLevels = 1;
            info.arrayLayers = 1;
            info.samples = VK_SAMPLE_COUNT_1_BIT;
            info.tiling = VK_IMAGE_TILING_OPTIMAL;
            info.usage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
            info.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
            check(vkCreateImage(ctx.device,&info,nullptr,&color.handle),"vkCreateImage color failed");
            VkMemoryRequirements req{};
            vkGetImageMemoryRequirements(ctx.device,color.handle,&req);
            VkMemoryAllocateInfo alloc{};
            alloc.sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
            alloc.allocationSize=req.size;
            alloc.memoryTypeIndex=memory_type(ctx.physical,req.memoryTypeBits,VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
            check(vkAllocateMemory(ctx.device,&alloc,nullptr,&color.memory),"vkAllocateMemory color failed");
            check(vkBindImageMemory(ctx.device,color.handle,color.memory,0),"vkBindImageMemory color failed");
            VkImageViewCreateInfo view{};
            view.sType=VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
            view.image=color.handle;
            view.viewType=VK_IMAGE_VIEW_TYPE_2D;
            view.format=VK_FORMAT_R8G8B8A8_UNORM;
            view.subresourceRange.aspectMask=VK_IMAGE_ASPECT_COLOR_BIT;
            view.subresourceRange.levelCount=1;
            view.subresourceRange.layerCount=1;
            check(vkCreateImageView(ctx.device,&view,nullptr,&color.view),"vkCreateImageView color failed");
        }

        VkAttachmentDescription attachment{};
        attachment.format = VK_FORMAT_R8G8B8A8_UNORM;
        attachment.samples = VK_SAMPLE_COUNT_1_BIT;
        attachment.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
        attachment.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
        attachment.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        attachment.finalLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
        VkAttachmentReference color_ref{};
        color_ref.attachment=0;
        color_ref.layout=VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
        VkSubpassDescription subpass{};
        subpass.pipelineBindPoint=VK_PIPELINE_BIND_POINT_GRAPHICS;
        subpass.colorAttachmentCount=1;
        subpass.pColorAttachments=&color_ref;
        VkSubpassDependency deps[2]{};
        deps[0].srcSubpass=VK_SUBPASS_EXTERNAL;
        deps[0].dstSubpass=0;
        deps[0].srcStageMask=VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT;
        deps[0].dstStageMask=VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
        deps[0].dstAccessMask=VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
        deps[1].srcSubpass=0;
        deps[1].dstSubpass=VK_SUBPASS_EXTERNAL;
        deps[1].srcStageMask=VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
        deps[1].srcAccessMask=VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
        deps[1].dstStageMask=VK_PIPELINE_STAGE_TRANSFER_BIT;
        deps[1].dstAccessMask=VK_ACCESS_TRANSFER_READ_BIT;
        VkRenderPassCreateInfo render{};
        render.sType=VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
        render.attachmentCount=1;
        render.pAttachments=&attachment;
        render.subpassCount=1;
        render.pSubpasses=&subpass;
        render.dependencyCount=2;
        render.pDependencies=deps;
        check(vkCreateRenderPass(ctx.device,&render,nullptr,&render_pass),"vkCreateRenderPass failed");

        VkFramebufferCreateInfo fb{};
        fb.sType=VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
        fb.renderPass=render_pass;
        fb.attachmentCount=1;
        fb.pAttachments=&color.view;
        fb.width=256;
        fb.height=256;
        fb.layers=1;
        check(vkCreateFramebuffer(ctx.device,&fb,nullptr,&framebuffer),"vkCreateFramebuffer failed");

        VkPipelineShaderStageCreateInfo stages[2]{};
        stages[0].sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        stages[0].stage=VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module=vert;
        stages[0].pName="main";
        stages[1].sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        stages[1].stage=VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module=frag;
        stages[1].pName="main";

        VkPipelineVertexInputStateCreateInfo vi{};
        vi.sType=VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO;
        VkPipelineInputAssemblyStateCreateInfo ia{};
        ia.sType=VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO;
        ia.topology=VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;

        VkViewport viewport{0,0,256,256,0,1};
        VkRect2D scissor{{0,0},{256,256}};
        VkPipelineViewportStateCreateInfo vp{};
        vp.sType=VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO;
        vp.viewportCount=1;
        vp.pViewports=&viewport;
        vp.scissorCount=1;
        vp.pScissors=&scissor;

        VkPipelineRasterizationStateCreateInfo raster{};
        raster.sType=VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO;
        raster.polygonMode=VK_POLYGON_MODE_FILL;
        raster.cullMode=VK_CULL_MODE_NONE;
        raster.frontFace=VK_FRONT_FACE_COUNTER_CLOCKWISE;
        raster.lineWidth=1.0f;

        VkPipelineMultisampleStateCreateInfo ms{};
        ms.sType=VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO;
        ms.rasterizationSamples=VK_SAMPLE_COUNT_1_BIT;

        VkPipelineColorBlendAttachmentState blend_attachment{};
        blend_attachment.blendEnable=VK_FALSE;
        blend_attachment.colorWriteMask=VK_COLOR_COMPONENT_R_BIT|VK_COLOR_COMPONENT_G_BIT|
                                         VK_COLOR_COMPONENT_B_BIT|VK_COLOR_COMPONENT_A_BIT;
        VkPipelineColorBlendStateCreateInfo blend{};
        blend.sType=VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO;
        blend.attachmentCount=1;
        blend.pAttachments=&blend_attachment;

        VkDescriptorSetLayout pipeline_sets[2] = {
            empty_set_layout,
            set_layout,
        };
        VkPipelineLayoutCreateInfo layout{};
        layout.sType=VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
        layout.setLayoutCount=2;
        layout.pSetLayouts=pipeline_sets;
        check(vkCreatePipelineLayout(ctx.device,&layout,nullptr,&pipeline_layout),
              "vkCreatePipelineLayout failed");

        VkGraphicsPipelineCreateInfo pipeline_info{};
        pipeline_info.sType=VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO;
        pipeline_info.stageCount=2;
        pipeline_info.pStages=stages;
        pipeline_info.pVertexInputState=&vi;
        pipeline_info.pInputAssemblyState=&ia;
        pipeline_info.pViewportState=&vp;
        pipeline_info.pRasterizationState=&raster;
        pipeline_info.pMultisampleState=&ms;
        pipeline_info.pColorBlendState=&blend;
        pipeline_info.layout=pipeline_layout;
        pipeline_info.renderPass=render_pass;
        check(vkCreateGraphicsPipelines(ctx.device,VK_NULL_HANDLE,1,&pipeline_info,nullptr,&pipeline),
              "vkCreateGraphicsPipelines failed");

        create_buffer(ctx, 256u*256u*4u, VK_BUFFER_USAGE_TRANSFER_DST_BIT,
                      VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
                      staging);

        VkCommandBufferAllocateInfo ca{};
        ca.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
        ca.commandPool=ctx.command_pool;
        ca.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        ca.commandBufferCount=1;
        check(vkAllocateCommandBuffers(ctx.device,&ca,&command),"vkAllocateCommandBuffers failed");
        VkCommandBufferBeginInfo begin{};
        begin.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
        check(vkBeginCommandBuffer(command,&begin),"vkBeginCommandBuffer failed");

        for (Texture& texture : textures) {
            transition_texture(command, texture.image, VK_IMAGE_LAYOUT_UNDEFINED,
                               VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 0,
                               VK_ACCESS_TRANSFER_WRITE_BIT,
                               VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                               VK_PIPELINE_STAGE_TRANSFER_BIT);
            VkBufferImageCopy copy{};
            copy.imageSubresource.aspectMask=VK_IMAGE_ASPECT_COLOR_BIT;
            copy.imageSubresource.layerCount=1;
            copy.imageExtent={texture.width,texture.height,1};
            vkCmdCopyBufferToImage(command, texture.staging.handle, texture.image,
                                   VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,1,&copy);
            transition_texture(command, texture.image, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                               VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                               VK_ACCESS_TRANSFER_WRITE_BIT,
                               VK_ACCESS_SHADER_READ_BIT,
                               VK_PIPELINE_STAGE_TRANSFER_BIT,
                               VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT);
        }

        VkRenderPassBeginInfo pass{};
        pass.sType=VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
        pass.renderPass=render_pass;
        pass.framebuffer=framebuffer;
        pass.renderArea.extent={256,256};
        VkClearValue clear{};
        clear.color.float32[0]=0.02f;
        clear.color.float32[1]=0.02f;
        clear.color.float32[2]=0.02f;
        clear.color.float32[3]=1.0f;
        pass.clearValueCount=1;
        pass.pClearValues=&clear;

        vkCmdBeginRenderPass(command,&pass,VK_SUBPASS_CONTENTS_INLINE);
        vkCmdBindPipeline(command,VK_PIPELINE_BIND_POINT_GRAPHICS,pipeline);
        vkCmdBindDescriptorSets(command,VK_PIPELINE_BIND_POINT_GRAPHICS,pipeline_layout,
                                1,1,&set,0,nullptr);
        vkCmdDraw(command,3,1,0,0);
        vkCmdEndRenderPass(command);

        VkBufferImageCopy readback{};
        readback.imageSubresource.aspectMask=VK_IMAGE_ASPECT_COLOR_BIT;
        readback.imageSubresource.layerCount=1;
        readback.imageExtent={256,256,1};
        vkCmdCopyImageToBuffer(command,color.handle,VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                               staging.handle,1,&readback);
        check(vkEndCommandBuffer(command),"vkEndCommandBuffer failed");

        VkSubmitInfo submit{};
        submit.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO;
        submit.commandBufferCount=1;
        submit.pCommandBuffers=&command;
        check(vkQueueSubmit(ctx.queue,1,&submit,VK_NULL_HANDLE),"vkQueueSubmit failed");
        check(vkQueueWaitIdle(ctx.queue),"vkQueueWaitIdle failed");

        void* mapped=nullptr;
        check(vkMapMemory(ctx.device,staging.memory,0,256u*256u*4u,0,&mapped),
              "vkMapMemory readback failed");
        std::vector<uint8_t> rgba(256u*256u*4u);
        std::memcpy(rgba.data(),mapped,rgba.size());
        vkUnmapMemory(ctx.device,staging.memory);
        write_ppm(output,rgba);

        VkPhysicalDeviceProperties props{};
        vkGetPhysicalDeviceProperties(ctx.physical,&props);
        std::cout << "{\n";
        std::cout << "  \"format\": \"SHIFT.VulkanTextureUpload/1\",\n";
        std::cout << "  \"device\": \"" << props.deviceName << "\",\n";
        std::cout << "  \"descriptor_set\": 1,\n";
        std::cout << "  \"texture_count\": " << textures.size() << ",\n";
        std::cout << "  \"output\": \"" << output << "\"\n";
        std::cout << "}\n";

        vkFreeCommandBuffers(ctx.device,ctx.command_pool,1,&command);
        destroy_buffer(ctx,staging);
        if (pipeline) vkDestroyPipeline(ctx.device,pipeline,nullptr);
        if (pipeline_layout) vkDestroyPipelineLayout(ctx.device,pipeline_layout,nullptr);
        if (pool) vkDestroyDescriptorPool(ctx.device,pool,nullptr);
        if (set_layout) vkDestroyDescriptorSetLayout(ctx.device,set_layout,nullptr);
        if (empty_set_layout) vkDestroyDescriptorSetLayout(ctx.device,empty_set_layout,nullptr);
        if (framebuffer) vkDestroyFramebuffer(ctx.device,framebuffer,nullptr);
        if (render_pass) vkDestroyRenderPass(ctx.device,render_pass,nullptr);
        if (vert) vkDestroyShaderModule(ctx.device,vert,nullptr);
        if (frag) vkDestroyShaderModule(ctx.device,frag,nullptr);
        if (color.view) vkDestroyImageView(ctx.device,color.view,nullptr);
        if (color.handle) vkDestroyImage(ctx.device,color.handle,nullptr);
        if (color.memory) vkFreeMemory(ctx.device,color.memory,nullptr);
        for (auto& texture : textures) destroy_texture(ctx,texture);
        destroy(ctx);
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "shift_vulkan_texture_upload: " << error.what() << "\n";
        if (ctx.device != VK_NULL_HANDLE) {
            if (pipeline) vkDestroyPipeline(ctx.device,pipeline,nullptr);
            if (pipeline_layout) vkDestroyPipelineLayout(ctx.device,pipeline_layout,nullptr);
            if (pool) vkDestroyDescriptorPool(ctx.device,pool,nullptr);
            if (set_layout) vkDestroyDescriptorSetLayout(ctx.device,set_layout,nullptr);
            if (framebuffer) vkDestroyFramebuffer(ctx.device,framebuffer,nullptr);
            if (render_pass) vkDestroyRenderPass(ctx.device,render_pass,nullptr);
            if (vert) vkDestroyShaderModule(ctx.device,vert,nullptr);
            if (frag) vkDestroyShaderModule(ctx.device,frag,nullptr);
            if (color.view) vkDestroyImageView(ctx.device,color.view,nullptr);
            if (color.handle) vkDestroyImage(ctx.device,color.handle,nullptr);
            if (color.memory) vkFreeMemory(ctx.device,color.memory,nullptr);
            destroy_buffer(ctx,staging);
            for (auto& texture : textures) destroy_texture(ctx,texture);
        }
        destroy(ctx);
        return EXIT_FAILURE;
    }
}
