#include <vulkan/vulkan.h>

#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

[[noreturn]] void fail(const std::string& message, VkResult result) {
    throw std::runtime_error(message + " (" + std::to_string(static_cast<int>(result)) + ")");
}

void check(VkResult result, const char* message) {
    if (result != VK_SUCCESS) {
        fail(message, result);
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
        throw std::runtime_error("failed reading SPIR-V file: " + path);
    }
    return code;
}

struct Context {
    VkInstance instance = VK_NULL_HANDLE;
    VkPhysicalDevice physical = VK_NULL_HANDLE;
    VkDevice device = VK_NULL_HANDLE;
    VkQueue queue = VK_NULL_HANDLE;
    uint32_t queue_family = 0;
    VkCommandPool command_pool = VK_NULL_HANDLE;
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
    app.pApplicationName = "SHIFT Vulkan Headless Triangle";
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
        throw std::runtime_error("no graphics queue");
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

VkShaderModule shader_module(VkDevice device, const std::vector<uint32_t>& code) {
    VkShaderModuleCreateInfo info{};
    info.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
    info.codeSize = code.size() * sizeof(uint32_t);
    info.pCode = code.data();
    VkShaderModule module = VK_NULL_HANDLE;
    check(vkCreateShaderModule(device, &info, nullptr, &module), "vkCreateShaderModule failed");
    return module;
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
    if (!output) {
        throw std::runtime_error("failed writing output PPM");
    }
}

}  // namespace

