#pragma once

#include "shift_collision_query_contract.hpp"

#include <cmath>
#include <optional>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40QueryInputBoundaryFormat =
    "SHIFT.Fun00765c40QueryInputBoundary/1";

// Source-backed caller input immediately before FUN_00765c40 builds the
// seven-double FUN_007b0710 query record. The producer/coordinate transform for
// world_position remains deliberately external; this type only freezes the
// exact values the already-native collision-query contract needs.
struct Fun00765c40QueryInputBoundary {
    CollisionQueryVector3d world_position{};
    std::optional<std::uint64_t> cached_handle{};
    double miss_fallback = 0.0;  // source-visible caller state +0x38e8
};

inline void validate_fun_00765c40_query_input_boundary(
    const Fun00765c40QueryInputBoundary& input) {
    for (double value : input.world_position) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                "FUN_00765c40 query world position must be finite");
        }
    }
    if (!std::isfinite(input.miss_fallback)) {
        throw std::invalid_argument(
            "FUN_00765c40 query miss fallback must be finite");
    }
}

inline CollisionQueryRecord build_fun_00765c40_query_record(
    const Fun00765c40QueryInputBoundary& input) {
    validate_fun_00765c40_query_input_boundary(input);
    return build_fun_00765c40_collision_query_record(
        input.world_position,
        input.cached_handle);
}

inline double project_fun_00765c40_query_input_scalar(
    const Fun00765c40QueryInputBoundary& input,
    const CollisionQueryOutput& output) {
    validate_fun_00765c40_query_input_boundary(input);
    return project_fun_00765c40_query_scalar(
        input.world_position[1],
        output,
        input.miss_fallback);
}

}  // namespace shift::runtime::physics
