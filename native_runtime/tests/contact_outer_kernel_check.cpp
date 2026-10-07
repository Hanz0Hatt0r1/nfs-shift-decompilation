#include "shift_contact_outer_kernel.hpp"

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

shift::runtime::physics::ContactOuterKernelInput base_input() {
    using namespace shift::runtime::physics;
    ContactOuterKernelInput input{};
    input.planar_delta = {12.0, 7.0, 16.0};
    input.previous_distance_state = 10.0;
    input.distance_filter_cap = 100.0;
    input.speed_x = kContactSpeedFactorOffset + kContactSpeedFactorScale;
    input.speed_z = 0.0;
    input.surface_scalar = 5.0;
    input.base_scalar = 10.0;
    input.projected_scalar = 2.0;
    input.alignment_scalar = 3.0;
    input.param_3 = 2.0;
    return input;
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        double max_error = 0.0;

        const double filtered =
            execute_fun_00783a30_distance_filter(10.0, 20.0, 100.0, 0.5);
        require_close(
            filtered,
            10.0 + 10.0 * (0.5 / 100.5),
            1e-12,
            "FUN_00783a30 exact low-pass mismatch",
            max_error);

        const auto result =
            execute_fun_007675f0_outer_arithmetic(base_input());
        require_close(result.distance, 20.0, 0.0, "distance mismatch", max_error);
        require_close(
            result.planar_direction[0], 0.6, 1e-12,
            "planar direction X mismatch", max_error);
        require_close(
            result.planar_direction[1], 0.0, 0.0,
            "planar direction Y mismatch", max_error);
        require_close(
            result.planar_direction[2], 0.8, 1e-12,
            "planar direction Z mismatch", max_error);
        require_close(
            result.filtered_distance_state,
            10.0 + 10.0 * (0.5 / 100.5),
            1e-12,
            "distance state mismatch",
            max_error);
        require_close(
            result.gap,
            result.filtered_distance_state - (base_input().surface_scalar - kContactGapOffset),
            1e-12,
            "filtered-state gap mismatch",
            max_error);
        require_close(
            result.speed,
            kContactSpeedFactorOffset + kContactSpeedFactorScale,
            1e-12,
            "speed magnitude mismatch",
            max_error);
        require_close(
            result.speed_factor, 1.0, 1e-12,
            "speed factor upper clamp mismatch", max_error);
        if (!result.gate_open) {
            throw std::runtime_error("strict contact gate unexpectedly closed");
        }
        require_close(result.gap_shape, 1.0, 0.0, "gap upper clamp mismatch", max_error);
        require_close(result.force_scalar, 39.0, 1e-12, "force scalar mismatch", max_error);
        require_close(
            result.first_submission_scale, 78.0, 1e-12,
            "first submission scale mismatch", max_error);
        require_close(
            result.second_submission_scale, -3.9, 1e-12,
            "second submission scale mismatch", max_error);

        auto partial = base_input();
        partial.planar_delta = {7.0, 99.0, 0.0};
        const double partial_filtered =
            execute_fun_00783a30_distance_filter(
                partial.previous_distance_state,
                7.0,
                partial.distance_filter_cap,
                kContactDistanceFilterResponse);
        // Choose the source scalar so the machine-correct filtered-state gap is
        // exactly 1.25. Raw distance is deliberately different here.
        partial.surface_scalar = partial_filtered + 0.25;
        partial.speed_x =
            kContactSpeedFactorOffset + 0.25 * kContactSpeedFactorScale;
        const auto partial_result =
            execute_fun_007675f0_outer_arithmetic(partial);
        require_close(partial_result.gap, 1.25, 1e-12, "partial gap mismatch", max_error);
        require_close(partial_result.gap_shape, 0.5, 1e-12, "partial shape mismatch", max_error);
        require_close(partial_result.speed_factor, 0.25, 1e-12, "partial speed factor mismatch", max_error);
        require_close(partial_result.force_scalar, 7.3125, 1e-10, "partial force mismatch", max_error);
        require_close(partial_result.first_submission_scale, 14.625, 1e-10, "partial first scale mismatch", max_error);
        require_close(partial_result.second_submission_scale, -0.73125, 1e-10, "partial second scale mismatch", max_error);

        auto speed_floor = base_input();
        speed_floor.speed_x = kContactSpeedFactorOffset;
        const auto speed_floor_result =
            execute_fun_007675f0_outer_arithmetic(speed_floor);
        require_close(speed_floor_result.speed_factor, 0.0, 1e-12, "speed factor lower clamp mismatch", max_error);

        auto distance_five = base_input();
        distance_five.planar_delta = {3.0, 0.0, 4.0};
        if (execute_fun_007675f0_outer_arithmetic(distance_five).gate_open) {
            throw std::runtime_error("distance == 5 passed strict gate");
        }

        auto distance_two_hundred = base_input();
        distance_two_hundred.planar_delta = {120.0, 0.0, 160.0};
        const auto distance_two_hundred_result =
            execute_fun_007675f0_outer_arithmetic(distance_two_hundred);
        if (distance_two_hundred_result.gate_open) {
            throw std::runtime_error("distance == 200 passed strict gate");
        }

        auto speed_one = base_input();
        speed_one.speed_x = 1.0;
        if (execute_fun_007675f0_outer_arithmetic(speed_one).gate_open) {
            throw std::runtime_error("speed == 1 passed strict gate");
        }

        auto capped = base_input();
        capped.planar_delta = {150.0, 0.0, 200.0};
        const auto capped_result =
            execute_fun_007675f0_outer_arithmetic(capped);
        require_close(
            capped_result.filtered_distance_state,
            kContactDistanceLimit,
            0.0,
            "distance > 200 did not store cap",
            max_error);

        bool zero_delta_rejected = false;
        try {
            auto bad = base_input();
            bad.planar_delta = {0.0, 10.0, 0.0};
            (void)execute_fun_007675f0_outer_arithmetic(bad);
        } catch (const std::invalid_argument&) {
            zero_delta_rejected = true;
        }
        if (!zero_delta_rejected) {
            throw std::runtime_error("zero X/Z delta was accepted");
        }

        bool zero_filter_denominator_rejected = false;
        try {
            (void)execute_fun_00783a30_distance_filter(1.0, 2.0, -0.5, 0.5);
        } catch (const std::invalid_argument&) {
            zero_filter_denominator_rejected = true;
        }
        if (!zero_filter_denominator_rejected) {
            throw std::runtime_error("zero FUN_00783a30 denominator was accepted");
        }

        bool non_finite_rejected = false;
        try {
            auto bad = base_input();
            bad.alignment_scalar = std::numeric_limits<double>::infinity();
            (void)execute_fun_007675f0_outer_arithmetic(bad);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error("non-finite FUN_007675f0 input was accepted");
        }

        std::cout
            << "{\"format\":\"SHIFT.NativeContactOuterKernel/1\","
            << "\"ready\":true,"
            << "\"function\":\"FUN_007675f0\","
            << "\"distance_filter_function\":\"FUN_00783a30\","
            << "\"outer_arithmetic_proven\":true,"
            << "\"strict_gate_proven\":true,"
            << "\"distance_filter_proven\":true,"
            << "\"gap_uses_filtered_state\":true,"
            << "\"paired_submission_scales_proven\":true,"
            << "\"body_point_submission_vectors_proven\":false,"
            << "\"runtime_scheduling_proven\":false,"
            << "\"zero_delta_rejected\":true,"
            << "\"non_finite_rejected\":true,"
            << "\"max_absolute_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << "\n";
        return 1;
    }
}
