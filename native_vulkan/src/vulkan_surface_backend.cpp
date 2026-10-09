#include "shift_vulkan_surface_backend.h"

#include <vector>

extern "C" int shift_vulkan_surface_probe_backend(
    const ShiftVulkanSurfaceBackend* backend) {
    if (backend == nullptr || backend->backend_name == nullptr ||
        backend->required_instance_extensions == nullptr ||
        backend->required_instance_extension_count == 0u ||
        backend->create_surface == nullptr) {
        return SHIFT_VULKAN_SURFACE_PROBE_INVALID_BACKEND;
    }

    VkApplicationInfo app{};
    app.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
    app.pApplicationName = backend->backend_name;
    app.applicationVersion = 1;
    app.pEngineName = "SHIFT";
    app.engineVersion = 1;
    app.apiVersion = VK_API_VERSION_1_0;

    VkInstanceCreateInfo instance_create{};
    instance_create.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    instance_create.pApplicationInfo = &app;
    instance_create.enabledExtensionCount =
        backend->required_instance_extension_count;
    instance_create.ppEnabledExtensionNames =
        backend->required_instance_extensions;

    VkInstance instance = VK_NULL_HANDLE;
    if (vkCreateInstance(&instance_create, nullptr, &instance) != VK_SUCCESS) {
        return SHIFT_VULKAN_SURFACE_PROBE_INSTANCE_FAILURE;
    }

    VkSurfaceKHR surface = VK_NULL_HANDLE;
    const VkResult surface_result =
        backend->create_surface(backend->context, instance, &surface);
    if (surface_result != VK_SUCCESS || surface == VK_NULL_HANDLE) {
        vkDestroyInstance(instance, nullptr);
        return SHIFT_VULKAN_SURFACE_PROBE_SURFACE_FAILURE;
    }

    uint32_t device_count = 0;
    VkResult enumerate_result =
        vkEnumeratePhysicalDevices(instance, &device_count, nullptr);
    if (enumerate_result != VK_SUCCESS || device_count == 0u) {
        vkDestroySurfaceKHR(instance, surface, nullptr);
        vkDestroyInstance(instance, nullptr);
        return SHIFT_VULKAN_SURFACE_PROBE_PHYSICAL_DEVICE_FAILURE;
    }

    std::vector<VkPhysicalDevice> devices(device_count);
    enumerate_result =
        vkEnumeratePhysicalDevices(instance, &device_count, devices.data());
    if (enumerate_result != VK_SUCCESS) {
        vkDestroySurfaceKHR(instance, surface, nullptr);
        vkDestroyInstance(instance, nullptr);
        return SHIFT_VULKAN_SURFACE_PROBE_PHYSICAL_DEVICE_FAILURE;
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
    return compatible_queue
        ? SHIFT_VULKAN_SURFACE_PROBE_OK
        : SHIFT_VULKAN_SURFACE_PROBE_QUEUE_FAMILY_FAILURE;
}
