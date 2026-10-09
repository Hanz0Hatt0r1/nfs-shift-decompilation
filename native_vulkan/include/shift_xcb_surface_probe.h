#pragma once

#include <xcb/xcb.h>

#ifdef __cplusplus
extern "C" {
#endif

// Returns 0 only when the supplied XCB window can be promoted to a Vulkan
// surface with a graphics+present queue family. The caller retains ownership
// of both the XCB connection and window.
int shift_xcb_vulkan_surface_probe(
    xcb_connection_t* connection,
    xcb_window_t window);

#ifdef __cplusplus
}
#endif
