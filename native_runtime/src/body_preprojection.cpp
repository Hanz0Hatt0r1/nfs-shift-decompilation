#include "shift_body_preprojection.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {
namespace {

template <typename Range>
void require_finite(const Range& values, const char* label) {
    for (const auto value : values) {
        if (!std::isfinite(static_cast<double>(value))) {
            throw std::invalid_argument(
                std::string(label) + " contains non-finite value");
        }
    }
}

}  // namespace

BodyPreProjectionResult evaluate_fun_007bc680_preprojection(
    const BodyPreProjectionInput& input) {

    require_finite(input.body_correction, "BODY +0x30/+0x38/+0x40");
    require_finite(input.body_axis, "BODY +0x18/+0x20/+0x28");
    require_finite(input.angular_state, "BODY +0x48/+0x50/+0x58");
    require_finite(input.linear_state, "BODY +0x60/+0x68/+0x70");
    require_finite(input.body_frame, "BODY frame +0xb0");
    if (!std::isfinite(input.inverse_scalar)) {
        throw std::invalid_argument(
            "BODY +0x90 contains non-finite value");
    }

    const double c0 = input.body_correction[0];
    const double c1 = input.body_correction[1];
    const double c2 = input.body_correction[2];
    const double a0 = input.body_axis[0];
    const double a1 = input.body_axis[1];
    const double a2 = input.body_axis[2];

    BodyPreProjectionResult result{};
    result.residual[0] =
        input.angular_state[0] -
        (c2 * a1 - c1 * a2);
    result.residual[1] =
        input.angular_state[1] -
        (c0 * a2 - c2 * a0);
    result.residual[2] =
        input.angular_state[2] -
        (c1 * a0 - c0 * a1);

    const float x = static_cast<float>(result.residual[0]);
    const float y = static_cast<float>(result.residual[1]);
    const float z = static_cast<float>(result.residual[2]);
    const auto& m = input.body_frame;

    // Exact FUN_007aefb0 coefficient and operation ordering.
    result.transformed_residual[0] = static_cast<double>(
        m[2] * z + m[0] * x + m[1] * y);
    result.transformed_residual[1] = static_cast<double>(
        m[5] * z + m[4] * y + m[3] * x);
    result.transformed_residual[2] = static_cast<double>(
        m[8] * z + m[7] * y + m[6] * x);

    result.scaled_linear[0] =
        input.linear_state[0] * input.inverse_scalar;
    result.scaled_linear[1] =
        input.linear_state[1] * input.inverse_scalar;
    result.scaled_linear[2] =
        input.linear_state[2] * input.inverse_scalar;

    require_finite(result.residual, "FUN_007bc680 residual");
    require_finite(
        result.transformed_residual,
        "FUN_007bc680 transformed residual");
    require_finite(result.scaled_linear, "FUN_007bc680 scaled linear");
    return result;
}

}  // namespace shift::runtime::physics
