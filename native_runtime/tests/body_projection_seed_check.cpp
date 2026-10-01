#include "shift_body_projection_seed.hpp"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {

double max_error(
    const std::array<double, 3>& actual,
    const std::array<double, 3>& expected) {

    double error = 0.0;
    for (std::size_t index = 0; index < actual.size(); ++index) {
        error = std::max(
            error,
            std::abs(actual[index] - expected[index]));
    }
    return error;
}

}  // namespace

int main() {
    try {
        using namespace shift::runtime::physics;

        BodyProjectionSeedInput input{};
        input.angular_state = {10.0, 20.0, 30.0};
        input.axis_state = {1.0, 2.0, 3.0};
        input.prepared_body_state = {4.0, 5.0, 6.0};
        input.linear_state = {2.0, -4.0, 8.0};
        input.inverse_scalar = 0.25;
        input.body_frame = {
            1.0f, 2.0f, 3.0f,
            4.0f, 5.0f, 6.0f,
            7.0f, 8.0f, 9.0f,
        };

        const BodyProjectionSeedResult result =
            build_body_projection_seed(input);

        double error = 0.0;
        error = std::max(
            error,
            max_error(result.residual, {13.0, 14.0, 33.0}));
        error = std::max(
            error,
            max_error(
                result.transformed_residual,
                {140.0, 320.0, 500.0}));
        error = std::max(
            error,
            max_error(result.scaled_linear, {0.5, -1.0, 2.0}));

        bool non_finite_rejected = false;
        try {
            BodyProjectionSeedInput invalid = input;
            invalid.angular_state[1] =
                std::numeric_limits<double>::quiet_NaN();
            (void)build_body_projection_seed(invalid);
        } catch (const std::runtime_error&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error(
                "non-finite BODY projection seed was accepted");
        }
        if (error > 1e-12) {
            throw std::runtime_error(
                "FUN_007bc680 projection seed parity mismatch");
        }

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeBodyProjectionSeedCheck/1\",\n"
            << "  \"source_function\": \""
            << kBodyProjectionSeedSourceFunction << "\",\n"
            << "  \"transform_function\": \""
            << kBodyProjectionSeedTransformFunction << "\",\n"
            << "  \"residual\": [13, 14, 33],\n"
            << "  \"transformed_residual\": [140, 320, 500],\n"
            << "  \"scaled_linear\": [0.5, -1, 2],\n"
            << "  \"max_error\": "
            << std::setprecision(17) << error << ",\n"
            << "  \"non_finite_rejected\": true,\n"
            << "  \"full_FUN_007bc680_implemented\": false,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_body_projection_seed_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
