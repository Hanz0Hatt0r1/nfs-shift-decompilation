#define VK_USE_PLATFORM_XCB_KHR 1
#include <vulkan/vulkan.h>

#include "shift_vulkan_surface_backend.h"
#include "shift_xcb_surface_probe.h"

namespace {

struct XcbSurfaceContext {
    xcb_connection_t* connection = nullptr;
    xcb_window_t window = XCB_WINDOW_NONE;
};

VkResult create_xcb_surface(
    void* raw_context,
    VkInstance instance,
    VkSurfaceKHR* out_surface) {
    auto* context = static_cast<XcbSurfaceContext*>(raw_context);
    if (context == nullptr || context->connection == nullptr ||
        context->window == XCB_WINDOW_NONE || out_surface == nullptr) {
        return VK_ERROR_INITIALIZATION_FAILED;
    }

    VkXcbSurfaceCreateInfoKHR create{};
    create.sType = VK_STRUCTURE_TYPE_XCB_SURFACE_CREATE_INFO_KHR;
    create.connection = context->connection;
    create.window = context->window;
    return vkCreateXcbSurfaceKHR(instance, &create, nullptr, out_surface);
}

}  // namespace

extern "C" int shift_xcb_vulkan_surface_probe(
    xcb_connection_t* connection,
    xcb_window_t window) {
    if (connection == nullptr || window == XCB_WINDOW_NONE) {
        return SHIFT_VULKAN_SURFACE_PROBE_INVALID_BACKEND;
    }

    const char* extensions[] = {
        VK_KHR_SURFACE_EXTENSION_NAME,
        VK_KHR_XCB_SURFACE_EXTENSION_NAME,
    };
    XcbSurfaceContext context{connection, window};
    ShiftVulkanSurfaceBackend backend{};
    backend.backend_name = "SHIFT XCB Vulkan Surface";
    backend.required_instance_extensions = extensions;
    backend.required_instance_extension_count = 2u;
    backend.context = &context;
    backend.create_surface = create_xcb_surface;
    return shift_vulkan_surface_probe_backend(&backend);
}
