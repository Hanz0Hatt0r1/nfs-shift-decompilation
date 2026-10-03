#include "shift_body_frame_integration.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

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

shift::runtime::physics::ConstraintRefreshFrame3f identity_basis() {
    return {
        1.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f,
        0.0f, 0.0f, 1.0f,
    };
}

shift::runtime::physics::BodyFrameIntegrationState make_state() {
    using namespace shift::runtime::physics;
    BodyFrameIntegrationState state{};
    state.origin = {1.0, 2.0, 3.0};
    state.cross_vector = {0.1, -0.2, 0.3};
    state.prepared_vector = {10.0, 20.0, 30.0};
    state.accumulators.angular = {2.0, 4.0, 6.0};
    state.accumulators.linear = {1.0, 2.0, 3.0};
    state.motion_triplet = {4.0, 5.0, 6.0};
    state.scalar_0x90 = 0.5;
    state.reciprocal_coefficients = {2.0, 3.0, 5.0};
    state.basis = identity_basis();
    return state;
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        double max_error = 0.0;
        constexpr double dt = 0.25;

        const auto pre =
            advance_fun_007bab70_pre_basis(make_state(), dt);
        const double expected_origin[3] = {2.0, 3.25, 4.5};
        const double expected_motion[3] = {4.125, 5.25, 6.375};
        const double expected_rotation[3] = {0.025, -0.05, 0.075};
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(
                pre.state.origin[component],
                expected_origin[component],
                1e-15,
                "FUN_007bab70 origin update mismatch",
                max_error);
            require_close(
                pre.state.motion_triplet[component],
                expected_motion[component],
                1e-15,
                "FUN_007bab70 motion update mismatch",
                max_error);
            require_close(
                pre.rotation_increment[component],
                expected_rotation[component],
                1e-15,
                "FUN_007bab70 rotation increment mismatch",
                max_error);
        }
        // The pre-basis stage must not consume accumulator_a or mutate basis.
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(
                pre.state.prepared_vector[component],
                make_state().prepared_vector[component],
                0.0,
                "FUN_007bab70 prepared vector changed before basis boundary",
                max_error);
        }
        if (pre.state.basis != identity_basis()) {
            throw std::runtime_error(
                "FUN_007bab70 pre-basis stage changed basis");
        }

        auto zero_rotation_state = make_state();
        zero_rotation_state.cross_vector = {0.0, 0.0, 0.0};
        const auto complete =
            execute_fun_007bab70_with_external_basis(
                zero_rotation_state,
                identity_basis(),
                dt);
        const double expected_prepared[3] = {10.5, 21.0, 31.5};
        const double expected_cross[3] = {21.0, 63.0, 157.5};
        const double expected_tensor[3][3] = {
            {2.0, 0.0, 0.0},
            {0.0, 3.0, 0.0},
            {0.0, 0.0, 5.0},
        };
        for (std::size_t row = 0; row < 3u; ++row) {
            for (std::size_t column = 0; column < 3u; ++column) {
                require_close(
                    complete.symmetric_tensor[row][column],
                    expected_tensor[row][column],
                    0.0,
                    "FUN_007ba630 joined tensor mismatch",
                    max_error);
            }
            require_close(
                complete.state.prepared_vector[row],
                expected_prepared[row],
                0.0,
                "FUN_007bab70 prepared vector update mismatch",
                max_error);
            require_close(
                complete.state.cross_vector[row],
                expected_cross[row],
                0.0,
                "FUN_007bab70 tensor/vector join mismatch",
                max_error);
        }

        std::vector<BodyFrameIntegrationState> bodies = {
            zero_rotation_state,
            zero_rotation_state,
        };
        bodies[1].origin = {-1.0, -2.0, -3.0};
        bodies[1].motion_triplet = {-4.0, -5.0, -6.0};
        const std::vector<ConstraintRefreshFrame3f> updated_bases = {
            identity_basis(),
            identity_basis(),
        };
        const auto array_result =
            execute_fun_007b2270_body_array_with_external_bases(
                bodies,
                updated_bases,
                dt);
        if (array_result.size() != 2u) {
            throw std::runtime_error("FUN_007b2270 BODY count mismatch");
        }
        require_close(
            array_result[0].state.origin[0],
            2.0,
            0.0,
            "FUN_007b2270 first BODY mismatch",
            max_error);
        require_close(
            array_result[1].state.origin[0],
            -2.0,
            0.0,
            "FUN_007b2270 second BODY mismatch",
            max_error);

        bool size_mismatch_rejected = false;
        try {
            (void)execute_fun_007b2270_body_array_with_external_bases(
                bodies,
                {identity_basis()},
                dt);
        } catch (const std::invalid_argument&) {
            size_mismatch_rejected = true;
        }
        if (!size_mismatch_rejected) {
            throw std::runtime_error(
                "FUN_007b2270 accepted mismatched BODY/basis arrays");
        }

        bool non_finite_rejected = false;
        try {
            auto bad = make_state();
            bad.motion_triplet[1] =
                std::numeric_limits<double>::infinity();
            (void)advance_fun_007bab70_pre_basis(bad, dt);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error(
                "FUN_007bab70 accepted non-finite BODY state");
        }

        std::cout
            << "{\"format\":\"SHIFT.NativeBodyFrameIntegration/1\","
            << "\"ready\":true,"
            << "\"body_array_function\":\"FUN_007b2270\","
            << "\"body_integrator_function\":\"FUN_007bab70\","
            << "\"translation_lane_proven\":true,"
            << "\"accumulator_b_to_motion_proven\":true,"
            << "\"rotation_increment_proven\":true,"
            << "\"accumulator_a_to_prepared_proven\":true,"
            << "\"prepared_to_cross_proven\":true,"
            << "\"body_array_loop_proven\":true,"
            << "\"basis_rotation_helper_external\":true,"
            << "\"runtime_scheduling_proven\":false,"
            << "\"non_finite_rejected\":true,"
            << "\"max_absolute_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << "\n";
        return 1;
    }
}
