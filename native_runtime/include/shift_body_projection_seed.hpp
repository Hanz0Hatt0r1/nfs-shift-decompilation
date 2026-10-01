#pragma once

#include <array>

namespace shift::runtime::physics {

inline constexpr const char* kBodyProjectionSeedSourceFunction =
    "FUN_007bc680";
inline constexpr const char* kBodyProjectionSeedTransformFunction =
    "FUN_007aefb0";

struct BodyProjectionSeedInput {
    std::array<double, 3> angular_state{};
    std::array<double, 3> axis_state{};
    std::array<double, 3> prepared_body_state{};
    std::array<double, 3> linear_state{};
    double inverse_scalar = 0.0;
    std::array<float, 9> body_frame{};
};

struct BodyProjectionSeedResult {
    std::array<double, 3> residual{};
    std::array<double, 3> transformed_residual{};
    std::array<double, 3> scaled_linear{};
};

BodyProjectionSeedResult build_body_projection_seed(
    const BodyProjectionSeedInput& input);

}  // namespace shift::runtime::physics
