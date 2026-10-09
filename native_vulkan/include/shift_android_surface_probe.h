#pragma once

#ifdef __ANDROID__
#include <android/native_window.h>
#else
struct ANativeWindow;
#endif

#ifdef __cplusplus
extern "C" {
#endif

// Returns 0 only when an Android native window can be promoted to a Vulkan
// surface and at least one physical-device queue family supports both graphics
// and presentation to that surface. Non-zero values are fail-closed diagnostics.
int shift_android_vulkan_surface_probe(ANativeWindow* window);

#ifdef __cplusplus
}
#endif
