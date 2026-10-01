#include "shift_constraint_relation_frame.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>
#include <stdexcept>

namespace {

double max_error = 0.0;

void check_close(
    double actual,
    double expected,
    double tolerance = 1e-12) {

    const double error =
        std::abs(actual - expected);
    max_error = std::max(max_error, error);
    if (error >
        tolerance *
            std::max(1.0, std::abs(expected))) {
        throw std::runtime_error(
            "constraint relation frame oracle mismatch");
    }
}

template <std::size_t N>
void check_array(
    const std::array<double, N>& actual,
    const std::array<double, N>& expected,
    double tolerance = 1e-12) {

    for (std::size_t index = 0;
         index < N;
         ++index) {
        check_close(
            actual[index],
            expected[index],
            tolerance);
    }
}

}  // namespace

int main() {
    try {
        using namespace shift::runtime::physics;

        const ConstraintRefreshFrame3f identity = {
            1.0f, 0.0f, 0.0f,
            0.0f, 1.0f, 0.0f,
            0.0f, 0.0f, 1.0f,
        };

        ConstraintRelationFrameInput input{};
        input.scalar_count = 6;
        input.bodies = {
            {identity, {1.0, 2.0, 3.0}},
            {identity, {-1.0, 0.0, 1.0}},
        };
        input.joints.push_back({
            0,
            1,
            {2.0, 3.0, 4.0},
            0,
        });
        input.hinges.push_back({
            0,
            1,
            {0.0, 1.0, 0.0},
            3,
        });
        input.bars.push_back({
            0,
            1,
            {3.0, 2.0, 3.0},
            {-1.0, 3.0, 1.0},
            5,
        });

        const auto result =
            build_fun_007b3820_constraint_relation_frame(
                input);

        if (result.refreshed.joint_count != 1 ||
            result.refreshed.hinge_count != 1 ||
            result.refreshed.bar_count != 1 ||
            result.body_sample_count != 6) {
            throw std::runtime_error(
                "constraint relation/sample count mismatch");
        }

        check_array(
            result.refresh_input.joints[0]
                .positive_local_position,
            std::array<double, 3>{1.0, 1.0, 1.0});
        check_array(
            result.refresh_input.joints[0]
                .negative_local_position,
            std::array<double, 3>{3.0, 3.0, 3.0});
        check_array(
            result.body_joints[0][0].position,
            std::array<double, 3>{1.0, 1.0, 1.0});
        check_array(
            result.body_joints[1][0].position,
            std::array<double, 3>{3.0, 3.0, 3.0});
        if (result.body_joints[0][0].side_flag != 1u ||
            result.body_joints[1][0].side_flag != 0u) {
            throw std::runtime_error(
                "JOINT side ownership mismatch");
        }
        if (result.joint_ownership[0][0]
                .body_sample_ordinal != 0 ||
            result.joint_ownership[1][0]
                .body_sample_ordinal != 0) {
            throw std::runtime_error(
                "JOINT sample ordinal mismatch");
        }

        check_array(
            result.body_hinges[0][0].position,
            std::array<double, 3>{0.0, 1.0, 0.0});
        check_array(
            result.body_hinges[1][0].position,
            std::array<double, 3>{0.0, 1.0, 0.0});
        check_array(
            result.body_hinges[0][0].frame_offset,
            std::array<double, 3>{0.0, 1.0, 0.0});
        if (result.body_hinges[0][0].side_flag != 1u ||
            result.body_hinges[1][0].side_flag != 0u) {
            throw std::runtime_error(
                "HINGE side ownership mismatch");
        }

        check_array(
            result.body_bars[0][0].point,
            std::array<double, 3>{2.0, 0.0, 0.0});
        check_array(
            result.body_bars[1][0].point,
            std::array<double, 3>{0.0, 3.0, 0.0});
        const double inverse_sqrt_21 =
            1.0 / std::sqrt(21.0);
        const std::array<double, 3> direction = {
            4.0 * inverse_sqrt_21,
            -1.0 * inverse_sqrt_21,
            2.0 * inverse_sqrt_21,
        };
        check_array(
            result.body_bars[0][0].direction,
            direction);
        check_array(
            result.body_bars[1][0].direction,
            direction);
        check_close(
            result.body_bars[0][0].side_bias,
            std::sqrt(21.0));
        check_close(
            result.body_bars[1][0].side_bias,
            std::sqrt(21.0));
        if (result.body_bars[0][0].side_flag != 1u ||
            result.body_bars[1][0].side_flag != 0u) {
            throw std::runtime_error(
                "BAR side ownership mismatch");
        }

        ConstraintRelationFrameInput same_body{};
        same_body.scalar_count = 3;
        same_body.bodies = {
            {identity, {0.0, 0.0, 0.0}},
        };
        same_body.joints.push_back({
            0,
            0,
            {1.0, 2.0, 3.0},
            0,
        });
        const auto same =
            build_fun_007b3820_constraint_relation_frame(
                same_body);
        if (same.body_joints[0].size() != 2 ||
            same.joint_ownership[0].size() != 2 ||
            same.joint_ownership[0][0].side_flag != 1u ||
            same.joint_ownership[0][1].side_flag != 0u ||
            same.joint_ownership[0][0]
                .body_sample_ordinal != 0 ||
            same.joint_ownership[0][1]
                .body_sample_ordinal != 1) {
            throw std::runtime_error(
                "same-BODY positive/negative insertion order mismatch");
        }

        bool overlap_rejected = false;
        try {
            auto invalid = input;
            invalid.hinges[0].scalar_base = 2;
            (void)build_fun_007b3820_constraint_relation_frame(
                invalid);
        } catch (const std::invalid_argument&) {
            overlap_rejected = true;
        }
        if (!overlap_rejected) {
            throw std::runtime_error(
                "overlapping scalar layout accepted");
        }

        bool body_range_rejected = false;
        try {
            auto invalid = input;
            invalid.bars[0].negative_body_index = 2;
            (void)build_fun_007b3820_constraint_relation_frame(
                invalid);
        } catch (const std::out_of_range&) {
            body_range_rejected = true;
        }
        if (!body_range_rejected) {
            throw std::runtime_error(
                "out-of-range BODY relation accepted");
        }

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeConstraintRelationFrameCheck/1\",\n"
            << "  \"construction_function\": \"FUN_007b3820\",\n"
            << "  \"layout_function\": \"FUN_007b1b60\",\n"
            << "  \"refresh_function\": \"FUN_007b3ed0\",\n"
            << "  \"joint_allocator\": \"FUN_007ba8b0\",\n"
            << "  \"hinge_allocator\": \"FUN_007ba900\",\n"
            << "  \"bar_allocator\": \"FUN_007ba990\",\n"
            << "  \"positive_side_flag\": 1,\n"
            << "  \"negative_side_flag\": 0,\n"
            << "  \"relation_body_offsets\": [120, 128],\n"
            << "  \"relation_sample_offsets\": [124, 132],\n"
            << "  \"body_sample_count\": "
            << result.body_sample_count << ",\n"
            << "  \"same_body_insertion_order_preserved\": true,\n"
            << "  \"scalar_layout_fail_closed\": true,\n"
            << "  \"body_index_fail_closed\": true,\n"
            << "  \"gbcf_packet_emitted\": false,\n"
            << "  \"max_absolute_error\": "
            << std::setprecision(17)
            << max_error << ",\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";

        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_constraint_relation_frame_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
