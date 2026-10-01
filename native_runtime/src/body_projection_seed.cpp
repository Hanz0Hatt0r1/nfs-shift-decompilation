#include "shift_body_projection_seed.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {
namespace {

void require_finite(double value, const char* label) {
    if (!std::isfinite(value)) {
        throw std::runtime_error(
            std::string("FUN_007bc680 non-finite ") + label);
    }
}

void require_finite(float value, const char* label) {
    if (!std::isfinite(value)) {
        throw std::runtime_error(
            std::string("FUN_007bc680 non-finite ") + label);
    }
}

std::array<double, 3> transform_fun_007aefb0(
    const std::array<float, 9>& matrix,
    const std::array<double, 3>& vector) {

    const float x = static_cast<float>(vector[0]);
    const float y = static_cast<float>(vector[1]);
    const float z = static_cast<float>(vector[2]);

    const float out_x =
        matrix[2] * z + matrix[0] * x + matrix[1] * y;
    const float out_y =
        matrix[5] * z + matrix[4] * y + matrix[3] * x;
    const float out_z =
        matrix[8] * z + matrix[7] * y + matrix[6] * x;

    return {
        static_cast<double>(out_x),
        static_cast<double>(out_y),
        static_cast<double>(out_z),
    };
}

}  // namespace

BodyProjectionSeedResult build_body_projection_seed(
    const BodyProjectionSeedInput& input) {

    for (double value : input.angular_state) {
        require_finite(value, "angular state");
    }
    for (double value : input.axis_state) {
        require_finite(value, "axis state");
    }
    for (double value : input.prepared_body_state) {
        require_finite(value, "prepared body state");
    }
    for (double value : input.linear_state) {
        require_finite(value, "linear state");
    }
    require_finite(input.inverse_scalar, "inverse scalar");
    for (float value : input.body_frame) {
        require_finite(value, "body frame");
    }

    BodyProjectionSeedResult result{};
    result.residual = {
        input.angular_state[0] -
            (
                input.prepared_body_state[2] * input.axis_state[1] -
                input.prepared_body_state[1] * input.axis_state[2]
            ),
        input.angular_state[1] -
            (
                input.prepared_body_state[0] * input.axis_state[2] -
                input.prepared_body_state[2] * input.axis_state[0]
            ),
        input.angular_state[2] -
            (
                input.prepared_body_state[1] * input.axis_state[0] -
                input.prepared_body_state[0] * input.axis_state[1]
            ),
    };

    for (double value : result.residual) {
        require_finite(value, "residual");
    }

    result.transformed_residual =
        transform_fun_007aefb0(
            input.body_frame,
            result.residual);

    result.scaled_linear = {
        input.linear_state[0] * input.inverse_scalar,
        input.linear_state[1] * input.inverse_scalar,
        input.linear_state[2] * input.inverse_scalar,
    };
    for (double value : result.scaled_linear) {
        require_finite(value, "scaled linear state");
    }
    return result;
}

}  // namespace shift::runtime::physics
