#pragma once

#include "shift_fun_00765c40_residual_pass_contract.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40WheelPairRefreshFormat =
    "SHIFT.Fun00765c40WheelPairRefresh/1";

inline constexpr std::size_t kFun00765c40WheelPairCount = 4u;
inline constexpr std::size_t kFun00765c40WheelPairStride = 0x0a80u;

struct Fun00765c40WheelPairRefreshInputs {
    double state_plus_8 = 0.0;
    double state_plus_28 = 0.0;
    double sqrt_lane = 0.0;
};

using Fun00765c40WheelPairRefreshState =
    std::array<std::array<double, 2>, kFun00765c40WheelPairCount>;

inline float clamp_fun_00765c40_pair_source(double value) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(
            "FUN_00765c40 wheel-pair source must be finite");
    }
    const float narrowed = static_cast<float>(value);
    if (!std::isfinite(narrowed)) {
        throw std::invalid_argument(
            "FUN_00765c40 wheel-pair float narrowing overflow");
    }
    if (narrowed <= 0.0f) {
        return 0.0f;
    }
    if (narrowed >= 1.0f) {
        return 1.0f;
    }
    return narrowed;
}

inline Fun00765c40WheelPairRefreshState
materialize_fun_00765c40_wheel_pair_refresh(
    const Fun00765c40WheelPairRefreshInputs& inputs) {
    if (!std::isfinite(inputs.sqrt_lane)) {
        throw std::invalid_argument(
            "FUN_00765c40 unresolved sqrt lane must be finite");
    }

    const float source_a =
        clamp_fun_00765c40_pair_source(inputs.state_plus_8);
    const float source_b =
        clamp_fun_00765c40_pair_source(inputs.state_plus_28);
    const float selected = std::max(source_a, source_b);
    const double first_lane = static_cast<double>(selected * 100.0f);

    Fun00765c40WheelPairRefreshState state{};
    for (auto& pair : state) {
        pair[0] = first_lane;
        pair[1] = inputs.sqrt_lane;
    }
    return state;
}

}  // namespace shift::runtime::physics
