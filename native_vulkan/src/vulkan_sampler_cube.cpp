#include <vulkan/vulkan.h>

#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#pragma pack(push, 1)
struct Header {
    char magic[4];
    uint32_t version;
    uint32_t register_index;
    uint32_t width;
    uint32_t height;
    uint32_t face_count;
    uint32_t face_bytes;
};
#pragma pack(pop)

static_assert(sizeof(Header) == 28, "unexpected cube packet header size");

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

struct ResourceBuffer {
    VkBuffer buffer = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
};

struct ResourceImage {
    VkImage image = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
    VkImageView view = VK_NULL_HANDLE;
};

struct Packet {
    Header header{};
    std::vector<uint8_t> pixels;
};

void destroy(Context& context) {
    if (context.device != VK_NULL_HANDLE) {
        vkDeviceWaitIdle(context.device);
        if (context.command_pool) {
            vkDestroyCommandPool(context.device, context.command_pool, nullptr);
        }
        vkDestroyDevice(context.device, nullptr);
    }
    if (context.instance) vkDestroyInstance(context.instance, nullptr);
}

Context create_context() {
    Context context{};

    VkApplicationInfo app{};
    app.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
    app.pApplicationName = "SHIFT Vulkan SamplerCube";
    app.applicationVersion = 1;
    app.pEngineName = "SHIFT";
    app.engineVersion = 1;
    app.apiVersion = VK_API_VERSION_1_0;

    VkInstanceCreateInfo instance{};
    instance.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    instance.pApplicationInfo = &app;
    check(vkCreateInstance(&instance, nullptr, &context.instance),
          "vkCreateInstance failed");

    uint32_t count = 0;
    check(vkEnumeratePhysicalDevices(context.instance, &count, nullptr),
          "vkEnumeratePhysicalDevices(count) failed");
    if (count == 0) throw std::runtime_error("no Vulkan physical devices");

    std::vector<VkPhysicalDevice> devices(count);
    check(vkEnumeratePhysicalDevices(context.instance, &count, devices.data()),
          "vkEnumeratePhysicalDevices(data) failed");

    for (VkPhysicalDevice candidate : devices) {
        uint32_t family_count = 0;
        vkGetPhysicalDeviceQueueFamilyProperties(candidate, &family_count, nullptr);
        std::vector<VkQueueFamilyProperties> families(family_count);
        vkGetPhysicalDeviceQueueFamilyProperties(candidate, &family_count, families.data());
        for (uint32_t index = 0; index < family_count; ++index) {
            if (families[index].queueFlags & VK_QUEUE_GRAPHICS_BIT) {
                context.physical = candidate;
                context.queue_family = index;
                break;
            }
        }
        if (context.physical) break;
    }
    if (!context.physical) throw std::runtime_error("no graphics queue");

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
    check(vkCreateCommandPool(context.device, &pool, nullptr, &context.command_pool),
          "vkCreateCommandPool failed");
    return context;
}

std::vector<uint8_t> read_file(const std::string& path) {
    std::ifstream input(path, std::ios::binary | std::ios::ate);
    if (!input) throw std::runtime_error("cannot open cube packet");
    const std::streamsize size = input.tellg();
    if (size <= 0) throw std::runtime_error("cube packet is empty");
    input.seekg(0);
    std::vector<uint8_t> data(static_cast<size_t>(size));
    input.read(reinterpret_cast<char*>(data.data()), size);
    if (!input) throw std::runtime_error("cannot read cube packet");
    return data;
}

Packet parse_packet(const std::string& path) {
    const auto data = read_file(path);
    if (data.size() < sizeof(Header)) throw std::runtime_error("cube packet truncated");

    Packet packet{};
    std::memcpy(&packet.header, data.data(), sizeof(packet.header));
    if (std::memcmp(packet.header.magic, "SVCP", 4) != 0 ||
        packet.header.version != 1 ||
        packet.header.register_index != 3 ||
        packet.header.face_count != 6) {
        throw std::runtime_error("invalid SHIFT Vulkan cube packet");
    }

    const uint64_t expected_face_bytes =
        static_cast<uint64_t>(packet.header.width) *
        static_cast<uint64_t>(packet.header.height) * 4u;
    const uint64_t expected_total =
        expected_face_bytes * 6u;
    if (packet.header.width == 0 || packet.header.height == 0 ||
        expected_face_bytes > UINT32_MAX ||
        packet.header.face_bytes != static_cast<uint32_t>(expected_face_bytes) ||
        expected_total > SIZE_MAX ||
        data.size() != sizeof(Header) + static_cast<size_t>(expected_total)) {
        throw std::runtime_error("cube packet dimensions or payload size invalid");
    }

    packet.pixels.assign(
        data.begin() + sizeof(Header),
        data.end());
    return packet;
}

