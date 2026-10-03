#include "shift_fun_007afdd0_source_core.hpp"

#include <array>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {

using namespace shift::runtime::physics;

void require_equal(float actual, float expected, const char* label) {
    if (actual != expected) {
        throw std::runtime_error(label);
    }
}

void require_close(float actual, float expected, const char* label) {
    if (!std::isfinite(actual) || std::abs(actual - expected) > 1e-6f) {
        throw std::runtime_error(label);
    }
}

void require_frame_equal(
    const ConstraintRefreshFrame3f& actual,
    const ConstraintRefreshFrame3f& expected,
    const char* label) {
    for (std::size_t index = 0; index < actual.size(); ++index) {
        require_equal(actual[index], expected[index], label);
    }
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        const ConstraintRefreshFrame3f basis = {
            1.0f, 2.0f, 3.0f,
            4.0f, 5.0f, 6.0f,
            7.0f, 8.0f, 9.0f,
        };

        Fun007afdd0ScalarBoundary zero{};
        zero.squared_magnitude_test = 0.0f;
        zero.sqrt_magnitude = std::numeric_limits<float>::quiet_NaN();
        zero.sine = std::numeric_limits<float>::quiet_NaN();
        zero.cosine = std::numeric_limits<float>::quiet_NaN();
        const auto no_op = execute_fun_007afdd0_source_core(
            basis,
            {0.0, 0.0, 0.0},
            zero);
        if (no_op.applied) {
            throw std::runtime_error("FUN_007afdd0 zero path unexpectedly applied");
        }
        require_frame_equal(no_op.basis, basis, "FUN_007afdd0 zero path changed basis");
        require_frame_equal(
            no_op.rotation_coefficients,
            {1.0f, 0.0f, 0.0f,
             0.0f, 1.0f, 0.0f,
             0.0f, 0.0f, 1.0f},
            "FUN_007afdd0 zero path rotation is not identity");

        Fun007afdd0ScalarBoundary quarter_turn{};
        quarter_turn.squared_magnitude_test = 4.0f;
        quarter_turn.sqrt_magnitude = 2.0f;
        quarter_turn.sine = 1.0f;
        quarter_turn.cosine = 0.0f;
        const auto rotated = execute_fun_007afdd0_source_core(
            basis,
            {0.0, 0.0, 2.0},
            quarter_turn);
        if (!rotated.applied) {
            throw std::runtime_error("FUN_007afdd0 non-zero path was not applied");
        }
        require_equal(rotated.normalized_axis[0], 0.0f, "axis x mismatch");
        require_equal(rotated.normalized_axis[1], 0.0f, "axis y mismatch");
        require_equal(rotated.normalized_axis[2], 1.0f, "axis z mismatch");
        require_frame_equal(
            rotated.rotation_coefficients,
            {0.0f, -1.0f, 0.0f,
             1.0f, 0.0f, 0.0f,
             0.0f, 0.0f, 1.0f},
            "FUN_007afdd0 recovered rotation coefficients mismatch");
        require_frame_equal(
            rotated.basis,
            {-4.0f, -5.0f, -6.0f,
             1.0f, 2.0f, 3.0f,
             7.0f, 8.0f, 9.0f},
            "FUN_007afdd0 in-place stripe order mismatch");

        const ConstraintRefreshFrame3f identity = {
            1.0f, 0.0f, 0.0f,
            0.0f, 1.0f, 0.0f,
            0.0f, 0.0f, 1.0f,
        };
        Fun007afdd0ScalarBoundary normalized{};
        normalized.squared_magnitude_test = 25.0f;
        normalized.sqrt_magnitude = 5.0f;
        normalized.sine = 0.0f;
        normalized.cosine = 1.0f;
        const auto axis_result = execute_fun_007afdd0_source_core(
            identity,
            {3.0000001192092896, 4.000000238418579, 0.0},
            normalized);
        require_close(axis_result.normalized_axis[0], 0.6f, "normalized x mismatch");
        require_close(axis_result.normalized_axis[1], 0.8f, "normalized y mismatch");
        require_frame_equal(
            axis_result.basis,
            identity,
            "cos=1/sin=0 source core changed identity basis");

        bool zero_sqrt_rejected = false;
        try {
            Fun007afdd0ScalarBoundary bad{};
            bad.squared_magnitude_test = 1.0f;
            bad.sqrt_magnitude = 0.0f;
            (void)execute_fun_007afdd0_source_core(
                identity,
                {1.0, 0.0, 0.0},
                bad);
        } catch (const std::invalid_argument&) {
            zero_sqrt_rejected = true;
        }
        if (!zero_sqrt_rejected) {
            throw std::runtime_error("FUN_007afdd0 zero sqrt boundary accepted");
        }

        bool nonfinite_rejected = false;
        try {
            Fun007afdd0ScalarBoundary bad{};
            bad.squared_magnitude_test = 1.0f;
            bad.sqrt_magnitude = 1.0f;
            bad.sine = std::numeric_limits<float>::infinity();
            bad.cosine = 1.0f;
            (void)execute_fun_007afdd0_source_core(
                identity,
                {1.0, 0.0, 0.0},
                bad);
        } catch (const std::invalid_argument&) {
            nonfinite_rejected = true;
        }
        if (!nonfinite_rejected) {
            throw std::runtime_error("FUN_007afdd0 non-finite trig boundary accepted");
        }

        std::cout
            << "{\"format\":\"" << kNativeFun007afdd0SourceCoreFormat << "\","
            << "\"ready\":true,"
            << "\"source_function\":\"" << kFun007afdd0SourceFunction << "\","
            << "\"sine_helper\":\"" << kFun007afdd0SineHelper << "\","
            << "\"cosine_helper\":\"" << kFun007afdd0CosineHelper << "\","
            << "\"zero_test_noop_proven\":true,"
            << "\"in_place_stripe_order_proven\":true,"
            << "\"host_math_used\":false,"
            << "\"machine_precision_gate_required\":true,"
            << "\"native_callback_replacement_ready\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
