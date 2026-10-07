#pragma once

#include <cmath>
#include <cstddef>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun007675f0DistanceFilterCapSetupFormat =
    "SHIFT.Fun007675f0DistanceFilterCapSetup/1";
inline constexpr std::size_t kFun007675f0DistanceFilterCapOffset = 0xa0u;

// PC retail FUN_007675f0 passes this+0xa0 to FUN_00783a30 as the distance
// filter cap. The Xbox 360 counterpart independently reads +0xa0 from the same
// HDVehicle object that owns +0x4080 immediately before its corresponding
// low-pass helper call. Neither source proves the upstream initializer/value for
// the selected session, so keep the value explicit as one-time setup state and
// do not allow the per-pass provider to refresh it arbitrarily.
struct Fun007675f0DistanceFilterCapSetup {
    bool ready = false;
    double distance_filter_cap = 0.0;
};

inline void validate_fun_007675f0_distance_filter_cap_setup(
    const Fun007675f0DistanceFilterCapSetup& setup) {
    if (!setup.ready) {
        throw std::invalid_argument(
            "FUN_007675f0 distance filter cap requires explicit setup seed");
    }
    if (!std::isfinite(setup.distance_filter_cap)) {
        throw std::invalid_argument(
            "FUN_007675f0 distance filter cap setup seed must be finite");
    }
}

}  // namespace shift::runtime::physics
