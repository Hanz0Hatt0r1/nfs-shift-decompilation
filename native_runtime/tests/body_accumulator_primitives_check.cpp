#include "shift_body_accumulator_primitives.hpp"

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

        BodyAccumulatorState positive{};
        apply_fun_007baa70_body_accumulator(
            positive,
            {4.0, 5.0, 6.0},
            {2.0, 4.0, 8.0});
        const double expected_angular[3] = {16.0, -20.0, 6.0};
        const double expected_linear[3] = {2.0, 4.0, 8.0};
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(
                positive.angular[component],
                expected_angular[component],
                0.0,
                "FUN_007baa70 angular update",
                max_error);
            require_close(
                positive.linear[component],
                expected_linear[component],
                0.0,
                "FUN_007baa70 linear update",
                max_error);
        }

        BodyAccumulatorState negative{};
        apply_fun_007baaf0_body_accumulator(
            negative,
            {4.0, 5.0, 6.0},
            {2.0, 4.0, 8.0});
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(
                negative.angular[component],
                -expected_angular[component],
                0.0,
                "FUN_007baaf0 angular update",
                max_error);
            require_close(
                negative.linear[component],
                -expected_linear[component],
                0.0,
                "FUN_007baaf0 linear update",
                max_error);
        }

        BodyAccumulatorState point_accumulator{};
        apply_fun_007ba9e0_point_accumulator(
            point_accumulator,
            {5.0, 7.0, 9.0},
            {1.0, 2.0, 3.0},
            {2.0, 4.0, 8.0});
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(
                point_accumulator.angular[component],
                expected_angular[component],
                0.0,
                "FUN_007ba9e0 angular update",
                max_error);
            require_close(
                point_accumulator.linear[component],
                expected_linear[component],
                0.0,
                "FUN_007ba9e0 linear update",
                max_error);
        }

        BodyAccumulatorState accumulated{};
        accumulated.angular = {1.0, 2.0, 3.0};
        accumulated.linear = {4.0, 5.0, 6.0};
        apply_fun_007baa70_body_accumulator(
            accumulated,
            {4.0, 5.0, 6.0},
            {2.0, 4.0, 8.0});
        apply_fun_007baaf0_body_accumulator(
            accumulated,
            {4.0, 5.0, 6.0},
            {2.0, 4.0, 8.0});
        const double original_angular[3] = {1.0, 2.0, 3.0};
        const double original_linear[3] = {4.0, 5.0, 6.0};
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(
                accumulated.angular[component],
                original_angular[component],
                0.0,
                "BODY paired angular cancellation",
                max_error);
            require_close(
                accumulated.linear[component],
                original_linear[component],
                0.0,
                "BODY paired linear cancellation",
                max_error);
        }

        bool non_finite_rejected = false;
        try {
            BodyAccumulatorState bad{};
            apply_fun_007baa70_body_accumulator(
                bad,
                {1.0, 0.0, 0.0},
                {std::numeric_limits<double>::infinity(), 0.0, 0.0});
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error(
                "BODY accumulator accepted non-finite contribution");
        }

        std::cout
            << "{\"format\":\"SHIFT.NativeBodyAccumulatorPrimitives/1\","
            << "\"ready\":true,"
            << "\"point_accumulator_function\":\"FUN_007ba9e0\","
            << "\"positive_function\":\"FUN_007baa70\","
            << "\"negative_function\":\"FUN_007baaf0\","
            << "\"paired_cancellation_proven\":true,"
            << "\"non_finite_rejected\":true,"
            << "\"max_absolute_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << "\n";
        return 1;
    }
}
