#include "shift_android_native_activity.h"

#include "shift_android_surface_probe.h"
#include "shift_vulkan_surface_backend.h"

#include <android/log.h>
#include <android/native_window.h>

#include <new>

namespace {

constexpr const char* kLogTag = "SHIFT.NativeActivity";

struct AndroidActivityState {
    int last_surface_probe_status = SHIFT_VULKAN_SURFACE_PROBE_INVALID_BACKEND;
    bool native_window_ready = false;
};

AndroidActivityState* state_from(ANativeActivity* activity) {
    return activity == nullptr
        ? nullptr
        : static_cast<AndroidActivityState*>(activity->instance);
}

const AndroidActivityState* state_from(const ANativeActivity* activity) {
    return activity == nullptr
        ? nullptr
        : static_cast<const AndroidActivityState*>(activity->instance);
}

void on_native_window_created(
    ANativeActivity* activity,
    ANativeWindow* window) {
    AndroidActivityState* state = state_from(activity);
    if (state == nullptr || window == nullptr) {
        if (state != nullptr) {
            state->native_window_ready = false;
            state->last_surface_probe_status =
                SHIFT_VULKAN_SURFACE_PROBE_INVALID_BACKEND;
        }
        return;
    }

    state->native_window_ready = true;
    state->last_surface_probe_status =
        shift_android_vulkan_surface_probe(window);
    __android_log_print(
        state->last_surface_probe_status == SHIFT_VULKAN_SURFACE_PROBE_OK
            ? ANDROID_LOG_INFO
            : ANDROID_LOG_ERROR,
        kLogTag,
        "ANativeWindow Vulkan surface probe status=%d",
        state->last_surface_probe_status);
}

void on_native_window_destroyed(
    ANativeActivity* activity,
    ANativeWindow*) {
    AndroidActivityState* state = state_from(activity);
    if (state == nullptr) {
        return;
    }
    state->native_window_ready = false;
    state->last_surface_probe_status =
        SHIFT_VULKAN_SURFACE_PROBE_INVALID_BACKEND;
}

void on_activity_destroy(ANativeActivity* activity) {
    if (activity == nullptr) {
        return;
    }
    delete state_from(activity);
    activity->instance = nullptr;
}

}  // namespace

extern "C" void ANativeActivity_onCreate(
    ANativeActivity* activity,
    void*,
    size_t) {
    if (activity == nullptr || activity->callbacks == nullptr) {
        return;
    }

    auto* state = new (std::nothrow) AndroidActivityState{};
    if (state == nullptr) {
        __android_log_print(
            ANDROID_LOG_FATAL,
            kLogTag,
            "failed to allocate NativeActivity state");
        return;
    }

    activity->instance = state;
    activity->callbacks->onNativeWindowCreated = on_native_window_created;
    activity->callbacks->onNativeWindowDestroyed = on_native_window_destroyed;
    activity->callbacks->onDestroy = on_activity_destroy;
}

extern "C" int shift_android_activity_last_surface_probe_status(
    const ANativeActivity* activity) {
    const AndroidActivityState* state = state_from(activity);
    if (state == nullptr || !state->native_window_ready) {
        return SHIFT_VULKAN_SURFACE_PROBE_INVALID_BACKEND;
    }
    return state->last_surface_probe_status;
}
