#pragma once

#include <array>

namespace shift::runtime::physics {

struct BodyPreProjectionInput {
    std::array<double, 3> body_correction{};
    std::array<double, 3> body_axis{};
    std::array<double, 3> angular_state{};
    std::array<double, 3> linear_state{};
    double inverse_scalar = 0.0;
    std::array<float, 9> body_frame{};
};

struct BodyPreProjectionResult {
    std::array<double, 3> residual{};
    std::array<double, 3> transformed_residual{};
    std::array<double, 3> scaled_linear{};
};

BodyPreProjectionResult evaluate_fun_007bc680_preprojection(
    const BodyPreProjectionInput& input);

}  // namespace shift::runtime::physics
