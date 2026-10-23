#include "shift_xbox_live_vulkan_renderer.hpp"

#include <algorithm>
#include <array>
#include <cstring>
#include <initializer_list>
#include <sstream>
#include <utility>

namespace shift::xbox {
namespace {

struct BufferResource {
    VkBuffer buffer = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
};

struct ImageResource {
    VkImage image = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
    VkImageView view = VK_NULL_HANDLE;
};

struct DrawResources {
    BufferResource vertices;
    BufferResource indices;
    BufferResource vertex_constants;
    BufferResource pixel_constants;
    BufferResource texture_upload;
    ImageResource texture;
    VkSampler sampler = VK_NULL_HANDLE;
    VkShaderModule vertex_shader = VK_NULL_HANDLE;
    VkShaderModule pixel_shader = VK_NULL_HANDLE;
    VkDescriptorSetLayout descriptor_layouts[2]{};
    VkDescriptorPool descriptor_pool = VK_NULL_HANDLE;
    VkDescriptorSet descriptor_sets[2]{};
    VkPipelineLayout pipeline_layout = VK_NULL_HANDLE;
    VkPipeline pipeline = VK_NULL_HANDLE;
};

struct FrameResources {
    VkDevice device = VK_NULL_HANDLE;
    VkQueue queue = VK_NULL_HANDLE;
    VkRenderPass render_pass = VK_NULL_HANDLE;
    VkFramebuffer framebuffer = VK_NULL_HANDLE;
    VkCommandPool command_pool = VK_NULL_HANDLE;
    std::vector<DrawResources> draws;
    bool submitted = false;

    ~FrameResources() {
        if (submitted) vkQueueWaitIdle(queue);
        for (auto it = draws.rbegin(); it != draws.rend(); ++it) {
            DrawResources& draw = *it;
            if (draw.pipeline) vkDestroyPipeline(device, draw.pipeline, nullptr);
            if (draw.pipeline_layout) vkDestroyPipelineLayout(device, draw.pipeline_layout, nullptr);
            if (draw.descriptor_pool) vkDestroyDescriptorPool(device, draw.descriptor_pool, nullptr);
            for (VkDescriptorSetLayout layout : draw.descriptor_layouts) {
                if (layout) vkDestroyDescriptorSetLayout(device, layout, nullptr);
            }
            if (draw.vertex_shader) vkDestroyShaderModule(device, draw.vertex_shader, nullptr);
            if (draw.pixel_shader) vkDestroyShaderModule(device, draw.pixel_shader, nullptr);
            if (draw.sampler) vkDestroySampler(device, draw.sampler, nullptr);
            destroy_image(draw.texture);
            destroy_buffer(draw.texture_upload);
            destroy_buffer(draw.pixel_constants);
            destroy_buffer(draw.vertex_constants);
            destroy_buffer(draw.indices);
            destroy_buffer(draw.vertices);
        }
        if (framebuffer) vkDestroyFramebuffer(device, framebuffer, nullptr);
        if (render_pass) vkDestroyRenderPass(device, render_pass, nullptr);
        if (command_pool) vkDestroyCommandPool(device, command_pool, nullptr);
    }

    void destroy_buffer(BufferResource& resource) const {
        if (resource.buffer) vkDestroyBuffer(device, resource.buffer, nullptr);
        if (resource.memory) vkFreeMemory(device, resource.memory, nullptr);
        resource = {};
    }

