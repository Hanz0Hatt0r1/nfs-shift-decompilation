#pragma once

#include <cmath>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun007675f0DistanceStateSetupFormat =
    "SHIFT.Fun007675f0DistanceStateSetup/1";

// PC retail FUN_007675f0 reads HDVehicle+0x4080 as the previous value passed to
// FUN_00783a30, then writes the newly filtered/clamped distance state back to
// the same field. The upstream setup initializer is not yet proven for the
// selected session, so keep only that one-time seed explicit; per-pass refresh
// belongs to the native session.
struct Fun007675f0DistanceStateSetup {
    bool ready = false;
    double previous_distance_state = 0.0;
};

inline void validate_fun_007675f0_distance_state_setup(
    const Fun007675f0DistanceStateSetup& setup) {
    if (!setup.ready) {
        throw std::invalid_argument(
            "FUN_007675f0 distance state requires explicit setup seed");
    }
    if (!std::isfinite(setup.previous_distance_state)) {
        throw std::invalid_argument(
            "FUN_007675f0 distance state setup seed must be finite");
    }
}

}  // namespace shift::runtime::physics
