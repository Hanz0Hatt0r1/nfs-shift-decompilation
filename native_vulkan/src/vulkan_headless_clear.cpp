#include <vulkan/vulkan.h>

#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
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

uint32_t find_memory_type(
    VkPhysicalDevice physical_device,
    uint32_t type_bits,
    VkMemoryPropertyFlags required) {

    VkPhysicalDeviceMemoryProperties memory{};
    vkGetPhysicalDeviceMemoryProperties(physical_device, &memory);
    for (uint32_t i = 0; i < memory.memoryTypeCount; ++i) {
        if ((type_bits & (1u << i)) != 0 &&
            (memory.memoryTypes[i].propertyFlags & required) == required) {
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
    app.pApplicationName = "SHIFT Vulkan Headless Clear";
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
        throw std::runtime_error("no Vulkan physical devices available");
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
        throw std::runtime_error("no graphics-capable Vulkan queue family available");
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

    VkCommandPoolCreateInfo pool_info{};
    pool_info.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
    pool_info.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
    pool_info.queueFamilyIndex = ctx.queue_family;
    check(vkCreateCommandPool(ctx.device, &pool_info, nullptr, &ctx.command_pool),
          "vkCreateCommandPool failed");

    return ctx;
}

void write_ppm(
    const std::string& path,
    const std::vector<uint8_t>& rgba,
    uint32_t width,
    uint32_t height) {

    if (rgba.size() != static_cast<size_t>(width) * height * 4) {
        throw std::runtime_error("unexpected staging buffer size");
    }

    std::ofstream output(path, std::ios::binary);
    if (!output) {
        throw std::runtime_error("cannot open output PPM: " + path);
    }

    output << "P6\n" << width << " " << height << "\n255\n";
    for (size_t i = 0; i < rgba.size(); i += 4) {
        output.put(static_cast<char>(rgba[i + 0]));
        output.put(static_cast<char>(rgba[i + 1]));
        output.put(static_cast<char>(rgba[i + 2]));
    }
    if (!output) {
        throw std::runtime_error("failed while writing output PPM: " + path);
    }
}

}  // namespace

int main(int argc, char** argv) {
    const std::string output = argc >= 2 ? argv[1] : "shift_vulkan_headless.ppm";
    constexpr uint32_t width = 256;
    constexpr uint32_t height = 256;
    constexpr VkFormat format = VK_FORMAT_R8G8B8A8_UNORM;

    Context ctx{};
    VkImage image = VK_NULL_HANDLE;
    VkDeviceMemory image_memory = VK_NULL_HANDLE;
    VkBuffer staging = VK_NULL_HANDLE;
    VkDeviceMemory staging_memory = VK_NULL_HANDLE;

    try {
        ctx = create_context();

        VkPhysicalDeviceProperties properties{};
        vkGetPhysicalDeviceProperties(ctx.physical, &properties);

        VkImageCreateInfo image_info{};
        image_info.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
        image_info.imageType = VK_IMAGE_TYPE_2D;
        image_info.format = format;
        image_info.extent = {width, height, 1};
        image_info.mipLevels = 1;
        image_info.arrayLayers = 1;
        image_info.samples = VK_SAMPLE_COUNT_1_BIT;
        image_info.tiling = VK_IMAGE_TILING_OPTIMAL;
        image_info.usage = VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
        image_info.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        check(vkCreateImage(ctx.device, &image_info, nullptr, &image), "vkCreateImage failed");

        VkMemoryRequirements image_requirements{};
        vkGetImageMemoryRequirements(ctx.device, image, &image_requirements);
        const uint32_t image_memory_type = find_memory_type(
            ctx.physical,
            image_requirements.memoryTypeBits,
            VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);

        VkMemoryAllocateInfo image_allocate{};
        image_allocate.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
        image_allocate.allocationSize = image_requirements.size;
        image_allocate.memoryTypeIndex = image_memory_type;
        check(vkAllocateMemory(ctx.device, &image_allocate, nullptr, &image_memory),
              "vkAllocateMemory(image) failed");
        check(vkBindImageMemory(ctx.device, image, image_memory, 0),
              "vkBindImageMemory failed");

        const VkDeviceSize staging_size =
            static_cast<VkDeviceSize>(width) * height * 4;

        VkBufferCreateInfo buffer_info{};
        buffer_info.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
        buffer_info.size = staging_size;
        buffer_info.usage = VK_BUFFER_USAGE_TRANSFER_DST_BIT;
        check(vkCreateBuffer(ctx.device, &buffer_info, nullptr, &staging),
              "vkCreateBuffer failed");

        VkMemoryRequirements staging_requirements{};
        vkGetBufferMemoryRequirements(ctx.device, staging, &staging_requirements);
        const uint32_t staging_memory_type = find_memory_type(
            ctx.physical,
            staging_requirements.memoryTypeBits,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);

        VkMemoryAllocateInfo staging_allocate{};
        staging_allocate.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
        staging_allocate.allocationSize = staging_requirements.size;
        staging_allocate.memoryTypeIndex = staging_memory_type;
        check(vkAllocateMemory(ctx.device, &staging_allocate, nullptr, &staging_memory),
              "vkAllocateMemory(staging) failed");
        check(vkBindBufferMemory(ctx.device, staging, staging_memory, 0),
              "vkBindBufferMemory failed");

        VkCommandBufferAllocateInfo command_allocate{};
        command_allocate.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
        command_allocate.commandPool = ctx.command_pool;
        command_allocate.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        command_allocate.commandBufferCount = 1;

        VkCommandBuffer command = VK_NULL_HANDLE;
        check(vkAllocateCommandBuffers(ctx.device, &command_allocate, &command),
              "vkAllocateCommandBuffers failed");

        VkCommandBufferBeginInfo begin{};
        begin.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
        check(vkBeginCommandBuffer(command, &begin), "vkBeginCommandBuffer failed");

        VkImageMemoryBarrier to_transfer{};
        to_transfer.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
        to_transfer.srcAccessMask = 0;
        to_transfer.dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
        to_transfer.oldLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        to_transfer.newLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
        to_transfer.image = image;
        to_transfer.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        to_transfer.subresourceRange.baseMipLevel = 0;
        to_transfer.subresourceRange.levelCount = 1;
        to_transfer.subresourceRange.baseArrayLayer = 0;
        to_transfer.subresourceRange.layerCount = 1;

        vkCmdPipelineBarrier(
            command,
            VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
            VK_PIPELINE_STAGE_TRANSFER_BIT,
            0,
            0, nullptr,
            0, nullptr,
            1, &to_transfer);

        VkClearColorValue clear{};
        clear.float32[0] = 0.125f;
        clear.float32[1] = 0.250f;
        clear.float32[2] = 0.500f;
        clear.float32[3] = 1.0f;
        VkImageSubresourceRange range{};
        range.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        range.baseMipLevel = 0;
        range.levelCount = 1;
        range.baseArrayLayer = 0;
        range.layerCount = 1;
        vkCmdClearColorImage(
            command,
            image,
            VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
            &clear,
            1,
            &range);

        VkImageMemoryBarrier to_source{};
        to_source.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
        to_source.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
        to_source.dstAccessMask = VK_ACCESS_TRANSFER_READ_BIT;
        to_source.oldLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
        to_source.newLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
        to_source.image = image;
        to_source.subresourceRange = range;

        vkCmdPipelineBarrier(
            command,
            VK_PIPELINE_STAGE_TRANSFER_BIT,
            VK_PIPELINE_STAGE_TRANSFER_BIT,
            0,
            0, nullptr,
            0, nullptr,
            1, &to_source);

        VkBufferImageCopy copy{};
        copy.bufferOffset = 0;
        copy.bufferRowLength = 0;
        copy.bufferImageHeight = 0;
        copy.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        copy.imageSubresource.mipLevel = 0;
        copy.imageSubresource.baseArrayLayer = 0;
        copy.imageSubresource.layerCount = 1;
        copy.imageOffset = {0, 0, 0};
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
        std::cout << "  \"format\": \"SHIFT.VulkanHeadlessImage/1\",\n";
        std::cout << "  \"device\": \"" << properties.deviceName << "\",\n";
        std::cout << "  \"queue_family\": " << ctx.queue_family << ",\n";
        std::cout << "  \"width\": " << width << ",\n";
        std::cout << "  \"height\": " << height << ",\n";
        std::cout << "  \"clear_rgba\": [0.125, 0.25, 0.5, 1.0],\n";
        std::cout << "  \"output\": \"" << output << "\",\n";
        std::cout << "  \"bytes\": " << rgba.size() << "\n";
        std::cout << "}\n";

        vkFreeCommandBuffers(ctx.device, ctx.command_pool, 1, &command);
        vkDestroyBuffer(ctx.device, staging, nullptr);
        vkFreeMemory(ctx.device, staging_memory, nullptr);
        vkDestroyImage(ctx.device, image, nullptr);
        vkFreeMemory(ctx.device, image_memory, nullptr);
        destroy(ctx);
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "shift_vulkan_headless_clear: " << error.what() << "\n";
        if (ctx.device != VK_NULL_HANDLE) {
            if (staging != VK_NULL_HANDLE) vkDestroyBuffer(ctx.device, staging, nullptr);
            if (staging_memory != VK_NULL_HANDLE) vkFreeMemory(ctx.device, staging_memory, nullptr);
            if (image != VK_NULL_HANDLE) vkDestroyImage(ctx.device, image, nullptr);
            if (image_memory != VK_NULL_HANDLE) vkFreeMemory(ctx.device, image_memory, nullptr);
        }
        destroy(ctx);
        return EXIT_FAILURE;
    }
}
