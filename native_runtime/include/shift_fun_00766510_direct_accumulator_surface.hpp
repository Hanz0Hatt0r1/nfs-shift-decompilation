#pragma once

#include "shift_body_accumulator_primitives.hpp"

#include <array>
#include <cmath>
#include <cstddef>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00766510DirectAccumulatorSurfaceFormat =
    "SHIFT.Fun00766510DirectAccumulatorSurface/1";

inline constexpr std::array<std::size_t, 3>
    kFun00766510CallerAccumulatorOffsets = {0x40a0u, 0x40a8u, 0x40b0u};
inline constexpr std::size_t kFun00766510DirectAccumulatorSiteCount = 4u;

struct Fun00766510DirectAccumulatorSite {
    const char* id = nullptr;
    std::size_t source_line = 0u;
    bool conditional = false;
};

inline constexpr std::array<Fun00766510DirectAccumulatorSite,
                            kFun00766510DirectAccumulatorSiteCount>
    kFun00766510DirectAccumulatorSites = {{
        {"early_3b20", 759558u, true},
        {"optional_3c60", 759621u, true},
        {"primary_3950", 759692u, false},
        {"later_3a40", 759732u, true},
    }};

inline void apply_fun_00766510_direct_accumulator_delta(
    BodyAccumulatorVector3d& accumulator,
    const BodyAccumulatorVector3d& source_computed_delta) {
    for (const double value : accumulator) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                "FUN_00766510 caller accumulator must be finite");
        }
    }
    for (const double value : source_computed_delta) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                "FUN_00766510 direct accumulator delta must be finite");
        }
    }

    // This helper models one proven direct caller write at its original
    // scheduling point. It deliberately does not batch/reorder all four direct
    // sites because two FUN_00758fc0 contributions and a final transformed
    // vector contribution remain interleaved in the unresolved P1.1c schedule.
    accumulator[0] += source_computed_delta[0];
    accumulator[1] += source_computed_delta[1];
    accumulator[2] += source_computed_delta[2];
}

}  // namespace shift::runtime::physics
