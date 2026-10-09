#define VK_USE_PLATFORM_ANDROID_KHR 1
#include <vulkan/vulkan.h>

#include "shift_android_surface_probe.h"
#include "shift_vulkan_surface_backend.h"

namespace {

VkResult create_android_surface(
    void* raw_context,
    VkInstance instance,
    VkSurfaceKHR* out_surface) {
    auto* window = static_cast<ANativeWindow*>(raw_context);
    if (window == nullptr || out_surface == nullptr) {
        return VK_ERROR_INITIALIZATION_FAILED;
    }

    VkAndroidSurfaceCreateInfoKHR create{};
    create.sType = VK_STRUCTURE_TYPE_ANDROID_SURFACE_CREATE_INFO_KHR;
    create.window = window;
    return vkCreateAndroidSurfaceKHR(instance, &create, nullptr, out_surface);
}

}  // namespace

extern "C" int shift_android_vulkan_surface_probe(ANativeWindow* window) {
    if (window == nullptr) {
        return SHIFT_VULKAN_SURFACE_PROBE_INVALID_BACKEND;
    }

    const char* extensions[] = {
        VK_KHR_SURFACE_EXTENSION_NAME,
        VK_KHR_ANDROID_SURFACE_EXTENSION_NAME,
    };
    ShiftVulkanSurfaceBackend backend{};
    backend.backend_name = "SHIFT Android Vulkan Surface";
    backend.required_instance_extensions = extensions;
    backend.required_instance_extension_count = 2u;
    backend.context = window;
    backend.create_surface = create_android_surface;
    return shift_vulkan_surface_probe_backend(&backend);
}
