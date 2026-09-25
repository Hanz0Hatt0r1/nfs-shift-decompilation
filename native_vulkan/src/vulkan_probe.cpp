#include <vulkan/vulkan.h>
#include <cstdint>

#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

namespace {

const char* result_name(VkResult result) {
    switch (result) {
        case VK_SUCCESS: return "VK_SUCCESS";
        case VK_NOT_READY: return "VK_NOT_READY";
        case VK_TIMEOUT: return "VK_TIMEOUT";
        case VK_EVENT_SET: return "VK_EVENT_SET";
        case VK_EVENT_RESET: return "VK_EVENT_RESET";
        case VK_INCOMPLETE: return "VK_INCOMPLETE";
        case VK_ERROR_OUT_OF_HOST_MEMORY: return "VK_ERROR_OUT_OF_HOST_MEMORY";
        case VK_ERROR_OUT_OF_DEVICE_MEMORY: return "VK_ERROR_OUT_OF_DEVICE_MEMORY";
        case VK_ERROR_INITIALIZATION_FAILED: return "VK_ERROR_INITIALIZATION_FAILED";
        case VK_ERROR_LAYER_NOT_PRESENT: return "VK_ERROR_LAYER_NOT_PRESENT";
        case VK_ERROR_EXTENSION_NOT_PRESENT: return "VK_ERROR_EXTENSION_NOT_PRESENT";
        case VK_ERROR_FEATURE_NOT_PRESENT: return "VK_ERROR_FEATURE_NOT_PRESENT";
        case VK_ERROR_INCOMPATIBLE_DRIVER: return "VK_ERROR_INCOMPATIBLE_DRIVER";
        default: return "VK_RESULT_UNKNOWN";
    }
}

bool has_graphics_or_compute_queue(VkPhysicalDevice device) {
    std::uint32_t count = 0;
    vkGetPhysicalDeviceQueueFamilyProperties(device, &count, nullptr);
    std::vector<VkQueueFamilyProperties> families(count);
    if (count != 0) {
        vkGetPhysicalDeviceQueueFamilyProperties(device, &count, families.data());
    }

    for (const auto& family : families) {
        const VkQueueFlags flags = family.queueFlags;
        if ((flags & VK_QUEUE_GRAPHICS_BIT) != 0 || (flags & VK_QUEUE_COMPUTE_BIT) != 0) {
            return true;
        }
    }
    return false;
}

}  // namespace

int main() {
    uint32_t loader_version = VK_API_VERSION_1_0;
    if (vkEnumerateInstanceVersion != nullptr) {
        const VkResult version_result = vkEnumerateInstanceVersion(&loader_version);
        if (version_result != VK_SUCCESS) {
            std::cerr << "vkEnumerateInstanceVersion failed: "
                      << result_name(version_result) << "\n";
            return EXIT_FAILURE;
        }
    }

    const uint32_t requested_api = VK_MAKE_API_VERSION(
        0, VK_API_VERSION_MAJOR(loader_version),
        VK_API_VERSION_MINOR(loader_version), 0);

    VkApplicationInfo app_info{};
    app_info.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
    app_info.pApplicationName = "SHIFT Vulkan Probe";
    app_info.applicationVersion = 1;
    app_info.pEngineName = "SHIFT";
    app_info.engineVersion = 1;
    app_info.apiVersion = requested_api;

    VkInstanceCreateInfo instance_info{};
    instance_info.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    instance_info.pApplicationInfo = &app_info;

    VkInstance instance = VK_NULL_HANDLE;
    VkResult result = vkCreateInstance(&instance_info, nullptr, &instance);
    if (result != VK_SUCCESS) {
        std::cerr << "vkCreateInstance failed: " << result_name(result) << "\n";
        return EXIT_FAILURE;
    }

    std::uint32_t device_count = 0;
    result = vkEnumeratePhysicalDevices(instance, &device_count, nullptr);
    if (result != VK_SUCCESS) {
        std::cerr << "vkEnumeratePhysicalDevices(count) failed: "
                  << result_name(result) << "\n";
        vkDestroyInstance(instance, nullptr);
        return EXIT_FAILURE;
    }

    std::vector<VkPhysicalDevice> devices(device_count);
    if (device_count != 0) {
        result = vkEnumeratePhysicalDevices(instance, &device_count, devices.data());
        if (result != VK_SUCCESS) {
            std::cerr << "vkEnumeratePhysicalDevices(data) failed: "
                      << result_name(result) << "\n";
            vkDestroyInstance(instance, nullptr);
            return EXIT_FAILURE;
        }
    }

    std::cout << "{\n";
    std::cout << "  \"format\": \"SHIFT.VulkanProbe/1\",\n";
    std::cout << "  \"loader_api_version\": ["
              << VK_API_VERSION_MAJOR(loader_version) << ", "
              << VK_API_VERSION_MINOR(loader_version) << ", "
              << VK_API_VERSION_PATCH(loader_version) << "],\n";
    std::cout << "  \"physical_device_count\": " << device_count << ",\n";
    std::cout << "  \"devices\": [\n";

    for (std::uint32_t i = 0; i < device_count; ++i) {
        VkPhysicalDeviceProperties properties{};
        vkGetPhysicalDeviceProperties(devices[i], &properties);

        const bool queue_ok = has_graphics_or_compute_queue(devices[i]);

        std::cout << "    {\n";
        std::cout << "      \"index\": " << i << ",\n";
        std::cout << "      \"name\": \"" << properties.deviceName << "\",\n";
        std::cout << "      \"api_version\": ["
                  << VK_API_VERSION_MAJOR(properties.apiVersion) << ", "
                  << VK_API_VERSION_MINOR(properties.apiVersion) << ", "
                  << VK_API_VERSION_PATCH(properties.apiVersion) << "],\n";
        std::cout << "      \"vendor_id\": " << properties.vendorID << ",\n";
        std::cout << "      \"device_id\": " << properties.deviceID << ",\n";
        std::cout << "      \"graphics_or_compute_queue\": "
                  << (queue_ok ? "true" : "false") << "\n";
        std::cout << "    }" << (i + 1 == device_count ? "\n" : ",\n");
    }

    std::cout << "  ]\n";
    std::cout << "}\n";

    vkDestroyInstance(instance, nullptr);
    return EXIT_SUCCESS;
}
