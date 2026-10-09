#define VK_USE_PLATFORM_XCB_KHR 1
#include <vulkan/vulkan.h>

#include "shift_vulkan_surface_backend.h"
#include "shift_xcb_surface_probe.h"
#include "shift_xcb_window.h"

#include <cstdlib>
#include <new>

struct ShiftXcbWindow {
    xcb_connection_t* connection = nullptr;
    xcb_window_t window = XCB_WINDOW_NONE;
};

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

bool check_void_cookie(
    xcb_connection_t* connection,
    xcb_void_cookie_t cookie) {
    xcb_generic_error_t* error = xcb_request_check(connection, cookie);
    if (error == nullptr) {
        return true;
    }
    std::free(error);
    return false;
}

void destroy_native_window(ShiftXcbWindow* window) {
    if (window == nullptr || window->connection == nullptr) {
        return;
    }
    if (window->window != XCB_WINDOW_NONE) {
        xcb_destroy_window(window->connection, window->window);
        window->window = XCB_WINDOW_NONE;
    }
    xcb_disconnect(window->connection);
    window->connection = nullptr;
}

}  // namespace

extern "C" int shift_xcb_window_create(
    uint16_t width,
    uint16_t height,
    ShiftXcbWindow** out_window) {
    if (out_window == nullptr || width == 0u || height == 0u) {
        return SHIFT_XCB_WINDOW_INVALID_ARGUMENT;
    }
    *out_window = nullptr;

    int screen_index = 0;
    xcb_connection_t* connection = xcb_connect(nullptr, &screen_index);
    if (connection == nullptr || xcb_connection_has_error(connection)) {
        if (connection != nullptr) {
            xcb_disconnect(connection);
        }
        return SHIFT_XCB_WINDOW_CONNECT_FAILURE;
    }

    const xcb_setup_t* setup = xcb_get_setup(connection);
    xcb_screen_iterator_t screen_it = xcb_setup_roots_iterator(setup);
    for (int index = 0; index < screen_index && screen_it.rem; ++index) {
        xcb_screen_next(&screen_it);
    }
    if (!screen_it.rem || screen_it.data == nullptr) {
        xcb_disconnect(connection);
        return SHIFT_XCB_WINDOW_SCREEN_FAILURE;
    }

    const xcb_screen_t* screen = screen_it.data;
    const xcb_window_t native_window = xcb_generate_id(connection);
    const uint32_t event_mask =
        XCB_EVENT_MASK_EXPOSURE |
        XCB_EVENT_MASK_STRUCTURE_NOTIFY |
        XCB_EVENT_MASK_KEY_PRESS |
        XCB_EVENT_MASK_KEY_RELEASE;
    const uint32_t values[] = {
        screen->black_pixel,
        event_mask,
    };

    const xcb_void_cookie_t create_cookie = xcb_create_window_checked(
        connection,
        XCB_COPY_FROM_PARENT,
        native_window,
        screen->root,
        0,
        0,
        width,
        height,
        0,
        XCB_WINDOW_CLASS_INPUT_OUTPUT,
        screen->root_visual,
        XCB_CW_BACK_PIXEL | XCB_CW_EVENT_MASK,
        values);
    if (!check_void_cookie(connection, create_cookie)) {
        xcb_disconnect(connection);
        return SHIFT_XCB_WINDOW_CREATE_FAILURE;
    }

    const xcb_void_cookie_t map_cookie =
        xcb_map_window_checked(connection, native_window);
    if (!check_void_cookie(connection, map_cookie) || xcb_flush(connection) <= 0) {
        xcb_destroy_window(connection, native_window);
        xcb_disconnect(connection);
        return SHIFT_XCB_WINDOW_CREATE_FAILURE;
    }

    auto* result = new (std::nothrow) ShiftXcbWindow{};
    if (result == nullptr) {
        xcb_destroy_window(connection, native_window);
        xcb_disconnect(connection);
        return SHIFT_XCB_WINDOW_CREATE_FAILURE;
    }
    result->connection = connection;
    result->window = native_window;
    *out_window = result;
    return SHIFT_XCB_WINDOW_OK;
}

extern "C" void shift_xcb_window_destroy(ShiftXcbWindow* window) {
    if (window == nullptr) {
        return;
    }
    destroy_native_window(window);
    delete window;
}

extern "C" int shift_xcb_window_poll(
    ShiftXcbWindow* window,
    ShiftPlatformInputState* input) {
    if (window == nullptr || window->connection == nullptr || input == nullptr) {
        return SHIFT_XCB_WINDOW_INVALID_ARGUMENT;
    }
    if (xcb_connection_has_error(window->connection)) {
        return SHIFT_XCB_WINDOW_CONNECT_FAILURE;
    }

    while (xcb_generic_event_t* raw = xcb_poll_for_event(window->connection)) {
        const uint8_t type = raw->response_type & 0x7fu;
        if (type == XCB_KEY_PRESS || type == XCB_KEY_RELEASE) {
            const auto* event =
                reinterpret_cast<const xcb_key_press_event_t*>(raw);
            const uint8_t pressed = type == XCB_KEY_PRESS ? 1u : 0u;
            switch (event->detail) {
                case 9:   // Escape
                case 24:  // Q
                    if (pressed) input->quit = 1u;
                    break;
                case 111: // Up
                case 25:  // W
                    input->throttle = pressed;
                    break;
                case 116: // Down
                case 39:  // S
                    input->brake = pressed;
                    break;
                case 113: // Left
                case 38:  // A
                    input->steer_left = pressed;
                    break;
                case 114: // Right
                case 40:  // D
                    input->steer_right = pressed;
                    break;
                default:
                    break;
            }
        } else if (type == XCB_DESTROY_NOTIFY) {
            input->quit = 1u;
        }
        std::free(raw);
    }
    return SHIFT_XCB_WINDOW_OK;
}

extern "C" xcb_connection_t* shift_xcb_window_connection(
    const ShiftXcbWindow* window) {
    return window == nullptr ? nullptr : window->connection;
}

extern "C" xcb_window_t shift_xcb_window_id(const ShiftXcbWindow* window) {
    return window == nullptr ? XCB_WINDOW_NONE : window->window;
}

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
