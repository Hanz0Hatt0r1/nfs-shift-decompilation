#define VK_USE_PLATFORM_ANDROID_KHR 1
#include <vulkan/vulkan.h>

#include "shift_android_surface_probe.h"

#include <cstdint>
#include <vector>

namespace {

constexpr int kInvalidWindow = 2;
constexpr int kInstanceFailure = 3;
constexpr int kSurfaceFailure = 4;
constexpr int kPhysicalDeviceFailure = 5;
constexpr int kQueueFamilyFailure = 6;

}  // namespace

extern "C" int shift_android_vulkan_surface_probe(ANativeWindow* window) {
    if (window == nullptr) {
        return kInvalidWindow;
    }

    const char* instance_extensions[] = {
        VK_KHR_SURFACE_EXTENSION_NAME,
        VK_KHR_ANDROID_SURFACE_EXTENSION_NAME,
    };

    VkApplicationInfo app{};
    app.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
    app.pApplicationName = "SHIFT Android Vulkan Surface Probe";
    app.applicationVersion = 1;
    app.pEngineName = "SHIFT";
    app.engineVersion = 1;
    app.apiVersion = VK_API_VERSION_1_0;

    VkInstanceCreateInfo instance_create{};
    instance_create.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    instance_create.pApplicationInfo = &app;
    instance_create.enabledExtensionCount = 2;
    instance_create.ppEnabledExtensionNames = instance_extensions;

    VkInstance instance = VK_NULL_HANDLE;
    if (vkCreateInstance(&instance_create, nullptr, &instance) != VK_SUCCESS) {
        return kInstanceFailure;
    }

    VkAndroidSurfaceCreateInfoKHR surface_create{};
    surface_create.sType = VK_STRUCTURE_TYPE_ANDROID_SURFACE_CREATE_INFO_KHR;
    surface_create.window = window;

    VkSurfaceKHR surface = VK_NULL_HANDLE;
    if (vkCreateAndroidSurfaceKHR(
            instance, &surface_create, nullptr, &surface) != VK_SUCCESS) {
        vkDestroyInstance(instance, nullptr);
        return kSurfaceFailure;
    }

    uint32_t device_count = 0;
    VkResult enumerate_result =
        vkEnumeratePhysicalDevices(instance, &device_count, nullptr);
    if (enumerate_result != VK_SUCCESS || device_count == 0) {
        vkDestroySurfaceKHR(instance, surface, nullptr);
        vkDestroyInstance(instance, nullptr);
        return kPhysicalDeviceFailure;
    }

    std::vector<VkPhysicalDevice> devices(device_count);
    enumerate_result =
        vkEnumeratePhysicalDevices(instance, &device_count, devices.data());
    if (enumerate_result != VK_SUCCESS) {
        vkDestroySurfaceKHR(instance, surface, nullptr);
        vkDestroyInstance(instance, nullptr);
        return kPhysicalDeviceFailure;
    }

    bool compatible_queue = false;
    for (VkPhysicalDevice physical : devices) {
        uint32_t queue_count = 0;
        vkGetPhysicalDeviceQueueFamilyProperties(
            physical, &queue_count, nullptr);
        std::vector<VkQueueFamilyProperties> queues(queue_count);
        vkGetPhysicalDeviceQueueFamilyProperties(
            physical, &queue_count, queues.data());

        for (uint32_t index = 0; index < queue_count; ++index) {
            if ((queues[index].queueFlags & VK_QUEUE_GRAPHICS_BIT) == 0u) {
                continue;
            }
            VkBool32 present = VK_FALSE;
            if (vkGetPhysicalDeviceSurfaceSupportKHR(
                    physical, index, surface, &present) == VK_SUCCESS &&
                present == VK_TRUE) {
                compatible_queue = true;
                break;
            }
        }
        if (compatible_queue) {
            break;
        }
    }

    vkDestroySurfaceKHR(instance, surface, nullptr);
    vkDestroyInstance(instance, nullptr);
    return compatible_queue ? 0 : kQueueFamilyFailure;
}
