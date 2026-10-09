#pragma once

#include <android/native_activity.h>

#ifdef __cplusplus
extern "C" {
#endif

// NativeActivity entry point exported by the Android shared library.
void ANativeActivity_onCreate(
    ANativeActivity* activity,
    void* saved_state,
    size_t saved_state_size);

// Returns the latest platform-surface probe status recorded by the activity.
// A missing activity/state or a destroyed native window returns the same
// fail-closed invalid-backend status used by the common Vulkan surface layer.
int shift_android_activity_last_surface_probe_status(
    const ANativeActivity* activity);

#ifdef __cplusplus
}
#endif
