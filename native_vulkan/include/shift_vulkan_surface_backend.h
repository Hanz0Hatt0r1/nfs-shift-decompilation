#pragma once

#include <stdint.h>
#include <vulkan/vulkan.h>

#ifdef __cplusplus
extern "C" {
#endif

// Platform-neutral surface creation contract.
//
// The caller owns `context` and every native handle reachable through it. The
// backend callback creates one VkSurfaceKHR for the supplied VkInstance. On
// success the common probe owns and destroys that surface; the callback must
// not destroy the VkInstance, the native handle, or the returned surface.
typedef VkResult (*ShiftVulkanCreateSurfaceFn)(
    void* context,
    VkInstance instance,
    VkSurfaceKHR* out_surface);

typedef struct ShiftVulkanSurfaceBackend {
    const char* backend_name;
    const char* const* required_instance_extensions;
    uint32_t required_instance_extension_count;
    void* context;
    ShiftVulkanCreateSurfaceFn create_surface;
} ShiftVulkanSurfaceBackend;

enum ShiftVulkanSurfaceProbeStatus {
    SHIFT_VULKAN_SURFACE_PROBE_OK = 0,
    SHIFT_VULKAN_SURFACE_PROBE_INVALID_BACKEND = 2,
    SHIFT_VULKAN_SURFACE_PROBE_INSTANCE_FAILURE = 3,
    SHIFT_VULKAN_SURFACE_PROBE_SURFACE_FAILURE = 4,
    SHIFT_VULKAN_SURFACE_PROBE_PHYSICAL_DEVICE_FAILURE = 5,
    SHIFT_VULKAN_SURFACE_PROBE_QUEUE_FAMILY_FAILURE = 6,
};

// Creates a Vulkan instance from the backend-declared extension set, asks the
// backend to create a surface, and proves that at least one physical-device
// queue family supports both graphics and presentation. Returns a fail-closed
// ShiftVulkanSurfaceProbeStatus value.
int shift_vulkan_surface_probe_backend(
    const ShiftVulkanSurfaceBackend* backend);

#ifdef __cplusplus
}
#endif
