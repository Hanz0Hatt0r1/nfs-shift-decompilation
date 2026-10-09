#pragma once

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// Platform-neutral live control state consumed by the runtime. Platform
// backends only translate native input events into these booleans; they do not
// own vehicle/physics state.
typedef struct ShiftPlatformInputState {
    uint8_t quit;
    uint8_t throttle;
    uint8_t brake;
    uint8_t steer_left;
    uint8_t steer_right;
} ShiftPlatformInputState;

#ifdef __cplusplus
}
#endif
