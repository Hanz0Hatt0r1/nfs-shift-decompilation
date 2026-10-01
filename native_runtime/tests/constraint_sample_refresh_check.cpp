#include "shift_constraint_sample_refresh.hpp"

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

double max_error = 0.0;

void check_close(double actual, double expected, double tolerance = 1e-12) {
    const double error = std::abs(actual - expected);
    max_error = std::max(max_error, error);
    if (error > tolerance * std::max(1.0, std::abs(expected))) {
        throw std::runtime_error("constraint sample refresh oracle mismatch");
    }
}

template <std::size_t N>
void check_array(
    const std::array<double, N>& actual,
    const std::array<double, N>& expected,
    double tolerance = 1e-12) {

    for (std::size_t index = 0; index < N; ++index) {
        check_close(actual[index], expected[index], tolerance);
    }
}

}  // namespace

int main() {
    try {
        using namespace shift::runtime::physics;

        const ConstraintRefreshFrame3f dense_frame = {
            1.0f, 2.0f, 3.0f,
            4.0f, 5.0f, 6.0f,
            7.0f, 8.0f, 9.0f,
        };
        const ConstraintRefreshFrame3f positive_frame = {
            2.0f, 0.0f, 0.0f,
            0.0f, 3.0f, 0.0f,
            0.0f, 0.0f, 4.0f,
        };
        const ConstraintRefreshFrame3f negative_frame = {
            1.0f, 0.0f, 0.0f,
            0.0f, 2.0f, 0.0f,
            0.0f, 0.0f, 3.0f,
        };

        JointConstraintRefreshInput joint{};
        joint.positive_body_frame = dense_frame;
        joint.negative_body_frame = positive_frame;
        joint.positive_local_position = {0.25, 0.5, 0.75};
        joint.negative_local_position = {-1.0, 0.5, 2.0};
        const auto joint_result =
            refresh_fun_007b2da0_joint(joint);
        check_array(
            joint_result.positive_position,
            std::array<double, 3>{3.5, 8.0, 12.5});
        check_array(
            joint_result.negative_position,
            std::array<double, 3>{-2.0, 1.5, 8.0});

        HingeConstraintRefreshInput hinge{};
        hinge.positive_body_frame = positive_frame;
        hinge.negative_body_frame = negative_frame;
        hinge.positive_angular_local = {1.0, 2.0, 3.0};
        hinge.positive_linear_local = {4.0, 5.0, 6.0};
        hinge.negative_primary_local = {1.0, 0.0, 0.0};
        const auto hinge_result =
            refresh_fun_007b2de0_hinge(hinge);
        check_array(
            hinge_result.positive_angular,
            std::array<double, 3>{2.0, 6.0, 12.0});
        check_array(
            hinge_result.positive_linear,
            std::array<double, 3>{8.0, 15.0, 24.0});
        check_array(
            hinge_result.negative_linear_local,
            std::array<double, 3>{0.0, -36.0, 12.0});
        check_array(
            hinge_result.negative_angular_local,
            std::array<double, 3>{0.0, 12.0, 36.0});
        check_array(
            hinge_result.negative_angular,
            std::array<double, 3>{0.0, 24.0, 108.0});
        check_array(
            hinge_result.negative_linear,
            std::array<double, 3>{0.0, -72.0, 36.0});

        BarConstraintRefreshInput bar{};
        bar.positive_body_frame = {
            2.0f, 0.0f, 0.0f,
            0.0f, 1.0f, 0.0f,
            0.0f, 0.0f, 1.0f,
        };
        bar.negative_body_frame = {
            1.0f, 0.0f, 0.0f,
            0.0f, 3.0f, 0.0f,
            0.0f, 0.0f, 1.0f,
        };
        bar.positive_body_position = {1.0, 2.0, 3.0};
        bar.negative_body_position = {-1.0, 0.0, 1.0};
        bar.positive_local_point = {1.0, 0.0, 0.0};
        bar.negative_local_point = {0.0, 1.0, 0.0};
        const auto bar_result =
            refresh_fun_007b2f70_bar(bar);
        check_array(
            bar_result.positive_point,
            std::array<double, 3>{2.0, 0.0, 0.0});
        check_array(
            bar_result.negative_point,
            std::array<double, 3>{0.0, 3.0, 0.0});
        const double inv_sqrt_21 = 1.0 / std::sqrt(21.0);
        check_array(
            bar_result.direction,
            std::array<double, 3>{
                4.0 * inv_sqrt_21,
                -1.0 * inv_sqrt_21,
                2.0 * inv_sqrt_21,
            });

        BarConstraintRefreshInput degenerate{};
        degenerate.positive_body_frame = negative_frame;
        degenerate.negative_body_frame = negative_frame;
        const auto degenerate_result =
            refresh_fun_007b2f70_bar(degenerate);
        check_array(
            degenerate_result.direction,
            std::array<double, 3>{0.0, 0.0, 0.0});

        ConstraintSampleRefreshFrameInput frame{};
        frame.joints.push_back(joint);
        frame.hinges.push_back(hinge);
        frame.bars.push_back(bar);
        const auto frame_result =
            refresh_fun_007b3ed0_constraints(frame);
        if (frame_result.joint_count != 1 ||
            frame_result.hinge_count != 1 ||
            frame_result.bar_count != 1) {
            throw std::runtime_error(
                "FUN_007b3ed0 refresh count mismatch");
        }
        check_array(
            frame_result.joints[0].positive_position,
            joint_result.positive_position);
        check_array(
            frame_result.hinges[0].negative_angular,
            hinge_result.negative_angular);
        check_array(
            frame_result.bars[0].direction,
            bar_result.direction);

        bool nonfinite_rejected = false;
        try {
            auto invalid = joint;
            invalid.positive_local_position[0] =
                std::numeric_limits<double>::infinity();
            (void)refresh_fun_007b2da0_joint(invalid);
        } catch (const std::invalid_argument&) {
            nonfinite_rejected = true;
        }
        if (!nonfinite_rejected) {
            throw std::runtime_error(
                "non-finite refresh input was accepted");
        }

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeConstraintSampleRefreshCheck/1\",\n"
            << "  \"frame_function\": \"FUN_007b3ed0\",\n"
            << "  \"joint_function\": \"FUN_007b2da0\",\n"
            << "  \"hinge_function\": \"FUN_007b2de0\",\n"
            << "  \"bar_function\": \"FUN_007b2f70\",\n"
            << "  \"forward_transform\": \"FUN_007aefb0\",\n"
            << "  \"transpose_transform\": \"FUN_007af0a0\",\n"
            << "  \"joint_record_stride\": 160,\n"
            << "  \"hinge_record_stride\": 160,\n"
            << "  \"bar_record_stride\": 184,\n"
            << "  \"joint_count\": " << frame_result.joint_count << ",\n"
            << "  \"hinge_count\": " << frame_result.hinge_count << ",\n"
            << "  \"bar_count\": " << frame_result.bar_count << ",\n"
            << "  \"bar_zero_length_preserved\": true,\n"
            << "  \"nonfinite_rejected\": true,\n"
            << "  \"writes_generated_contributions\": false,\n"
            << "  \"refreshes_prepared_samples\": true,\n"
            << "  \"max_absolute_error\": "
            << std::setprecision(17) << max_error << ",\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_constraint_sample_refresh_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
