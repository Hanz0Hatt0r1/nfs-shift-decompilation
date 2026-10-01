#include "shift_body_preprojection.hpp"

#include <algorithm>
#include <array>
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

    double result = 0.0;
    for (std::size_t index = 0; index < actual.size(); ++index) {
        result = std::max(
            result,
            std::abs(actual[index] - expected[index]));
    }
    return result;
}

void require_close(
    const std::array<double, 3>& actual,
    const std::array<double, 3>& expected,
    double tolerance,
    const char* label,
    double& observed_max) {

    observed_max = std::max(
        observed_max,
        max_error(actual, expected));
    if (max_error(actual, expected) > tolerance) {
        throw std::runtime_error(
            std::string(label) + " mismatch");
    }
}

}  // namespace

int main() {
    try {
        using namespace shift::runtime::physics;
        double max_absolute_error = 0.0;

        BodyPreProjectionInput identity{};
        identity.body_correction = {1.0, 2.0, 3.0};
        identity.body_axis = {4.0, 5.0, 6.0};
        identity.angular_state = {10.0, 20.0, 30.0};
        identity.linear_state = {2.0, 4.0, 6.0};
        identity.inverse_scalar = 0.5;
        identity.body_frame = {
            1.0f, 0.0f, 0.0f,
            0.0f, 1.0f, 0.0f,
            0.0f, 0.0f, 1.0f,
        };
        const auto first =
            evaluate_fun_007bc680_preprojection(identity);
        require_close(
            first.residual,
            {7.0, 26.0, 27.0},
            1e-12,
            "residual",
            max_absolute_error);
        require_close(
            first.transformed_residual,
            {7.0, 26.0, 27.0},
            1e-12,
            "identity transformed residual",
            max_absolute_error);
        require_close(
            first.scaled_linear,
            {1.0, 2.0, 3.0},
            1e-12,
            "scaled linear",
            max_absolute_error);

        BodyPreProjectionInput matrix_case = identity;
        matrix_case.inverse_scalar = 2.0;
        matrix_case.body_frame = {
            1.0f, 2.0f, 3.0f,
            4.0f, 5.0f, 6.0f,
            7.0f, 8.0f, 9.0f,
        };
        const auto second =
            evaluate_fun_007bc680_preprojection(matrix_case);
        require_close(
            second.transformed_residual,
            {140.0, 320.0, 500.0},
            1e-12,
            "FUN_007aefb0 transformed residual",
            max_absolute_error);
        require_close(
            second.scaled_linear,
            {4.0, 8.0, 12.0},
            1e-12,
            "scaled linear second case",
            max_absolute_error);

        BodyPreProjectionInput zero{};
        zero.body_frame = identity.body_frame;
        const auto third =
            evaluate_fun_007bc680_preprojection(zero);
        require_close(
            third.residual,
            {0.0, 0.0, 0.0},
            1e-12,
            "zero residual",
            max_absolute_error);
        require_close(
            third.scaled_linear,
            {0.0, 0.0, 0.0},
            1e-12,
            "zero scaled linear",
            max_absolute_error);

        bool non_finite_rejected = false;
        try {
            BodyPreProjectionInput invalid = identity;
            invalid.inverse_scalar =
                std::numeric_limits<double>::quiet_NaN();
            (void)evaluate_fun_007bc680_preprojection(invalid);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error(
                "non-finite BODY preprojection input was accepted");
        }

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeBodyPreProjectionCheck/1\",\n"
            << "  \"source_function\": \"FUN_007bc680\",\n"
            << "  \"transform_source_function\": \"FUN_007aefb0\",\n"
            << "  \"cases\": 3,\n"
            << "  \"non_finite_rejected\": true,\n"
            << "  \"max_absolute_error\": "
            << std::setprecision(17)
            << max_absolute_error << ",\n"
            << "  \"full_constraint_projection_executed\": false,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_body_preprojection_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