    void destroy_image(ImageResource& resource) const {
        if (resource.view) vkDestroyImageView(device, resource.view, nullptr);
        if (resource.image) vkDestroyImage(device, resource.image, nullptr);
        if (resource.memory) vkFreeMemory(device, resource.memory, nullptr);
        resource = {};
    }
};

bool fail(const char* message, std::string* error) {
    if (error) *error = message;
    return false;
}

bool vk_fail(const char* operation, VkResult result, std::string* error) {
    if (error) {
        std::ostringstream stream;
        stream << operation << " failed with VkResult " << result;
        *error = stream.str();
    }
    return false;
}

uint32_t find_memory_type(
    const VkPhysicalDeviceMemoryProperties& properties,
    uint32_t type_bits,
    VkMemoryPropertyFlags required,
    VkMemoryPropertyFlags preferred) {
    uint32_t fallback = UINT32_MAX;
    for (uint32_t i = 0; i < properties.memoryTypeCount; ++i) {
        if ((type_bits & (1u << i)) == 0) continue;
        const VkMemoryPropertyFlags flags = properties.memoryTypes[i].propertyFlags;
        if ((flags & required) != required) continue;
        if ((flags & preferred) == preferred) return i;
        if (fallback == UINT32_MAX) fallback = i;
    }
    return fallback;
}

bool create_buffer(
    VkPhysicalDeviceMemoryProperties const& memory_properties,
    VkDevice device,
    VkDeviceSize size,
    VkBufferUsageFlags usage,
    const void* data,
    BufferResource* output,
    std::string* error) {
    VkBufferCreateInfo create_info{};
    create_info.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
    create_info.size = size;
    create_info.usage = usage;
    create_info.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    VkResult result = vkCreateBuffer(device, &create_info, nullptr, &output->buffer);
    if (result != VK_SUCCESS) return vk_fail("vkCreateBuffer", result, error);

    VkMemoryRequirements requirements{};
    vkGetBufferMemoryRequirements(device, output->buffer, &requirements);
    const uint32_t memory_type = find_memory_type(
        memory_properties, requirements.memoryTypeBits,
        VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT,
        VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
    if (memory_type == UINT32_MAX) return fail("no host-visible Vulkan buffer memory type", error);

    VkMemoryAllocateInfo allocate_info{};
    allocate_info.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    allocate_info.allocationSize = requirements.size;
    allocate_info.memoryTypeIndex = memory_type;
    result = vkAllocateMemory(device, &allocate_info, nullptr, &output->memory);
    if (result != VK_SUCCESS) return vk_fail("vkAllocateMemory(buffer)", result, error);
    result = vkBindBufferMemory(device, output->buffer, output->memory, 0);
    if (result != VK_SUCCESS) return vk_fail("vkBindBufferMemory", result, error);

    if (data) {
        void* mapped = nullptr;
        result = vkMapMemory(device, output->memory, 0, VK_WHOLE_SIZE, 0, &mapped);
        if (result != VK_SUCCESS) return vk_fail("vkMapMemory(buffer)", result, error);
        std::memcpy(mapped, data, static_cast<size_t>(size));
        if ((memory_properties.memoryTypes[memory_type].propertyFlags &
             VK_MEMORY_PROPERTY_HOST_COHERENT_BIT) == 0) {
            VkMappedMemoryRange range{};
            range.sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE;
            range.memory = output->memory;
            range.offset = 0;
            range.size = VK_WHOLE_SIZE;
            result = vkFlushMappedMemoryRanges(device, 1, &range);
            if (result != VK_SUCCESS) return vk_fail("vkFlushMappedMemoryRanges", result, error);
        }
        vkUnmapMemory(device, output->memory);
    }
    return true;
}

bool create_texture_image(
    VkPhysicalDeviceMemoryProperties const& memory_properties,
    VkDevice device,
    uint32_t width,
    uint32_t height,
    ImageResource* output,
    std::string* error) {
    VkImageCreateInfo image_info{};
    image_info.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
    image_info.imageType = VK_IMAGE_TYPE_2D;
    image_info.format = VK_FORMAT_R8G8B8A8_SRGB;
    image_info.extent = {width, height, 1};
    image_info.mipLevels = 1;
    image_info.arrayLayers = 1;
    image_info.samples = VK_SAMPLE_COUNT_1_BIT;
    image_info.tiling = VK_IMAGE_TILING_OPTIMAL;
    image_info.usage = VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_SAMPLED_BIT;
    image_info.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    image_info.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    VkResult result = vkCreateImage(device, &image_info, nullptr, &output->image);
    if (result != VK_SUCCESS) return vk_fail("vkCreateImage(texture)", result, error);

    VkMemoryRequirements requirements{};
    vkGetImageMemoryRequirements(device, output->image, &requirements);
    const uint32_t memory_type = find_memory_type(
        memory_properties, requirements.memoryTypeBits, 0, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    if (memory_type == UINT32_MAX) return fail("no compatible Vulkan texture memory type", error);
    VkMemoryAllocateInfo allocate_info{};
    allocate_info.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    allocate_info.allocationSize = requirements.size;
    allocate_info.memoryTypeIndex = memory_type;
    result = vkAllocateMemory(device, &allocate_info, nullptr, &output->memory);
    if (result != VK_SUCCESS) return vk_fail("vkAllocateMemory(texture)", result, error);
    result = vkBindImageMemory(device, output->image, output->memory, 0);
    if (result != VK_SUCCESS) return vk_fail("vkBindImageMemory(texture)", result, error);

    VkImageViewCreateInfo view_info{};
    view_info.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
    view_info.image = output->image;
    view_info.viewType = VK_IMAGE_VIEW_TYPE_2D;
    view_info.format = VK_FORMAT_R8G8B8A8_SRGB;
    view_info.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    view_info.subresourceRange.levelCount = 1;
    view_info.subresourceRange.layerCount = 1;
    result = vkCreateImageView(device, &view_info, nullptr, &output->view);
    if (result != VK_SUCCESS) return vk_fail("vkCreateImageView(texture)", result, error);
    return true;
}

VkSamplerAddressMode sampler_address_mode(TextureClamp clamp, bool* supported) {
    switch (clamp) {
        case TextureClamp::Repeat: return VK_SAMPLER_ADDRESS_MODE_REPEAT;
        case TextureClamp::MirroredRepeat: return VK_SAMPLER_ADDRESS_MODE_MIRRORED_REPEAT;
        case TextureClamp::ClampToEdge: return VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
        case TextureClamp::ClampToBorder: return VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_BORDER;
        default:
            *supported = false;
            return VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    }
}

VkFilter sampler_filter(TextureFilter filter, bool* supported) {
    if (filter == TextureFilter::Linear || filter == TextureFilter::BaseMap) {
        return VK_FILTER_LINEAR;
    }
    if (filter == TextureFilter::Point) return VK_FILTER_NEAREST;
    *supported = false;
    return VK_FILTER_NEAREST;
}

bool create_draw_resources(
    const CapturedVulkanDraw& source,
    const VkPhysicalDeviceMemoryProperties& memory_properties,
    VkDevice device,
    VkRenderPass render_pass,
    DrawResources* output,
    std::string* error) {
    const uint32_t vertex_constants_size = sizeof(source.constants.vertex_float_constants);
    const uint32_t pixel_constants_size = sizeof(source.constants.pixel_float_constants);
    const uint64_t texture_size = static_cast<uint64_t>(source.texture_width) *
                                  source.texture_height * 4u;
    if (source.vertices.empty() || source.indices.empty() || source.index_count == 0 ||
        source.vertex_shader_spirv.empty() || source.pixel_shader_spirv.empty() ||
        source.texture_width == 0 || source.texture_height == 0 ||
        texture_size != source.texture_rgba8.size() || texture_size > (uint64_t{1} << 26)) {
        return fail("captured Vulkan draw resources are incomplete or oversized", error);
    }
    if (source.raster.blend_control_0 != 0x07010706u) {
        return fail("captured blend control is outside the supported retail draw", error);
    }

    if (!create_buffer(memory_properties, device, source.vertices.size(),
                       VK_BUFFER_USAGE_VERTEX_BUFFER_BIT, source.vertices.data(),
                       &output->vertices, error) ||
        !create_buffer(memory_properties, device, source.indices.size(),
                       VK_BUFFER_USAGE_INDEX_BUFFER_BIT, source.indices.data(),
                       &output->indices, error) ||
        !create_buffer(memory_properties, device, vertex_constants_size,
                       VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT,
                       source.constants.vertex_float_constants.data(),
                       &output->vertex_constants, error) ||
        !create_buffer(memory_properties, device, pixel_constants_size,
                       VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT,
                       source.constants.pixel_float_constants.data(),
                       &output->pixel_constants, error) ||
        !create_buffer(memory_properties, device, texture_size,
                       VK_BUFFER_USAGE_TRANSFER_SRC_BIT, source.texture_rgba8.data(),
                       &output->texture_upload, error) ||
        !create_texture_image(memory_properties, device, source.texture_width,
                              source.texture_height, &output->texture, error)) {
        return false;
    }

    bool sampler_supported = true;
    VkSamplerCreateInfo sampler_info{};
    sampler_info.sType = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO;
    sampler_info.magFilter = sampler_filter(source.texture_sampling.mag_filter, &sampler_supported);
    sampler_info.minFilter = sampler_filter(source.texture_sampling.min_filter, &sampler_supported);
    sampler_info.mipmapMode = VK_SAMPLER_MIPMAP_MODE_NEAREST;
    sampler_info.addressModeU = sampler_address_mode(source.texture_sampling.clamps[0], &sampler_supported);
    sampler_info.addressModeV = sampler_address_mode(source.texture_sampling.clamps[1], &sampler_supported);
    sampler_info.addressModeW = sampler_address_mode(source.texture_sampling.clamps[2], &sampler_supported);
    sampler_info.maxLod = 0.0f;
    sampler_info.borderColor = source.texture_sampling.border_alpha_known
                                   ? VK_BORDER_COLOR_FLOAT_OPAQUE_BLACK
                                   : VK_BORDER_COLOR_FLOAT_TRANSPARENT_BLACK;
    if (!sampler_supported || source.texture_sampling.anisotropy != TextureAnisotropy::Disabled ||
        source.texture_sampling.border_color != TextureBorderColor::AbgrBlack) {
        return fail("captured sampler state is outside the Vulkan 1.1 live-draw subset", error);
    }
    VkResult result = vkCreateSampler(device, &sampler_info, nullptr, &output->sampler);
    if (result != VK_SUCCESS) return vk_fail("vkCreateSampler", result, error);

    VkShaderModuleCreateInfo shader_info{};
    shader_info.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
    shader_info.codeSize = source.vertex_shader_spirv.size() * sizeof(uint32_t);
    shader_info.pCode = source.vertex_shader_spirv.data();
    result = vkCreateShaderModule(device, &shader_info, nullptr, &output->vertex_shader);
    if (result != VK_SUCCESS) return vk_fail("vkCreateShaderModule(vertex)", result, error);
    shader_info.codeSize = source.pixel_shader_spirv.size() * sizeof(uint32_t);
    shader_info.pCode = source.pixel_shader_spirv.data();
    result = vkCreateShaderModule(device, &shader_info, nullptr, &output->pixel_shader);
    if (result != VK_SUCCESS) return vk_fail("vkCreateShaderModule(pixel)", result, error);

    VkDescriptorSetLayoutBinding constant_bindings[2]{};
    constant_bindings[0] = {14, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, 1,
                            VK_SHADER_STAGE_VERTEX_BIT, nullptr};
    constant_bindings[1] = {15, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, 1,
                            VK_SHADER_STAGE_FRAGMENT_BIT, nullptr};
    VkDescriptorSetLayoutCreateInfo descriptor_layout_info{};
    descriptor_layout_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
    descriptor_layout_info.bindingCount = 2;
    descriptor_layout_info.pBindings = constant_bindings;
    result = vkCreateDescriptorSetLayout(device, &descriptor_layout_info, nullptr,
                                         &output->descriptor_layouts[0]);
    if (result != VK_SUCCESS) return vk_fail("vkCreateDescriptorSetLayout(constants)", result, error);

    VkDescriptorSetLayoutBinding texture_binding{};
    texture_binding.binding = 0;
    texture_binding.descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
    texture_binding.descriptorCount = 1;
    texture_binding.stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT;
    descriptor_layout_info.bindingCount = 1;
    descriptor_layout_info.pBindings = &texture_binding;
    result = vkCreateDescriptorSetLayout(device, &descriptor_layout_info, nullptr,
                                         &output->descriptor_layouts[1]);
    if (result != VK_SUCCESS) return vk_fail("vkCreateDescriptorSetLayout(texture)", result, error);

    const VkDescriptorPoolSize pool_sizes[2] = {
        {VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, 2},
        {VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 1},
    };
    VkDescriptorPoolCreateInfo pool_info{};
    pool_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;
    pool_info.maxSets = 2;
    pool_info.poolSizeCount = 2;
    pool_info.pPoolSizes = pool_sizes;
    result = vkCreateDescriptorPool(device, &pool_info, nullptr, &output->descriptor_pool);
    if (result != VK_SUCCESS) return vk_fail("vkCreateDescriptorPool", result, error);
    VkDescriptorSetAllocateInfo set_info{};
    set_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
    set_info.descriptorPool = output->descriptor_pool;
    set_info.descriptorSetCount = 2;
    set_info.pSetLayouts = output->descriptor_layouts;
    result = vkAllocateDescriptorSets(device, &set_info, output->descriptor_sets);
    if (result != VK_SUCCESS) return vk_fail("vkAllocateDescriptorSets", result, error);

    VkDescriptorBufferInfo vertex_constant_info{output->vertex_constants.buffer, 0,
                                                vertex_constants_size};
    VkDescriptorBufferInfo pixel_constant_info{output->pixel_constants.buffer, 0,
                                               pixel_constants_size};
    VkDescriptorImageInfo texture_info{output->sampler, output->texture.view,
                                       VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL};
    VkWriteDescriptorSet writes[3]{};
    writes[0].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
    writes[0].dstSet = output->descriptor_sets[0];
    writes[0].dstBinding = 14;
    writes[0].descriptorCount = 1;
    writes[0].descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
    writes[0].pBufferInfo = &vertex_constant_info;
    writes[1].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
    writes[1].dstSet = output->descriptor_sets[0];
    writes[1].dstBinding = 15;
    writes[1].descriptorCount = 1;
    writes[1].descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
    writes[1].pBufferInfo = &pixel_constant_info;
    writes[2].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
    writes[2].dstSet = output->descriptor_sets[1];
    writes[2].dstBinding = 0;
    writes[2].descriptorCount = 1;
    writes[2].descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
    writes[2].pImageInfo = &texture_info;
    vkUpdateDescriptorSets(device, 3, writes, 0, nullptr);

    const VkPipelineLayoutCreateInfo pipeline_layout_info{
        VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO, nullptr, 0, 2,
        output->descriptor_layouts, 0, nullptr};
    result = vkCreatePipelineLayout(device, &pipeline_layout_info, nullptr,
                                    &output->pipeline_layout);
    if (result != VK_SUCCESS) return vk_fail("vkCreatePipelineLayout", result, error);

    VkPipelineShaderStageCreateInfo stages[2]{};
    stages[0].sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
    stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
    stages[0].module = output->vertex_shader;
    stages[0].pName = "main";
    stages[1].sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
    stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
    stages[1].module = output->pixel_shader;
    stages[1].pName = "main";
    const VkVertexInputBindingDescription vertex_binding{0, 12, VK_VERTEX_INPUT_RATE_VERTEX};
    const VkVertexInputAttributeDescription vertex_attribute{
        0, 0, VK_FORMAT_R32G32B32_SFLOAT, 0};
    VkPipelineVertexInputStateCreateInfo vertex_input{};
    vertex_input.sType = VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO;
    vertex_input.vertexBindingDescriptionCount = 1;
    vertex_input.pVertexBindingDescriptions = &vertex_binding;
    vertex_input.vertexAttributeDescriptionCount = 1;
    vertex_input.pVertexAttributeDescriptions = &vertex_attribute;
    VkPipelineInputAssemblyStateCreateInfo assembly{};
    assembly.sType = VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO;
    assembly.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;
    VkPipelineViewportStateCreateInfo viewport_state{};
    viewport_state.sType = VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO;
    viewport_state.viewportCount = 1;
    viewport_state.scissorCount = 1;
    VkPipelineRasterizationStateCreateInfo raster{};
    raster.sType = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO;
    raster.polygonMode = VK_POLYGON_MODE_FILL;
    raster.cullMode = VK_CULL_MODE_NONE;
    raster.frontFace = VK_FRONT_FACE_COUNTER_CLOCKWISE;
    raster.lineWidth = 1.0f;
    VkPipelineMultisampleStateCreateInfo multisample{};
    multisample.sType = VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO;
    multisample.rasterizationSamples = VK_SAMPLE_COUNT_1_BIT;
    VkPipelineDepthStencilStateCreateInfo depth{};
    depth.sType = VK_STRUCTURE_TYPE_PIPELINE_DEPTH_STENCIL_STATE_CREATE_INFO;
    VkPipelineColorBlendAttachmentState blend_attachment{};
    blend_attachment.blendEnable = VK_TRUE;
    blend_attachment.srcColorBlendFactor = VK_BLEND_FACTOR_SRC_ALPHA;
    blend_attachment.dstColorBlendFactor = VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
    blend_attachment.colorBlendOp = VK_BLEND_OP_ADD;
    blend_attachment.srcAlphaBlendFactor = VK_BLEND_FACTOR_ONE;
    blend_attachment.dstAlphaBlendFactor = VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
    blend_attachment.alphaBlendOp = VK_BLEND_OP_ADD;
    blend_attachment.colorWriteMask = 0;
    if (source.raster.color_write_mask & 1u) blend_attachment.colorWriteMask |= VK_COLOR_COMPONENT_R_BIT;
    if (source.raster.color_write_mask & 2u) blend_attachment.colorWriteMask |= VK_COLOR_COMPONENT_G_BIT;
    if (source.raster.color_write_mask & 4u) blend_attachment.colorWriteMask |= VK_COLOR_COMPONENT_B_BIT;
    if (source.raster.color_write_mask & 8u) blend_attachment.colorWriteMask |= VK_COLOR_COMPONENT_A_BIT;
    VkPipelineColorBlendStateCreateInfo blend{};
    blend.sType = VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO;
    blend.attachmentCount = 1;
    blend.pAttachments = &blend_attachment;
    const VkDynamicState dynamic_values[] = {VK_DYNAMIC_STATE_VIEWPORT, VK_DYNAMIC_STATE_SCISSOR};
    VkPipelineDynamicStateCreateInfo dynamic{};
    dynamic.sType = VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO;
    dynamic.dynamicStateCount = 2;
    dynamic.pDynamicStates = dynamic_values;
    VkGraphicsPipelineCreateInfo pipeline_info{};
    pipeline_info.sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO;
    pipeline_info.stageCount = 2;
    pipeline_info.pStages = stages;
    pipeline_info.pVertexInputState = &vertex_input;
    pipeline_info.pInputAssemblyState = &assembly;
    pipeline_info.pViewportState = &viewport_state;
    pipeline_info.pRasterizationState = &raster;
    pipeline_info.pMultisampleState = &multisample;
    pipeline_info.pDepthStencilState = &depth;
    pipeline_info.pColorBlendState = &blend;
    pipeline_info.pDynamicState = &dynamic;
    pipeline_info.layout = output->pipeline_layout;
    pipeline_info.renderPass = render_pass;
    VkPipelineCache pipeline_cache = VK_NULL_HANDLE;
    result = vkCreateGraphicsPipelines(device, pipeline_cache, 1, &pipeline_info, nullptr,
                                       &output->pipeline);
    if (result != VK_SUCCESS) return vk_fail("vkCreateGraphicsPipelines", result, error);
    return true;
}

}  // namespace

bool submit_captured_vulkan_frame(
    VkPhysicalDevice physical_device,
    VkDevice device,
    VkQueue queue,
    uint32_t queue_family_index,
    VkImage output_image,
    VkImageView output_view,
    bool output_written_before,
    uint32_t output_width,
    uint32_t output_height,
    const std::vector<CapturedVulkanDraw>& draws,
    std::string* error) {
    if (!physical_device || !device || !queue || !output_image || !output_view ||
        !output_width || !output_height || draws.empty() || queue_family_index == UINT32_MAX) {
        return fail("invalid captured Vulkan frame target or draw list", error);
    }
    VkPhysicalDeviceMemoryProperties memory_properties{};
    vkGetPhysicalDeviceMemoryProperties(physical_device, &memory_properties);
    FrameResources resources{};
    resources.device = device;
    resources.queue = queue;
    resources.draws.resize(draws.size());

    for (const CapturedVulkanDraw& draw : draws) {
        const CapturedRasterState& raster = draw.raster;
        if (raster.width != output_width || raster.height != output_height ||
            raster.scissor_x1 > output_width || raster.scissor_y1 > output_height ||
            raster.scissor_x0 > raster.scissor_x1 || raster.scissor_y0 > raster.scissor_y1) {
            return fail("captured draw target or scissor differs from PM4_XE_SWAP", error);
        }
    }

    VkAttachmentDescription attachment{};
    attachment.format = VK_FORMAT_A2B10G10R10_UNORM_PACK32;
    attachment.samples = VK_SAMPLE_COUNT_1_BIT;
    attachment.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
    attachment.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
    attachment.stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
    attachment.stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
    attachment.initialLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    attachment.finalLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    VkAttachmentReference color_reference{0, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL};
    VkSubpassDescription subpass{};
    subpass.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
    subpass.colorAttachmentCount = 1;
    subpass.pColorAttachments = &color_reference;
    VkRenderPassCreateInfo render_pass_info{};
    render_pass_info.sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
    render_pass_info.attachmentCount = 1;
    render_pass_info.pAttachments = &attachment;
    render_pass_info.subpassCount = 1;
    render_pass_info.pSubpasses = &subpass;
    VkResult result = vkCreateRenderPass(device, &render_pass_info, nullptr,
                                         &resources.render_pass);
    if (result != VK_SUCCESS) return vk_fail("vkCreateRenderPass", result, error);

    VkFramebufferCreateInfo framebuffer_info{};
    framebuffer_info.sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
    framebuffer_info.renderPass = resources.render_pass;
    framebuffer_info.attachmentCount = 1;
    framebuffer_info.pAttachments = &output_view;
    framebuffer_info.width = output_width;
    framebuffer_info.height = output_height;
    framebuffer_info.layers = 1;
    result = vkCreateFramebuffer(device, &framebuffer_info, nullptr, &resources.framebuffer);
    if (result != VK_SUCCESS) return vk_fail("vkCreateFramebuffer", result, error);

    // Pipelines need the render pass compatibility key, so create them after
    // the pass exists. Resource upload and descriptor creation are independent.
    for (size_t i = 0; i < draws.size(); ++i) {
        DrawResources& draw = resources.draws[i];
        // Recreate just the graphics pipeline with this frame's render pass.
        if (!create_draw_resources(draws[i], memory_properties, device, resources.render_pass,
                                   &draw, error)) {
            return false;
        }
    }

    VkCommandPoolCreateInfo pool_info{};
    pool_info.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
    pool_info.flags = VK_COMMAND_POOL_CREATE_TRANSIENT_BIT;
    pool_info.queueFamilyIndex = queue_family_index;
    result = vkCreateCommandPool(device, &pool_info, nullptr, &resources.command_pool);
    if (result != VK_SUCCESS) return vk_fail("vkCreateCommandPool", result, error);
    VkCommandBufferAllocateInfo command_info{};
    command_info.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
    command_info.commandPool = resources.command_pool;
    command_info.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    command_info.commandBufferCount = 1;
    VkCommandBuffer command = VK_NULL_HANDLE;
    result = vkAllocateCommandBuffers(device, &command_info, &command);
    if (result != VK_SUCCESS) return vk_fail("vkAllocateCommandBuffers", result, error);
    VkCommandBufferBeginInfo begin_info{};
    begin_info.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
    begin_info.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    result = vkBeginCommandBuffer(command, &begin_info);
    if (result != VK_SUCCESS) return vk_fail("vkBeginCommandBuffer", result, error);

    std::vector<VkBufferMemoryBarrier> host_barriers;
    host_barriers.reserve(draws.size() * 5);
    for (const DrawResources& draw : resources.draws) {
        const std::array<std::pair<const BufferResource*, VkAccessFlags>, 5> buffers = {{
            {&draw.vertices, VK_ACCESS_VERTEX_ATTRIBUTE_READ_BIT},
            {&draw.indices, VK_ACCESS_INDEX_READ_BIT},
            {&draw.vertex_constants, VK_ACCESS_UNIFORM_READ_BIT},
            {&draw.pixel_constants, VK_ACCESS_UNIFORM_READ_BIT},
            {&draw.texture_upload, VK_ACCESS_TRANSFER_READ_BIT},
        }};
        for (const auto& [buffer, destination_access] : buffers) {
            VkBufferMemoryBarrier barrier{};
            barrier.sType = VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER;
            barrier.srcAccessMask = VK_ACCESS_HOST_WRITE_BIT;
            barrier.dstAccessMask = destination_access;
            barrier.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            barrier.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            barrier.buffer = buffer->buffer;
            barrier.size = VK_WHOLE_SIZE;
            host_barriers.push_back(barrier);
        }
    }
    vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_HOST_BIT,
                         VK_PIPELINE_STAGE_VERTEX_INPUT_BIT |
                             VK_PIPELINE_STAGE_VERTEX_SHADER_BIT |
                             VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT |
                             VK_PIPELINE_STAGE_TRANSFER_BIT,
                         0, 0, nullptr, static_cast<uint32_t>(host_barriers.size()),
                         host_barriers.data(), 0, nullptr);

    VkImageMemoryBarrier output_to_color{};
    output_to_color.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
    output_to_color.srcAccessMask = output_written_before ? VK_ACCESS_SHADER_READ_BIT : 0;
    output_to_color.dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_READ_BIT |
                                   VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
    output_to_color.oldLayout = output_written_before ? VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL
                                                      : VK_IMAGE_LAYOUT_UNDEFINED;
    output_to_color.newLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    output_to_color.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    output_to_color.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    output_to_color.image = output_image;
    output_to_color.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    output_to_color.subresourceRange.levelCount = 1;
    output_to_color.subresourceRange.layerCount = 1;
    vkCmdPipelineBarrier(command,
                         output_written_before ? VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT
                                               : VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                         VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT, 0,
                         0, nullptr, 0, nullptr, 1, &output_to_color);

    for (size_t i = 0; i < resources.draws.size(); ++i) {
        const DrawResources& draw = resources.draws[i];
        VkImageMemoryBarrier texture_barrier{};
        texture_barrier.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
        texture_barrier.srcAccessMask = 0;
        texture_barrier.dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
        texture_barrier.oldLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        texture_barrier.newLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
        texture_barrier.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        texture_barrier.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        texture_barrier.image = draw.texture.image;
        texture_barrier.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        texture_barrier.subresourceRange.levelCount = 1;
        texture_barrier.subresourceRange.layerCount = 1;
        vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                             VK_PIPELINE_STAGE_TRANSFER_BIT, 0,
                             0, nullptr, 0, nullptr, 1, &texture_barrier);
        VkBufferImageCopy copy{};
        copy.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        copy.imageSubresource.layerCount = 1;
        copy.imageExtent = {draws[i].texture_width, draws[i].texture_height, 1};
        vkCmdCopyBufferToImage(command, draw.texture_upload.buffer, draw.texture.image,
                               VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &copy);
        VkImageMemoryBarrier texture_to_sample{};
        texture_to_sample.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
        texture_to_sample.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
        texture_to_sample.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
        texture_to_sample.oldLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
        texture_to_sample.newLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
        texture_to_sample.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        texture_to_sample.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        texture_to_sample.image = draw.texture.image;
        texture_to_sample.subresourceRange = texture_barrier.subresourceRange;
        vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_TRANSFER_BIT,
                             VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT, 0,
                             0, nullptr, 0, nullptr, 1, &texture_to_sample);
    }

