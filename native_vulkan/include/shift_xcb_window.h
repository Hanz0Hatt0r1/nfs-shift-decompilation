#pragma once

#include <stdint.h>
#include <xcb/xcb.h>

#include "shift_platform_input.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct ShiftXcbWindow ShiftXcbWindow;

enum ShiftXcbWindowStatus {
    SHIFT_XCB_WINDOW_OK = 0,
    SHIFT_XCB_WINDOW_INVALID_ARGUMENT = 2,
    SHIFT_XCB_WINDOW_CONNECT_FAILURE = 3,
    SHIFT_XCB_WINDOW_SCREEN_FAILURE = 4,
    SHIFT_XCB_WINDOW_CREATE_FAILURE = 5,
};

// Creates and maps an XCB window. The returned object owns its XCB connection
// and native window until shift_xcb_window_destroy().
int shift_xcb_window_create(
    uint16_t width,
    uint16_t height,
    ShiftXcbWindow** out_window);

void shift_xcb_window_destroy(ShiftXcbWindow* window);

// Polls pending XCB events and updates the supplied platform-neutral state.
// Key mappings intentionally preserve the current Linux runtime controls:
// Escape/Q quit, Up/W throttle, Down/S brake, Left/A and Right/D steering.
int shift_xcb_window_poll(
    ShiftXcbWindow* window,
    ShiftPlatformInputState* input);

// Borrowed native handles for Vulkan surface creation. Ownership remains with
// ShiftXcbWindow and callers must not disconnect/destroy them.
xcb_connection_t* shift_xcb_window_connection(const ShiftXcbWindow* window);
xcb_window_t shift_xcb_window_id(const ShiftXcbWindow* window);

#ifdef __cplusplus
}
#endif