int main(int argc, char** argv) {
    const std::string output = argc >= 2 ? argv[1] : "shift_vulkan_triangle.ppm";
    const std::string shader_dir = argc >= 3 ? argv[2] : "shaders";
    constexpr uint32_t width = 256;
    constexpr uint32_t height = 256;
    constexpr VkFormat format = VK_FORMAT_R8G8B8A8_UNORM;

    Context ctx{};
    VkImage image = VK_NULL_HANDLE;
    VkDeviceMemory image_memory = VK_NULL_HANDLE;
    VkImageView image_view = VK_NULL_HANDLE;
    VkRenderPass render_pass = VK_NULL_HANDLE;
    VkFramebuffer framebuffer = VK_NULL_HANDLE;
    VkPipelineLayout pipeline_layout = VK_NULL_HANDLE;
    VkPipeline pipeline = VK_NULL_HANDLE;
    VkShaderModule vertex_shader = VK_NULL_HANDLE;
    VkShaderModule fragment_shader = VK_NULL_HANDLE;
    VkBuffer staging = VK_NULL_HANDLE;
    VkDeviceMemory staging_memory = VK_NULL_HANDLE;

    try {
        ctx = create_context();

        VkPhysicalDeviceProperties properties{};
        vkGetPhysicalDeviceProperties(ctx.physical, &properties);

        VkFormatProperties format_properties{};
        vkGetPhysicalDeviceFormatProperties(ctx.physical, format, &format_properties);
        const VkFormatFeatureFlags required_features =
            VK_FORMAT_FEATURE_COLOR_ATTACHMENT_BIT |
            VK_FORMAT_FEATURE_TRANSFER_SRC_BIT;
        if ((format_properties.optimalTilingFeatures & required_features) != required_features) {
            throw std::runtime_error("R8G8B8A8_UNORM lacks required optimal-tiled features");
        }

        VkImageCreateInfo image_info{};
        image_info.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
        image_info.imageType = VK_IMAGE_TYPE_2D;
        image_info.format = format;
        image_info.extent = {width, height, 1};
        image_info.mipLevels = 1;
        image_info.arrayLayers = 1;
        image_info.samples = VK_SAMPLE_COUNT_1_BIT;
        image_info.tiling = VK_IMAGE_TILING_OPTIMAL;
        image_info.usage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
        image_info.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        check(vkCreateImage(ctx.device, &image_info, nullptr, &image), "vkCreateImage failed");

        VkMemoryRequirements image_requirements{};
        vkGetImageMemoryRequirements(ctx.device, image, &image_requirements);
        VkMemoryAllocateInfo image_alloc{};
        image_alloc.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
        image_alloc.allocationSize = image_requirements.size;
        image_alloc.memoryTypeIndex = memory_type(
            ctx.physical, image_requirements.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        check(vkAllocateMemory(ctx.device, &image_alloc, nullptr, &image_memory),
              "vkAllocateMemory(image) failed");
        check(vkBindImageMemory(ctx.device, image, image_memory, 0),
              "vkBindImageMemory failed");

        VkImageViewCreateInfo view_info{};
        view_info.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
        view_info.image = image;
        view_info.viewType = VK_IMAGE_VIEW_TYPE_2D;
        view_info.format = format;
        view_info.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        view_info.subresourceRange.levelCount = 1;
        view_info.subresourceRange.layerCount = 1;
        check(vkCreateImageView(ctx.device, &view_info, nullptr, &image_view),
              "vkCreateImageView failed");

        const std::vector<uint32_t> vert = read_spirv(
            shader_dir + "/triangle.vert.spv");
        const std::vector<uint32_t> frag = read_spirv(
            shader_dir + "/triangle.frag.spv");
        vertex_shader = shader_module(ctx.device, vert);
        fragment_shader = shader_module(ctx.device, frag);

        VkAttachmentDescription color_attachment{};
        color_attachment.format = format;
        color_attachment.samples = VK_SAMPLE_COUNT_1_BIT;
        color_attachment.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
        color_attachment.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
        color_attachment.stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
        color_attachment.stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
        color_attachment.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        color_attachment.finalLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;

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

        VkRenderPassCreateInfo render_pass_info{};
        render_pass_info.sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
        render_pass_info.attachmentCount = 1;
        render_pass_info.pAttachments = &color_attachment;
        render_pass_info.subpassCount = 1;
        render_pass_info.pSubpasses = &subpass;
        render_pass_info.dependencyCount = 2;
        render_pass_info.pDependencies = dependencies;
        check(vkCreateRenderPass(ctx.device, &render_pass_info, nullptr, &render_pass),
              "vkCreateRenderPass failed");

        VkFramebufferCreateInfo framebuffer_info{};
        framebuffer_info.sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
        framebuffer_info.renderPass = render_pass;
        framebuffer_info.attachmentCount = 1;
        framebuffer_info.pAttachments = &image_view;
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

        VkPipelineVertexInputStateCreateInfo vertex_input{};
        vertex_input.sType = VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO;

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

        VkPipelineColorBlendAttachmentState blend_attachment{};
        blend_attachment.blendEnable = VK_FALSE;
        blend_attachment.colorWriteMask =
            VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
            VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT;

        VkPipelineColorBlendStateCreateInfo blend{};
        blend.sType = VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO;
        blend.attachmentCount = 1;
        blend.pAttachments = &blend_attachment;

        VkPipelineLayoutCreateInfo layout_info{};
        layout_info.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
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
        pipeline_info.pColorBlendState = &blend;
        pipeline_info.layout = pipeline_layout;
        pipeline_info.renderPass = render_pass;
        pipeline_info.subpass = 0;
        check(vkCreateGraphicsPipelines(
            ctx.device, VK_NULL_HANDLE, 1, &pipeline_info, nullptr, &pipeline),
            "vkCreateGraphicsPipelines failed");

        const VkDeviceSize staging_size =
            static_cast<VkDeviceSize>(width) * height * 4;
        VkBufferCreateInfo staging_info{};
        staging_info.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
        staging_info.size = staging_size;
        staging_info.usage = VK_BUFFER_USAGE_TRANSFER_DST_BIT;
        check(vkCreateBuffer(ctx.device, &staging_info, nullptr, &staging),
              "vkCreateBuffer failed");

        VkMemoryRequirements staging_requirements{};
        vkGetBufferMemoryRequirements(ctx.device, staging, &staging_requirements);
        VkMemoryAllocateInfo staging_alloc{};
        staging_alloc.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
        staging_alloc.allocationSize = staging_requirements.size;
        staging_alloc.memoryTypeIndex = memory_type(
            ctx.physical, staging_requirements.memoryTypeBits,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        check(vkAllocateMemory(ctx.device, &staging_alloc, nullptr, &staging_memory),
              "vkAllocateMemory(staging) failed");
        check(vkBindBufferMemory(ctx.device, staging, staging_memory, 0),
              "vkBindBufferMemory failed");

        VkCommandBufferAllocateInfo command_alloc{};
        command_alloc.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
        command_alloc.commandPool = ctx.command_pool;
        command_alloc.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        command_alloc.commandBufferCount = 1;
        VkCommandBuffer command = VK_NULL_HANDLE;
        check(vkAllocateCommandBuffers(ctx.device, &command_alloc, &command),
              "vkAllocateCommandBuffers failed");

        VkCommandBufferBeginInfo begin{};
        begin.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
        check(vkBeginCommandBuffer(command, &begin), "vkBeginCommandBuffer failed");

        VkRenderPassBeginInfo begin_pass{};
        begin_pass.sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
        begin_pass.renderPass = render_pass;
        begin_pass.framebuffer = framebuffer;
        begin_pass.renderArea.extent = {width, height};
        VkClearValue clear{};
        clear.color.float32[0] = 0.02f;
        clear.color.float32[1] = 0.02f;
        clear.color.float32[2] = 0.02f;
        clear.color.float32[3] = 1.0f;
        begin_pass.clearValueCount = 1;
        begin_pass.pClearValues = &clear;

        vkCmdBeginRenderPass(command, &begin_pass, VK_SUBPASS_CONTENTS_INLINE);
        vkCmdBindPipeline(command, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline);
        vkCmdDraw(command, 3, 1, 0, 0);
        vkCmdEndRenderPass(command);

        VkBufferImageCopy copy{};
        copy.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        copy.imageSubresource.layerCount = 1;
        copy.imageExtent = {width, height, 1};
        vkCmdCopyImageToBuffer(
            command,
            image,
            VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
            staging,
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

        void* mapped = nullptr;
        check(vkMapMemory(ctx.device, staging_memory, 0, staging_size, 0, &mapped),
              "vkMapMemory failed");
        std::vector<uint8_t> rgba(static_cast<size_t>(staging_size));
        std::memcpy(rgba.data(), mapped, rgba.size());
        vkUnmapMemory(ctx.device, staging_memory);

        write_ppm(output, rgba, width, height);

        std::cout << "{\n";
        std::cout << "  \"format\": \"SHIFT.VulkanHeadlessTriangle/1\",\n";
        std::cout << "  \"device\": \"" << properties.deviceName << "\",\n";
        std::cout << "  \"queue_family\": " << ctx.queue_family << ",\n";
        std::cout << "  \"width\": " << width << ",\n";
        std::cout << "  \"height\": " << height << ",\n";
        std::cout << "  \"shader_backend\": \"SPIR-V\",\n";
        std::cout << "  \"output\": \"" << output << "\"\n";
        std::cout << "}\n";

        vkFreeCommandBuffers(ctx.device, ctx.command_pool, 1, &command);
        vkDestroyBuffer(ctx.device, staging, nullptr);
        vkFreeMemory(ctx.device, staging_memory, nullptr);
        vkDestroyPipeline(ctx.device, pipeline, nullptr);
        vkDestroyPipelineLayout(ctx.device, pipeline_layout, nullptr);
        vkDestroyFramebuffer(ctx.device, framebuffer, nullptr);
        vkDestroyRenderPass(ctx.device, render_pass, nullptr);
        vkDestroyImageView(ctx.device, image_view, nullptr);
        vkDestroyShaderModule(ctx.device, vertex_shader, nullptr);
        vkDestroyShaderModule(ctx.device, fragment_shader, nullptr);
        vkDestroyImage(ctx.device, image, nullptr);
        vkFreeMemory(ctx.device, image_memory, nullptr);
        destroy(ctx);
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "shift_vulkan_headless_triangle: " << error.what() << "\n";
        if (ctx.device != VK_NULL_HANDLE) {
            if (staging != VK_NULL_HANDLE) vkDestroyBuffer(ctx.device, staging, nullptr);
            if (staging_memory != VK_NULL_HANDLE) vkFreeMemory(ctx.device, staging_memory, nullptr);
            if (pipeline != VK_NULL_HANDLE) vkDestroyPipeline(ctx.device, pipeline, nullptr);
            if (pipeline_layout != VK_NULL_HANDLE) vkDestroyPipelineLayout(ctx.device, pipeline_layout, nullptr);
            if (framebuffer != VK_NULL_HANDLE) vkDestroyFramebuffer(ctx.device, framebuffer, nullptr);
            if (render_pass != VK_NULL_HANDLE) vkDestroyRenderPass(ctx.device, render_pass, nullptr);
            if (image_view != VK_NULL_HANDLE) vkDestroyImageView(ctx.device, image_view, nullptr);
            if (vertex_shader != VK_NULL_HANDLE) vkDestroyShaderModule(ctx.device, vertex_shader, nullptr);
            if (fragment_shader != VK_NULL_HANDLE) vkDestroyShaderModule(ctx.device, fragment_shader, nullptr);
            if (image != VK_NULL_HANDLE) vkDestroyImage(ctx.device, image, nullptr);
            if (image_memory != VK_NULL_HANDLE) vkFreeMemory(ctx.device, image_memory, nullptr);
        }
        destroy(ctx);
        return EXIT_FAILURE;
    }
}