    VkClearValue clear{};
    clear.color.float32[3] = 1.0f;
    VkRenderPassBeginInfo pass_begin{};
    pass_begin.sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
    pass_begin.renderPass = resources.render_pass;
    pass_begin.framebuffer = resources.framebuffer;
    pass_begin.renderArea.extent = {output_width, output_height};
    pass_begin.clearValueCount = 1;
    pass_begin.pClearValues = &clear;
    vkCmdBeginRenderPass(command, &pass_begin, VK_SUBPASS_CONTENTS_INLINE);

    for (size_t i = 0; i < draws.size(); ++i) {
        const CapturedVulkanDraw& source = draws[i];
        const DrawResources& draw = resources.draws[i];
        VkViewport viewport{};
        viewport.x = 0.0f;
        viewport.y = source.raster.viewport_y_flipped
                         ? static_cast<float>(source.raster.height)
                         : 0.0f;
        viewport.width = static_cast<float>(source.raster.width);
        viewport.height = source.raster.viewport_y_flipped
                              ? -static_cast<float>(source.raster.height)
                              : static_cast<float>(source.raster.height);
        viewport.minDepth = 0.0f;
        viewport.maxDepth = 1.0f;
        VkRect2D scissor{};
        scissor.offset = {static_cast<int32_t>(source.raster.scissor_x0),
                          static_cast<int32_t>(source.raster.scissor_y0)};
        scissor.extent = {source.raster.scissor_x1 - source.raster.scissor_x0,
                          source.raster.scissor_y1 - source.raster.scissor_y0};
        const VkDeviceSize vertex_offset = 0;
        vkCmdBindPipeline(command, VK_PIPELINE_BIND_POINT_GRAPHICS, draw.pipeline);
        vkCmdSetViewport(command, 0, 1, &viewport);
        vkCmdSetScissor(command, 0, 1, &scissor);
        vkCmdBindVertexBuffers(command, 0, 1, &draw.vertices.buffer, &vertex_offset);
        vkCmdBindIndexBuffer(command, draw.indices.buffer, 0, VK_INDEX_TYPE_UINT16);
        vkCmdBindDescriptorSets(command, VK_PIPELINE_BIND_POINT_GRAPHICS,
                                draw.pipeline_layout, 0, 2,
                                draw.descriptor_sets, 0, nullptr);
        vkCmdDrawIndexed(command, source.index_count, 1, 0, 0, 0);
    }
    vkCmdEndRenderPass(command);

    VkImageMemoryBarrier output_to_sample{};
    output_to_sample.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
    output_to_sample.srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
    output_to_sample.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
    output_to_sample.oldLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    output_to_sample.newLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
    output_to_sample.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    output_to_sample.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    output_to_sample.image = output_image;
    output_to_sample.subresourceRange = output_to_color.subresourceRange;
    vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
                         VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT, 0,
                         0, nullptr, 0, nullptr, 1, &output_to_sample);
    result = vkEndCommandBuffer(command);
    if (result != VK_SUCCESS) return vk_fail("vkEndCommandBuffer", result, error);
    VkSubmitInfo submit{};
    submit.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
    submit.commandBufferCount = 1;
    submit.pCommandBuffers = &command;
    result = vkQueueSubmit(queue, 1, &submit, VK_NULL_HANDLE);
    if (result != VK_SUCCESS) return vk_fail("vkQueueSubmit(captured frame)", result, error);
    resources.submitted = true;
    result = vkQueueWaitIdle(queue);
    if (result != VK_SUCCESS) return vk_fail("vkQueueWaitIdle(captured frame)", result, error);
    resources.submitted = false;
    if (error) error->clear();
    return true;
}

}  // namespace shift::xbox
