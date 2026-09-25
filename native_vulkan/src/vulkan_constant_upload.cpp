#include <vulkan/vulkan.h>

#include <cstdint>
#include <cstdlib>
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
    uint32_t max_registers;
    uint32_t register_bytes;
    uint32_t vertex_populated_count;
    uint32_t pixel_populated_count;
    uint32_t reserved;
};
#pragma pack(pop)

static_assert(sizeof(PacketHeader) == 28, "unexpected Vulkan constant header size");

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

struct Image {
    VkImage handle = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
    VkImageView view = VK_NULL_HANDLE;
};

struct ConstantPacket {
    PacketHeader header{};
    std::vector<float> vertex;
    std::vector<float> pixel;
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
    app.pApplicationName = "SHIFT Vulkan Constant Upload";
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
    if (!file) throw std::runtime_error("cannot open constant packet: " + path);
    const std::streamsize size = file.tellg();
    if (size <= 0) throw std::runtime_error("constant packet is empty");
    file.seekg(0);
    std::vector<uint8_t> data(static_cast<size_t>(size));
    file.read(reinterpret_cast<char*>(data.data()), size);
    if (!file) throw std::runtime_error("failed reading constant packet");
    return data;
}

ConstantPacket parse_packet(const std::string& path) {
    const std::vector<uint8_t> data = read_file(path);
    if (data.size() < sizeof(PacketHeader)) throw std::runtime_error("constant packet truncated");

    ConstantPacket packet{};
    std::memcpy(&packet.header, data.data(), sizeof(packet.header));
    if (std::memcmp(packet.header.magic, "SVCP", 4) != 0 ||
        packet.header.version != 1) {
        throw std::runtime_error("unsupported SHIFT Vulkan constant packet");
    }
    if (packet.header.max_registers != 256 || packet.header.register_bytes != 16) {
        throw std::runtime_error("constant packet ABI mismatch");
    }

    const size_t bank_bytes = 256u * 16u;
    if (data.size() != sizeof(PacketHeader) + bank_bytes * 2u) {
        throw std::runtime_error("constant packet size mismatch");
    }
    packet.vertex.resize(256u * 4u);
    packet.pixel.resize(256u * 4u);
    const uint8_t* body = data.data() + sizeof(PacketHeader);
    std::memcpy(packet.vertex.data(), body, bank_bytes);
    std::memcpy(packet.pixel.data(), body + bank_bytes, bank_bytes);
    return packet;
}

void create_buffer(
    Context& ctx,
    VkDeviceSize size,
    VkBufferUsageFlags usage,
    Buffer& out) {

    VkBufferCreateInfo info{};
    info.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
    info.size = size;
    info.usage = usage;
    check(vkCreateBuffer(ctx.device, &info, nullptr, &out.handle), "vkCreateBuffer failed");

    VkMemoryRequirements requirements{};
    vkGetBufferMemoryRequirements(ctx.device, out.handle, &requirements);

    VkMemoryAllocateInfo allocation{};
    allocation.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    allocation.allocationSize = requirements.size;
    allocation.memoryTypeIndex = memory_type(
        ctx.physical,
        requirements.memoryTypeBits,
        VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
    check(vkAllocateMemory(ctx.device, &allocation, nullptr, &out.memory),
          "vkAllocateMemory failed");
    check(vkBindBufferMemory(ctx.device, out.handle, out.memory, 0),
          "vkBindBufferMemory failed");
}

void create_image(Context& ctx, Image& out) {
    constexpr uint32_t width = 256;
    constexpr uint32_t height = 256;

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
    info.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    check(vkCreateImage(ctx.device, &info, nullptr, &out.handle), "vkCreateImage failed");

    VkMemoryRequirements requirements{};
    vkGetImageMemoryRequirements(ctx.device, out.handle, &requirements);
    VkMemoryAllocateInfo allocation{};
    allocation.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    allocation.allocationSize = requirements.size;
    allocation.memoryTypeIndex = memory_type(
        ctx.physical, requirements.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    check(vkAllocateMemory(ctx.device, &allocation, nullptr, &out.memory),
          "vkAllocateMemory(image) failed");
    check(vkBindImageMemory(ctx.device, out.handle, out.memory, 0),
          "vkBindImageMemory failed");

    VkImageViewCreateInfo view{};
    view.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
    view.image = out.handle;
    view.viewType = VK_IMAGE_VIEW_TYPE_2D;
    view.format = VK_FORMAT_R8G8B8A8_UNORM;
    view.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    view.subresourceRange.levelCount = 1;
    view.subresourceRange.layerCount = 1;
    check(vkCreateImageView(ctx.device, &view, nullptr, &out.view),
          "vkCreateImageView failed");
}

std::vector<uint32_t> read_spirv(const std::string& path) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file) throw std::runtime_error("cannot open SPIR-V: " + path);
    const std::streamsize size = file.tellg();
    if (size <= 0 || size % 4 != 0) throw std::runtime_error("invalid SPIR-V");
    file.seekg(0);
    std::vector<uint32_t> code(static_cast<size_t>(size) / 4);
    file.read(reinterpret_cast<char*>(code.data()), size);
    if (!file) throw std::runtime_error("failed reading SPIR-V");
    return code;
}

