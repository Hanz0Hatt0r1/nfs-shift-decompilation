#include "shift_post_solve_application.hpp"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

void require_close(
    double actual,
    double expected,
    const char* label,
    double tolerance = 1e-12) {

    const double error = std::abs(actual - expected);
    const double limit =
        tolerance * std::max(1.0, std::abs(expected));
    if (!std::isfinite(actual) || error > limit) {
        throw std::runtime_error(
            std::string(label) + " mismatch");
    }
}

void require_vec(
    const shift::runtime::physics::Vec3d& actual,
    const shift::runtime::physics::Vec3d& expected,
    const char* label) {

    for (std::size_t index = 0; index < 3; ++index) {
        require_close(
            actual[index],
            expected[index],
            label);
    }
}

}  // namespace

int main() {
    try {
        using namespace shift::runtime::physics;

        const auto positive_delta =
            body_accumulator_delta(
                {1.0, 2.0, 3.0},
                {4.0, 5.0, 6.0},
                +1);
        require_vec(
            positive_delta.linear,
            {4.0, 5.0, 6.0},
            "positive linear delta");
        require_vec(
            positive_delta.angular,
            {-3.0, 6.0, -3.0},
            "positive angular delta");

        const auto negative_delta =
            body_accumulator_delta(
                {1.0, 2.0, 3.0},
                {4.0, 5.0, 6.0},
                -1);
        require_vec(
            negative_delta.linear,
            {-4.0, -5.0, -6.0},
            "negative linear delta");
        require_vec(
            negative_delta.angular,
            {3.0, -6.0, 3.0},
            "negative angular delta");

        const BodyAccumulatorState joint_positive{
            {0.0, 0.0, 0.0},
            {10.0, 20.0, 30.0},
        };
        const BodyAccumulatorState joint_negative{
            {1.0, 2.0, 3.0},
            {4.0, 5.0, 6.0},
        };
        const auto joint =
            apply_joint_solution(
                joint_positive,
                joint_negative,
                {10.0, 20.0, 30.0},
                {1.0, 2.0, 3.0},
                {4.0, 5.0, 6.0});
        require_vec(
            joint.positive.linear,
            {20.0, 40.0, 60.0},
            "joint positive linear");
        require_vec(
            joint.positive.angular,
            {0.0, 0.0, 0.0},
            "joint positive angular");
        require_vec(
            joint.negative.linear,
            {-6.0, -15.0, -24.0},
            "joint negative linear");

        const auto hinge =
            apply_hinge_solution(
                {
                    {1.0, 2.0, 3.0},
                    {7.0, 8.0, 9.0},
                },
                {
                    {4.0, 5.0, 6.0},
                    {10.0, 11.0, 12.0},
                },
                {2.0, 3.0},
                {1.0, 2.0, 3.0},
                {4.0, 5.0, 6.0},
                {2.0, 1.0, 0.0},
                {0.0, 3.0, 4.0});
        require_vec(
            hinge.positive.angular,
            {15.0, 21.0, 27.0},
            "hinge positive angular");
        require_vec(
            hinge.negative.angular,
            {0.0, -6.0, -6.0},
            "hinge negative angular");
        require_vec(
            hinge.positive.linear,
            {7.0, 8.0, 9.0},
            "hinge positive linear unchanged");
        require_vec(
            hinge.negative.linear,
            {10.0, 11.0, 12.0},
            "hinge negative linear unchanged");

        const BodyAccumulatorState zero_state{};
        const auto bar =
            apply_bar_solution(
                zero_state,
                zero_state,
                3.0,
                {1.0, 0.0, 0.0},
                {2.0, 0.0, 0.0},
                {2.0, 3.0, 4.0});
        require_vec(
            bar.vector_solution,
            {6.0, 9.0, 12.0},
            "bar vector solution");
        require_vec(
            bar.positive.linear,
            {6.0, 9.0, 12.0},
            "bar positive linear");
        require_vec(
            bar.negative.linear,
            {-6.0, -9.0, -12.0},
            "bar negative linear");
        require_vec(
            bar.positive.angular,
            {0.0, -12.0, 9.0},
            "bar positive angular");
        require_vec(
            bar.negative.angular,
            {0.0, 24.0, -18.0},
            "bar negative angular");

        bool invalid_sign_rejected = false;
        try {
            (void)body_accumulator_delta(
                {0.0, 0.0, 0.0},
                {1.0, 1.0, 1.0},
                0);
        } catch (const std::invalid_argument&) {
            invalid_sign_rejected = true;
        }
        if (!invalid_sign_rejected) {
            throw std::runtime_error(
                "invalid accumulator sign was accepted");
        }

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativePostSolveApplicationCheck/1\",\n"
            << "  \"post_solve_source_function\": "
            << "\"" << kPostSolveSourceFunction << "\",\n"
            << "  \"positive_helper\": "
            << "\"" << kPositiveBodyAccumulatorSourceFunction << "\",\n"
            << "  \"negative_helper\": "
            << "\"" << kNegativeBodyAccumulatorSourceFunction << "\",\n"
            << "  \"joint_width\": 3,\n"
            << "  \"hinge_width\": 2,\n"
            << "  \"bar_width\": 1,\n"
            << "  \"scheduler_integration\": false,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_post_solve_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
