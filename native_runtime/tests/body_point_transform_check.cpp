#include "shift_body_point_transform.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {

void require_close(
    double actual,
    double expected,
    double tolerance,
    const char* label,
    double& max_error) {

    const double error = std::abs(actual - expected);
    max_error = std::max(max_error, error);
    if (!std::isfinite(actual) || error > tolerance) {
        throw std::runtime_error(label);
    }
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        double max_error = 0.0;

        const BodyPointTransformState body = {
            {1.0, 2.0, 3.0},
            {10.0, 20.0, 30.0},
            {100.0, 200.0, 300.0},
        };
        const auto transformed =
            transform_fun_007537b0_body_point(
                body,
                {4.0, 5.0, 6.0});
        const double expected_transformed[3] = {97.0, 206.0, 297.0};
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(
                transformed[component],
                expected_transformed[component],
                0.0,
                "FUN_007537b0 result",
                max_error);
        }

        const BodyPointTransformState relative_body = {
            {1.0, 2.0, 3.0},
            {1.0, 1.0, 1.0},
            {0.0, 0.0, 0.0},
        };
        const auto relative =
            transform_fun_00753810_body_point_relative(
                relative_body,
                {4.0, 5.0, 6.0});
        const double expected_relative[3] = {-2.0, 4.0, -2.0};
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(
                relative[component],
                expected_relative[component],
                0.0,
                "FUN_00753810 result",
                max_error);
        }

        const BodyPointTransformState zero_angular = {
            {0.0, 0.0, 0.0},
            {2.0, 3.0, 4.0},
            {10.0, 20.0, 30.0},
        };
        const auto translation_only =
            transform_fun_007537b0_body_point(
                zero_angular,
                {100.0, 200.0, 300.0});
        const double expected_translation[3] = {10.0, 20.0, 30.0};
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(
                translation_only[component],
                expected_translation[component],
                0.0,
                "FUN_007537b0 zero-angular result",
                max_error);
        }

        bool non_finite_rejected = false;
        try {
            BodyPointTransformState bad = body;
            bad.angular[0] = std::numeric_limits<double>::infinity();
            (void)transform_fun_007537b0_body_point(
                bad,
                {1.0, 2.0, 3.0});
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error(
                "BODY point transform accepted non-finite state");
        }

        std::cout
            << "{\"format\":\"SHIFT.NativeBodyPointTransform/1\","
            << "\"ready\":true,"
            << "\"function\":\"FUN_007537b0\","
            << "\"relative_function\":\"FUN_00753810\","
            << "\"angular_offsets\":[24,32,40],"
            << "\"position_offsets\":[0,8,16],"
            << "\"translation_offsets\":[120,128,136],"
            << "\"non_finite_rejected\":true,"
            << "\"max_absolute_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << "\n";
        return 1;
    }
}