VkShaderModule make_shader(Context& ctx, const std::string& path) {
    const auto code = read_spirv(path);
    VkShaderModuleCreateInfo info{};
    info.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
    info.codeSize = code.size() * sizeof(uint32_t);
    info.pCode = code.data();
    VkShaderModule module = VK_NULL_HANDLE;
    check(vkCreateShaderModule(ctx.device, &info, nullptr, &module),
          "vkCreateShaderModule failed");
    return module;
}

void write_ppm(const std::string& path, const std::vector<uint8_t>& rgba) {
    constexpr uint32_t width = 256;
    constexpr uint32_t height = 256;
    if (rgba.size() != static_cast<size_t>(width) * height * 4) {
        throw std::runtime_error("unexpected image size");
    }
    std::ofstream out(path, std::ios::binary);
    if (!out) throw std::runtime_error("cannot open output PPM");
    out << "P6\n256 256\n255\n";
    for (size_t i = 0; i < rgba.size(); i += 4) {
        out.put(static_cast<char>(rgba[i]));
        out.put(static_cast<char>(rgba[i + 1]));
        out.put(static_cast<char>(rgba[i + 2]));
    }
}

}  // namespace

int main(int argc, char** argv) {
    const std::string packet_path = argc >= 2 ? argv[1] : "shift_vulkan_constants.svcp";
    const std::string output = argc >= 3 ? argv[2] : "shift_vulkan_constants.ppm";
    const std::string shader_dir = argc >= 4 ? argv[3] : "shaders";

    Context ctx{};
    Buffer vertex_constants{};
    Buffer pixel_constants{};
    Buffer staging{};
    Image color{};
    VkShaderModule vert = VK_NULL_HANDLE;
    VkShaderModule frag = VK_NULL_HANDLE;
    VkDescriptorSetLayout set_layout = VK_NULL_HANDLE;
    VkDescriptorPool descriptor_pool = VK_NULL_HANDLE;
    VkDescriptorSet descriptor_set = VK_NULL_HANDLE;
    VkPipelineLayout pipeline_layout = VK_NULL_HANDLE;
    VkPipeline pipeline = VK_NULL_HANDLE;
    VkRenderPass render_pass = VK_NULL_HANDLE;
    VkFramebuffer framebuffer = VK_NULL_HANDLE;
    VkCommandBuffer command = VK_NULL_HANDLE;

    try {
        const ConstantPacket packet = parse_packet(packet_path);
        ctx = create_context();
        create_buffer(ctx, 4096, VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT, vertex_constants);
        create_buffer(ctx, 4096, VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT, pixel_constants);
        create_image(ctx, color);

        void* mapped = nullptr;
        check(vkMapMemory(ctx.device, vertex_constants.memory, 0, 4096, 0, &mapped),
              "vkMapMemory(vertex constants) failed");
        std::memcpy(mapped, packet.vertex.data(), 4096);
        vkUnmapMemory(ctx.device);
        check(vkMapMemory(ctx.device, pixel_constants.memory, 0, 4096, 0, &mapped),
              "vkMapMemory(pixel constants) failed");
        std::memcpy(mapped, packet.pixel.data(), 4096);
        vkUnmapMemory(ctx.device, pixel_constants.memory);

        VkDescriptorSetLayoutBinding bindings[2]{};
        bindings[0].binding = 14;
        bindings[0].descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
        bindings[0].descriptorCount = 1;
        bindings[0].stageFlags = VK_SHADER_STAGE_VERTEX_BIT;
        bindings[1].binding = 15;
        bindings[1].descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
        bindings[1].descriptorCount = 1;
        bindings[1].stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT;

        VkDescriptorSetLayoutCreateInfo set_info{};
        set_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
        set_info.bindingCount = 2;
        set_info.pBindings = bindings;
        check(vkCreateDescriptorSetLayout(ctx.device, &set_info, nullptr, &set_layout),
              "vkCreateDescriptorSetLayout failed");

        VkDescriptorPoolSize pool_sizes[1]{};
        pool_sizes[0].type = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
        pool_sizes[0].descriptorCount = 2;
        VkDescriptorPoolCreateInfo pool_info{};
        pool_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;
        pool_info.maxSets = 1;
        pool_info.poolSizeCount = 1;
        pool_info.pPoolSizes = pool_sizes;
        check(vkCreateDescriptorPool(ctx.device, &pool_info, nullptr, &descriptor_pool),
              "vkCreateDescriptorPool failed");

        VkDescriptorSetAllocateInfo set_alloc{};
        set_alloc.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
        set_alloc.descriptorPool = descriptor_pool;
        set_alloc.descriptorSetCount = 1;
        set_alloc.pSetLayouts = &set_layout;
        check(vkAllocateDescriptorSets(ctx.device, &set_alloc, &descriptor_set),
              "vkAllocateDescriptorSets failed");

        VkDescriptorBufferInfo vertex_info{vertex_constants.handle, 0, 4096};
        VkDescriptorBufferInfo pixel_info{pixel_constants.handle, 0, 4096};
        VkWriteDescriptorSet writes[2]{};
        writes[0].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
        writes[0].dstSet = descriptor_set;
        writes[0].dstBinding = 14;
        writes[0].descriptorCount = 1;
        writes[0].descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
        writes[0].pBufferInfo = &vertex_info;
        writes[1].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
        writes[1].dstSet = descriptor_set;
        writes[1].dstBinding = 15;
        writes[1].descriptorCount = 1;
        writes[1].descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
        writes[1].pBufferInfo = &pixel_info;
        vkUpdateDescriptorSets(ctx.device, 2, writes, 0, nullptr);

        vert = make_shader(ctx, shader_dir + "/constants.vert.spv");
        frag = make_shader(ctx, shader_dir + "/constants.frag.spv");

        VkAttachmentDescription attachment{};
        attachment.format = VK_FORMAT_R8G8B8A8_UNORM;
        attachment.samples = VK_SAMPLE_COUNT_1_BIT;
        attachment.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
        attachment.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
        attachment.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        attachment.finalLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;

        VkAttachmentReference color_ref{};
        color_ref.attachment = 0;
        color_ref.layout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;

        VkSubpassDescription subpass{};
        subpass.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
        subpass.colorAttachmentCount = 1;
        subpass.pColorAttachments = &color_ref;

        VkSubpassDependency dependencies[2]{};
        dependencies[0].srcSubpass = VK_SUBPASS_EXTERNAL;
        dependencies[0].dstSubpass = 0;
        dependencies[0].srcStageMask = VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT;
        dependencies[0].dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
        dependencies[0].dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
        dependencies[1].srcSubpass = 0;
        dependencies[1].dstSubpass = VK_SUBPASS_EXTERNAL;
        dependencies[1].srcStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
        dependencies[1].srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
        dependencies[1].dstStageMask = VK_PIPELINE_STAGE_TRANSFER_BIT;
        dependencies[1].dstAccessMask = VK_ACCESS_TRANSFER_READ_BIT;

        VkRenderPassCreateInfo render_info{};
        render_info.sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
        render_info.attachmentCount = 1;
        render_info.pAttachments = &attachment;
        render_info.subpassCount = 1;
        render_info.pSubpasses = &subpass;
        render_info.dependencyCount = 2;
        render_info.pDependencies = dependencies;
        check(vkCreateRenderPass(ctx.device, &render_info, nullptr, &render_pass),
              "vkCreateRenderPass failed");

        VkFramebufferCreateInfo framebuffer_info{};
        framebuffer_info.sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
        framebuffer_info.renderPass = render_pass;
        framebuffer_info.attachmentCount = 1;
        framebuffer_info.pAttachments = &color.view;
        framebuffer_info.width = 256;
        framebuffer_info.height = 256;
        framebuffer_info.layers = 1;
        check(vkCreateFramebuffer(ctx.device, &framebuffer_info, nullptr, &framebuffer),
              "vkCreateFramebuffer failed");

        VkPipelineShaderStageCreateInfo stages[2]{};
        stages[0].sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module = vert;
        stages[0].pName = "main";
        stages[1].sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module = frag;
        stages[1].pName = "main";

        VkPipelineVertexInputStateCreateInfo vertex_input{};
        vertex_input.sType = VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO;
        VkPipelineInputAssemblyStateCreateInfo assembly{};
        assembly.sType = VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO;
        assembly.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;

        VkViewport viewport{0,0,256,256,0,1};
        VkRect2D scissor{{0,0},{256,256}};
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

        VkPipelineMultisampleStateCreateInfo ms{};
        ms.sType = VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO;
        ms.rasterizationSamples = VK_SAMPLE_COUNT_1_BIT;

        VkPipelineColorBlendAttachmentState blend_attachment{};
        blend_attachment.blendEnable = VK_FALSE;
        blend_attachment.colorWriteMask =
            VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
            VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT;
        VkPipelineColorBlendStateCreateInfo blend{};
        blend.sType = VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO;
        blend.attachmentCount = 1;
        blend.pAttachments = &blend_attachment;

        VkPipelineLayoutCreateInfo layout{};
        layout.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
        layout.setLayoutCount = 1;
        layout.pSetLayouts = &set_layout;
        check(vkCreatePipelineLayout(ctx.device, &layout, nullptr, &pipeline_layout),
              "vkCreatePipelineLayout failed");

        VkGraphicsPipelineCreateInfo pipeline_info{};
        pipeline_info.sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO;
        pipeline_info.stageCount = 2;
        pipeline_info.pStages = stages;
        pipeline_info.pVertexInputState = &vertex_input;
        pipeline_info.pInputAssemblyState = &assembly;
        pipeline_info.pViewportState = &viewport_state;
        pipeline_info.pRasterizationState = &raster;
        pipeline_info.pMultisampleState = &ms;
        pipeline_info.pColorBlendState = &blend;
        pipeline_info.layout = pipeline_layout;
        pipeline_info.renderPass = render_pass;
        check(vkCreateGraphicsPipelines(
            ctx.device, VK_NULL_HANDLE, 1, &pipeline_info, nullptr, &pipeline),
            "vkCreateGraphicsPipelines failed");

        create_buffer(
            ctx,
            256u * 256u * 4u,
            VK_BUFFER_USAGE_TRANSFER_DST_BIT,
            staging);

        VkCommandBufferAllocateInfo cmd_alloc{};
        cmd_alloc.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
        cmd_alloc.commandPool = ctx.command_pool;
        cmd_alloc.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        cmd_alloc.commandBufferCount = 1;
        check(vkAllocateCommandBuffers(ctx.device, &cmd_alloc, &command),
              "vkAllocateCommandBuffers failed");

        VkCommandBufferBeginInfo begin{};
        begin.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
        check(vkBeginCommandBuffer(command, &begin), "vkBeginCommandBuffer failed");

        VkRenderPassBeginInfo pass{};
        pass.sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
        pass.renderPass = render_pass;
        pass.framebuffer = framebuffer;
        pass.renderArea.extent = {256, 256};
        VkClearValue clear{};
        clear.color.float32[0] = 0.02f;
        clear.color.float32[1] = 0.02f;
        clear.color.float32[2] = 0.02f;
        clear.color.float32[3] = 1.0f;
        pass.clearValueCount = 1;
        pass.pClearValues = &clear;

        vkCmdBeginRenderPass(command, &pass, VK_SUBPASS_CONTENTS_INLINE);
        vkCmdBindPipeline(command, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline);
        vkCmdBindDescriptorSets(
            command, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline_layout,
            0, 1, &descriptor_set, 0, nullptr);
        vkCmdDraw(command, 3, 1, 0, 0);
        vkCmdEndRenderPass(command);

        VkBufferImageCopy copy{};
        copy.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        copy.imageSubresource.layerCount = 1;
        copy.imageExtent = {256, 256, 1};
        vkCmdCopyImageToBuffer(
            command, color.handle, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
            staging.handle, 1, &copy);

        check(vkEndCommandBuffer(command), "vkEndCommandBuffer failed");

        VkSubmitInfo submit{};
        submit.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
        submit.commandBufferCount = 1;
        submit.pCommandBuffers = &command;
        check(vkQueueSubmit(ctx.queue, 1, &submit, VK_NULL_HANDLE),
              "vkQueueSubmit failed");
        check(vkQueueWaitIdle(ctx.queue), "vkQueueWaitIdle failed");

        std::vector<uint8_t> rgba(256u * 256u * 4u);
        check(vkMapMemory(ctx.device, staging.memory, 0, rgba.size(), 0, &mapped),
              "vkMapMemory(staging) failed");
        std::memcpy(rgba.data(), mapped, rgba.size());
        vkUnmapMemory(ctx.device);
        write_ppm(output, rgba);

        VkPhysicalDeviceProperties props{};
        vkGetPhysicalDeviceProperties(ctx.physical, &props);
        std::cout << "{\n";
        std::cout << "  \"format\": \"SHIFT.VulkanConstantUpload/1\",\n";
        std::cout << "  \"device\": \"" << props.deviceName << "\",\n";
        std::cout << "  \"vertex_binding\": 14,\n";
        std::cout << "  \"pixel_binding\": 15,\n";
        std::cout << "  \"output\": \"" << output << "\"\n";
        std::cout << "}\n";

        if (command != VK_NULL_HANDLE) vkFreeCommandBuffers(ctx.device, ctx.command_pool, 1, &command);
        if (staging.handle) vkDestroyBuffer(ctx.device, staging.handle, nullptr);
        if (staging.memory) vkFreeMemory(ctx.device, staging.memory, nullptr);
        if (pipeline) vkDestroyPipeline(ctx.device, pipeline, nullptr);
        if (pipeline_layout) vkDestroyPipelineLayout(ctx.device, pipeline_layout, nullptr);
        if (descriptor_pool) vkDestroyDescriptorPool(ctx.device, descriptor_pool, nullptr);
        if (set_layout) vkDestroyDescriptorSetLayout(ctx.device, set_layout, nullptr);
        if (framebuffer) vkDestroyFramebuffer(ctx.device, framebuffer, nullptr);
        if (render_pass) vkDestroyRenderPass(ctx.device, render_pass, nullptr);
        if (vert) vkDestroyShaderModule(ctx.device, vert, nullptr);
        if (frag) vkDestroyShaderModule(ctx.device, frag, nullptr);
        if (color.view) vkDestroyImageView(ctx.device, color.view, nullptr);
        if (color.handle) vkDestroyImage(ctx.device, color.handle, nullptr);
        if (color.memory) vkFreeMemory(ctx.device, color.memory, nullptr);
        if (vertex_constants.handle) vkDestroyBuffer(ctx.device, vertex_constants.handle, nullptr);
        if (vertex_constants.memory) vkFreeMemory(ctx.device, vertex_constants.memory, nullptr);
        if (pixel_constants.handle) vkDestroyBuffer(ctx.device, pixel_constants.handle, nullptr);
        if (pixel_constants.memory) vkFreeMemory(ctx.device, pixel_constants.memory, nullptr);
        destroy(ctx);
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "shift_vulkan_constant_upload: " << error.what() << "\n";
        if (ctx.device != VK_NULL_HANDLE) {
            if (pipeline) vkDestroyPipeline(ctx.device, pipeline, nullptr);
            if (pipeline_layout) vkDestroyPipelineLayout(ctx.device, pipeline_layout, nullptr);
            if (descriptor_pool) vkDestroyDescriptorPool(ctx.device, descriptor_pool, nullptr);
            if (set_layout) vkDestroyDescriptorSetLayout(ctx.device, set_layout, nullptr);
            if (framebuffer) vkDestroyFramebuffer(ctx.device, framebuffer, nullptr);
            if (render_pass) vkDestroyRenderPass(ctx.device, render_pass, nullptr);
            if (vert) vkDestroyShaderModule(ctx.device, vert, nullptr);
            if (frag) vkDestroyShaderModule(ctx.device, frag, nullptr);
            if (color.view) vkDestroyImageView(ctx.device, color.view, nullptr);
            if (color.handle) vkDestroyImage(ctx.device, color.handle, nullptr);
            if (color.memory) vkFreeMemory(ctx.device, color.memory, nullptr);
            if (staging.handle) vkDestroyBuffer(ctx.device, staging.handle, nullptr);
            if (staging.memory) vkFreeMemory(ctx.device, staging.memory, nullptr);
            if (vertex_constants.handle) vkDestroyBuffer(ctx.device, vertex_constants.handle, nullptr);
            if (vertex_constants.memory) vkFreeMemory(ctx.device, vertex_constants.memory, nullptr);
            if (pixel_constants.handle) vkDestroyBuffer(ctx.device, pixel_constants.handle, nullptr);
            if (pixel_constants.memory) vkFreeMemory(ctx.device, pixel_constants.memory, nullptr);
        }
        destroy(ctx);
        return EXIT_FAILURE;
    }
}