void create_buffer(
    Context& context,
    VkDeviceSize size,
    VkBufferUsageFlags usage,
    VkMemoryPropertyFlags properties,
    ResourceBuffer& out) {

    VkBufferCreateInfo buffer{};
    buffer.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
    buffer.size = size;
    buffer.usage = usage;
    check(vkCreateBuffer(context.device, &buffer, nullptr, &out.buffer),
          "vkCreateBuffer failed");

    VkMemoryRequirements requirements{};
    vkGetBufferMemoryRequirements(context.device, out.buffer, &requirements);

    VkMemoryAllocateInfo allocation{};
    allocation.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    allocation.allocationSize = requirements.size;
    allocation.memoryTypeIndex = memory_type(
        context.physical, requirements.memoryTypeBits, properties);
    check(vkAllocateMemory(context.device, &allocation, nullptr, &out.memory),
          "vkAllocateMemory failed");
    check(vkBindBufferMemory(context.device, out.buffer, out.memory, 0),
          "vkBindBufferMemory failed");
}

void create_cube(
    Context& context,
    uint32_t width,
    uint32_t height,
    ResourceImage& out) {

    VkImageCreateInfo image{};
    image.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
    image.flags = VK_IMAGE_CREATE_CUBE_COMPATIBLE_BIT;
    image.imageType = VK_IMAGE_TYPE_2D;
    image.format = VK_FORMAT_R8G8B8A8_UNORM;
    image.extent = {width, height, 1};
    image.mipLevels = 1;
    image.arrayLayers = 6;
    image.samples = VK_SAMPLE_COUNT_1_BIT;
    image.tiling = VK_IMAGE_TILING_OPTIMAL;
    image.usage = VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_SAMPLED_BIT;
    image.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    check(vkCreateImage(context.device, &image, nullptr, &out.image),
          "vkCreateImage cube failed");

    VkMemoryRequirements requirements{};
    vkGetImageMemoryRequirements(context.device, out.image, &requirements);
    VkMemoryAllocateInfo allocation{};
    allocation.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    allocation.allocationSize = requirements.size;
    allocation.memoryTypeIndex = memory_type(
        context.physical, requirements.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    check(vkAllocateMemory(context.device, &allocation, nullptr, &out.memory),
          "vkAllocateMemory cube failed");
    check(vkBindImageMemory(context.device, out.image, out.memory, 0),
          "vkBindImageMemory cube failed");

    VkImageViewCreateInfo view{};
    view.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
    view.image = out.image;
    view.viewType = VK_IMAGE_VIEW_TYPE_CUBE;
    view.format = VK_FORMAT_R8G8B8A8_UNORM;
    view.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    view.subresourceRange.levelCount = 1;
    view.subresourceRange.layerCount = 6;
    check(vkCreateImageView(context.device, &view, nullptr, &out.view),
          "vkCreateImageView cube failed");
}

VkShaderModule make_shader(
    Context& context,
    const std::string& path) {

    const auto bytes = read_file(path);
    if (bytes.size() % 4 != 0) throw std::runtime_error("SPIR-V size is not aligned");
    VkShaderModuleCreateInfo info{};
    info.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
    info.codeSize = bytes.size();
    info.pCode = reinterpret_cast<const uint32_t*>(bytes.data());
    VkShaderModule module = VK_NULL_HANDLE;
    check(vkCreateShaderModule(context.device, &info, nullptr, &module),
          "vkCreateShaderModule failed");
    return module;
}

void transition(
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
    barrier.subresourceRange.layerCount = 6;

    vkCmdPipelineBarrier(
        command,
        src_stage,
        dst_stage,
        0,
        0, nullptr,
        0, nullptr,
        1, &barrier);
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

}  // namespace

int main(int argc, char** argv) {
    const std::string packet_path = argc >= 2 ? argv[1] : "shift_vulkan_cube.svcp";
    const std::string output = argc >= 3 ? argv[2] : "shift_vulkan_cube.ppm";
    const std::string shader_dir = argc >= 4 ? argv[3] : "shaders";

    constexpr uint32_t width_out = 256;
    constexpr uint32_t height_out = 256;

    Context context{};
    Packet packet{};
    ResourceImage cube{};
    ResourceImage color{};
    ResourceBuffer cube_staging{};
    ResourceBuffer readback{};
    VkDescriptorSetLayout empty_layout = VK_NULL_HANDLE;
    VkDescriptorSetLayout cube_layout = VK_NULL_HANDLE;
    VkDescriptorPool descriptor_pool = VK_NULL_HANDLE;
    VkDescriptorSet descriptor_set = VK_NULL_HANDLE;
    VkPipelineLayout pipeline_layout = VK_NULL_HANDLE;
    VkRenderPass render_pass = VK_NULL_HANDLE;
    VkFramebuffer framebuffer = VK_NULL_HANDLE;
    VkPipeline pipeline = VK_NULL_HANDLE;
    VkShaderModule vertex_shader = VK_NULL_HANDLE;
    VkShaderModule fragment_shader = VK_NULL_HANDLE;
    VkCommandBuffer command = VK_NULL_HANDLE;

    try {
        packet = parse_packet(packet_path);
        context = create_context();

        const size_t face_bytes = packet.header.face_bytes;
        create_buffer(
            context,
            static_cast<VkDeviceSize>(face_bytes) * 6u,
            VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
            cube_staging);
        void* mapped = nullptr;
        check(vkMapMemory(
            context.device, cube_staging.memory, 0,
            static_cast<VkDeviceSize>(face_bytes) * 6u, 0, &mapped),
            "vkMapMemory cube staging failed");
        std::memcpy(mapped, packet.pixels.data(), packet.pixels.size());
        vkUnmapMemory(context.device, cube_staging.memory);

        create_cube(context, packet.header.width, packet.header.height, cube);

        VkImageCreateInfo color_info{};
        color_info.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
        color_info.imageType = VK_IMAGE_TYPE_2D;
        color_info.format = VK_FORMAT_R8G8B8A8_UNORM;
        color_info.extent = {width_out,height_out,1};
        color_info.mipLevels = 1;
        color_info.arrayLayers = 1;
        color_info.samples = VK_SAMPLE_COUNT_1_BIT;
        color_info.tiling = VK_IMAGE_TILING_OPTIMAL;
        color_info.usage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
        check(vkCreateImage(context.device,&color_info,nullptr,&color.image),"vkCreateImage color failed");
        VkMemoryRequirements color_req{};
        vkGetImageMemoryRequirements(context.device,color.image,&color_req);
        VkMemoryAllocateInfo color_alloc{};
        color_alloc.sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
        color_alloc.allocationSize=color_req.size;
        color_alloc.memoryTypeIndex=memory_type(context.physical,color_req.memoryTypeBits,VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        check(vkAllocateMemory(context.device,&color_alloc,nullptr,&color.memory),"vkAllocateMemory color failed");
        check(vkBindImageMemory(context.device,color.image,color.memory,0),"vkBindImageMemory color failed");
        VkImageViewCreateInfo color_view{};
        color_view.sType=VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
        color_view.image=color.image;
        color_view.viewType=VK_IMAGE_VIEW_TYPE_2D;
        color_view.format=VK_FORMAT_R8G8B8A8_UNORM;
        color_view.subresourceRange.aspectMask=VK_IMAGE_ASPECT_COLOR_BIT;
        color_view.subresourceRange.levelCount=1;
        color_view.subresourceRange.layerCount=1;
        check(vkCreateImageView(context.device,&color_view,nullptr,&color.view),"vkCreateImageView color failed");

        VkDescriptorSetLayoutCreateInfo empty_info{};
        empty_info.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
        check(vkCreateDescriptorSetLayout(context.device,&empty_info,nullptr,&empty_layout),
              "vkCreateDescriptorSetLayout empty failed");

        VkDescriptorSetLayoutBinding cube_binding{};
        cube_binding.binding=3;
        cube_binding.descriptorType=VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
        cube_binding.descriptorCount=1;
        cube_binding.stageFlags=VK_SHADER_STAGE_FRAGMENT_BIT;
        VkDescriptorSetLayoutCreateInfo cube_info{};
        cube_info.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
        cube_info.bindingCount=1;
        cube_info.pBindings=&cube_binding;
        check(vkCreateDescriptorSetLayout(context.device,&cube_info,nullptr,&cube_layout),
              "vkCreateDescriptorSetLayout cube failed");

        VkDescriptorPoolSize pool_size{};
        pool_size.type=VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
        pool_size.descriptorCount=1;
        VkDescriptorPoolCreateInfo pool{};
        pool.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;
        pool.maxSets=1;
        pool.poolSizeCount=1;
        pool.pPoolSizes=&pool_size;
        check(vkCreateDescriptorPool(context.device,&pool,nullptr,&descriptor_pool),
              "vkCreateDescriptorPool failed");

        VkDescriptorSetLayout sets[2]={empty_layout,cube_layout};
        VkDescriptorSetAllocateInfo allocate{};
        allocate.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
        allocate.descriptorPool=descriptor_pool;
        allocate.descriptorSetCount=1;
        allocate.pSetLayouts=&sets[1];
        check(vkAllocateDescriptorSets(context.device,&allocate,&descriptor_set),
              "vkAllocateDescriptorSets failed");

        VkSamplerCreateInfo sampler{};
        sampler.sType=VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO;
        sampler.magFilter=VK_FILTER_LINEAR;
        sampler.minFilter=VK_FILTER_LINEAR;
        sampler.mipmapMode=VK_SAMPLER_MIPMAP_MODE_NEAREST;
        sampler.addressModeU=VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
        sampler.addressModeV=VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
        sampler.addressModeW=VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
        sampler.maxLod=1.0f;
        VkSampler cube_sampler=VK_NULL_HANDLE;
        check(vkCreateSampler(context.device,&sampler,nullptr,&cube_sampler),
              "vkCreateSampler failed");

        VkDescriptorImageInfo cube_image_info{};
        cube_image_info.sampler=cube_sampler;
        cube_image_info.imageView=cube.view;
        cube_image_info.imageLayout=VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
        VkWriteDescriptorSet write{};
        write.sType=VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
        write.dstSet=descriptor_set;
        write.dstBinding=3;
        write.descriptorCount=1;
        write.descriptorType=VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
        write.pImageInfo=&cube_image_info;
        vkUpdateDescriptorSets(context.device,1,&write,0,nullptr);

        vertex_shader=make_shader(context,shader_dir+"/cube.vert.spv");
        fragment_shader=make_shader(context,shader_dir+"/cube.frag.spv");

        VkAttachmentDescription attachment{};
        attachment.format=VK_FORMAT_R8G8B8A8_UNORM;
        attachment.samples=VK_SAMPLE_COUNT_1_BIT;
        attachment.loadOp=VK_ATTACHMENT_LOAD_OP_CLEAR;
        attachment.storeOp=VK_ATTACHMENT_STORE_OP_STORE;
        attachment.initialLayout=VK_IMAGE_LAYOUT_UNDEFINED;
        attachment.finalLayout=VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
        VkAttachmentReference attachment_ref{};
        attachment_ref.attachment=0;
        attachment_ref.layout=VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
        VkSubpassDescription subpass{};
        subpass.pipelineBindPoint=VK_PIPELINE_BIND_POINT_GRAPHICS;
        subpass.colorAttachmentCount=1;
        subpass.pColorAttachments=&attachment_ref;
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
        VkRenderPassCreateInfo rp{};
        rp.sType=VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
        rp.attachmentCount=1;
        rp.pAttachments=&attachment;
        rp.subpassCount=1;
        rp.pSubpasses=&subpass;
        rp.dependencyCount=2;
        rp.pDependencies=deps;
        check(vkCreateRenderPass(context.device,&rp,nullptr,&render_pass),"vkCreateRenderPass failed");
        VkFramebufferCreateInfo fb{};
        fb.sType=VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
        fb.renderPass=render_pass;
        fb.attachmentCount=1;
        fb.pAttachments=&color.view;
        fb.width=256;
        fb.height=256;
        fb.layers=1;
        check(vkCreateFramebuffer(context.device,&fb,nullptr,&framebuffer),"vkCreateFramebuffer failed");

        VkPipelineShaderStageCreateInfo stages[2]{};
        stages[0].sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        stages[0].stage=VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module=vertex_shader;
        stages[0].pName="main";
        stages[1].sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        stages[1].stage=VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module=fragment_shader;
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
        vp.viewportCount=1; vp.pViewports=&viewport;
        vp.scissorCount=1; vp.pScissors=&scissor;
        VkPipelineRasterizationStateCreateInfo raster{};
        raster.sType=VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO;
        raster.polygonMode=VK_POLYGON_MODE_FILL;
        raster.cullMode=VK_CULL_MODE_NONE;
        raster.frontFace=VK_FRONT_FACE_COUNTER_CLOCKWISE;
        raster.lineWidth=1.0f;
        VkPipelineMultisampleStateCreateInfo ms{};
        ms.sType=VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO;
        ms.rasterizationSamples=VK_SAMPLE_COUNT_1_BIT;
        VkPipelineColorBlendAttachmentState color_blend{};
        color_blend.blendEnable=VK_FALSE;
        color_blend.colorWriteMask=VK_COLOR_COMPONENT_R_BIT|VK_COLOR_COMPONENT_G_BIT|
                                   VK_COLOR_COMPONENT_B_BIT|VK_COLOR_COMPONENT_A_BIT;
        VkPipelineColorBlendStateCreateInfo blend{};
        blend.sType=VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO;
        blend.attachmentCount=1; blend.pAttachments=&color_blend;

        VkPipelineLayoutCreateInfo layout{};
        layout.sType=VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
        layout.setLayoutCount=2; layout.pSetLayouts=sets;
        check(vkCreatePipelineLayout(context.device,&layout,nullptr,&pipeline_layout),
              "vkCreatePipelineLayout failed");

        VkGraphicsPipelineCreateInfo pipeline_info{};
        pipeline_info.sType=VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO;
        pipeline_info.stageCount=2; pipeline_info.pStages=stages;
        pipeline_info.pVertexInputState=&vi; pipeline_info.pInputAssemblyState=&ia;
        pipeline_info.pViewportState=&vp; pipeline_info.pRasterizationState=&raster;
        pipeline_info.pMultisampleState=&ms; pipeline_info.pColorBlendState=&blend;
        pipeline_info.layout=pipeline_layout; pipeline_info.renderPass=render_pass;
        check(vkCreateGraphicsPipelines(context.device,VK_NULL_HANDLE,1,&pipeline_info,nullptr,&pipeline),
              "vkCreateGraphicsPipelines failed");

        create_buffer(
            context, 256u*256u*4u, VK_BUFFER_USAGE_TRANSFER_DST_BIT,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
            readback);

        VkCommandBufferAllocateInfo command_alloc{};
        command_alloc.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
        command_alloc.commandPool=context.command_pool;
        command_alloc.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        command_alloc.commandBufferCount=1;
        check(vkAllocateCommandBuffers(context.device,&command_alloc,&command),
              "vkAllocateCommandBuffers failed");
        VkCommandBufferBeginInfo begin{};
        begin.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
        check(vkBeginCommandBuffer(command,&begin),"vkBeginCommandBuffer failed");

        transition(
            command,cube.image,VK_IMAGE_LAYOUT_UNDEFINED,VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
            0,VK_ACCESS_TRANSFER_WRITE_BIT,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
            VK_PIPELINE_STAGE_TRANSFER_BIT);
        for (uint32_t face=0; face<6; ++face) {
            VkBufferImageCopy copy{};
            copy.bufferOffset=static_cast<VkDeviceSize>(face)*face_bytes;
            copy.imageSubresource.aspectMask=VK_IMAGE_ASPECT_COLOR_BIT;
            copy.imageSubresource.mipLevel=0;
            copy.imageSubresource.baseArrayLayer=face;
            copy.imageSubresource.layerCount=1;
            copy.imageExtent={packet.header.width,packet.header.height,1};
            vkCmdCopyBufferToImage(
                command,cube_staging.buffer,cube.image,
                VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,1,&copy);
        }
        transition(
            command,cube.image,VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
            VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
            VK_ACCESS_TRANSFER_WRITE_BIT,VK_ACCESS_SHADER_READ_BIT,
            VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT);

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
        pass.clearValueCount=1; pass.pClearValues=&clear;
        vkCmdBeginRenderPass(command,&pass,VK_SUBPASS_CONTENTS_INLINE);
        vkCmdBindPipeline(command,VK_PIPELINE_BIND_POINT_GRAPHICS,pipeline);
        vkCmdBindDescriptorSets(
            command,VK_PIPELINE_BIND_POINT_GRAPHICS,pipeline_layout,
            1,1,&descriptor_set,0,nullptr);
        vkCmdDraw(command,3,1,0,0);
        vkCmdEndRenderPass(command);

        VkBufferImageCopy read{};
        read.imageSubresource.aspectMask=VK_IMAGE_ASPECT_COLOR_BIT;
        read.imageSubresource.layerCount=1;
        read.imageExtent={256,256,1};
        vkCmdCopyImageToBuffer(
            command,color.image,VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
            readback.buffer,1,&read);
        check(vkEndCommandBuffer(command),"vkEndCommandBuffer failed");
        VkSubmitInfo submit{};
        submit.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO;
        submit.commandBufferCount=1;
        submit.pCommandBuffers=&command;
        check(vkQueueSubmit(context.queue,1,&submit,VK_NULL_HANDLE),"vkQueueSubmit failed");
        check(vkQueueWaitIdle(context.queue),"vkQueueWaitIdle failed");

        std::vector<uint8_t> rgba(256u*256u*4u);
        check(vkMapMemory(context.device,readback.memory,0,rgba.size(),0,&mapped),
              "vkMapMemory readback failed");
        std::memcpy(rgba.data(),mapped,rgba.size());
        vkUnmapMemory(context.device,readback.memory);
        write_ppm(output,rgba);

        VkPhysicalDeviceProperties props{};
        vkGetPhysicalDeviceProperties(context.physical,&props);
        std::cout << "{\n";
        std::cout << "  \"format\": \"SHIFT.VulkanSamplerCube/1\",\n";
        std::cout << "  \"device\": \"" << props.deviceName << "\",\n";
        std::cout << "  \"descriptor_set\": 1,\n";
        std::cout << "  \"sampler_register\": 3,\n";
        std::cout << "  \"face_count\": 6,\n";
        std::cout << "  \"output\": \"" << output << "\"\n";
        std::cout << "}\n";

        VkSampler sampler_handle = cube_sampler;
        if (command) vkFreeCommandBuffers(context.device,context.command_pool,1,&command);
        if (sampler_handle) vkDestroySampler(context.device,sampler_handle,nullptr);
        if (readback.buffer) vkDestroyBuffer(context.device,readback.buffer,nullptr);
        if (readback.memory) vkFreeMemory(context.device,readback.memory,nullptr);
        if (pipeline) vkDestroyPipeline(context.device,pipeline,nullptr);
        if (pipeline_layout) vkDestroyPipelineLayout(context.device,pipeline_layout,nullptr);
        if (descriptor_pool) vkDestroyDescriptorPool(context.device,descriptor_pool,nullptr);
        if (cube_layout) vkDestroyDescriptorSetLayout(context.device,cube_layout,nullptr);
        if (empty_layout) vkDestroyDescriptorSetLayout(context.device,empty_layout,nullptr);
        if (framebuffer) vkDestroyFramebuffer(context.device,framebuffer,nullptr);
        if (render_pass) vkDestroyRenderPass(context.device,render_pass,nullptr);
        if (vertex_shader) vkDestroyShaderModule(context.device,vertex_shader,nullptr);
        if (fragment_shader) vkDestroyShaderModule(context.device,fragment_shader,nullptr);
        if (color.view) vkDestroyImageView(context.device,color.view,nullptr);
        if (color.image) vkDestroyImage(context.device,color.image,nullptr);
        if (color.memory) vkFreeMemory(context.device,color.memory,nullptr);
        if (cube.view) vkDestroyImageView(context.device,cube.view,nullptr);
        if (cube.image) vkDestroyImage(context.device,cube.image,nullptr);
        if (cube.memory) vkFreeMemory(context.device,cube.memory,nullptr);
        if (cube_staging.buffer) vkDestroyBuffer(context.device,cube_staging.buffer,nullptr);
        if (cube_staging.memory) vkFreeMemory(context.device,cube_staging.memory,nullptr);
        destroy(context);
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "shift_vulkan_sampler_cube: " << error.what() << "\n";
        destroy(context);
        return EXIT_FAILURE;
    }
}
