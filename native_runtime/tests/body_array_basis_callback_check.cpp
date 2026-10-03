#include "shift_body_frame_integration.hpp"

#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

namespace {

shift::runtime::physics::ConstraintRefreshFrame3f identity_basis() {
    return {
        1.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f,
        0.0f, 0.0f, 1.0f,
    };
}

shift::runtime::physics::BodyFrameIntegrationState make_state(
    double cross_x,
    double origin_x) {
    using namespace shift::runtime::physics;
    BodyFrameIntegrationState state{};
    state.origin = {origin_x, 2.0, 3.0};
    state.cross_vector = {cross_x, 0.0, 0.0};
    state.prepared_vector = {1.0, 2.0, 3.0};
    state.accumulators.angular = {0.0, 0.0, 0.0};
    state.accumulators.linear = {0.0, 0.0, 0.0};
    state.motion_triplet = {4.0, 0.0, 0.0};
    state.scalar_0x90 = 1.0;
    state.reciprocal_coefficients = {1.0, 1.0, 1.0};
    state.basis = identity_basis();
    return state;
}

void require_close(double actual, double expected, const char* label) {
    if (!std::isfinite(actual) || std::abs(actual - expected) > 1e-15) {
        throw std::runtime_error(label);
    }
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        constexpr double timestep = 0.25;
        const std::vector<BodyFrameIntegrationState> bodies = {
            make_state(1.0, 0.0),
            make_state(2.0, 10.0),
            make_state(3.0, 20.0),
        };

        std::vector<double> callback_rotation_x;
        const auto result =
            execute_fun_007b2270_body_array_with_basis_callback(
                bodies,
                timestep,
                [&callback_rotation_x](
                    const ConstraintRefreshFrame3f& basis,
                    const BodyFrameIntegrationVector3d& rotation_increment) {
                    callback_rotation_x.push_back(rotation_increment[0]);
                    return basis;
                });

        if (result.size() != bodies.size() || callback_rotation_x.size() != bodies.size()) {
            throw std::runtime_error("FUN_007b2270 callback count mismatch");
        }
        require_close(callback_rotation_x[0], 0.25, "BODY[0] callback ordering mismatch");
        require_close(callback_rotation_x[1], 0.50, "BODY[1] callback ordering mismatch");
        require_close(callback_rotation_x[2], 0.75, "BODY[2] callback ordering mismatch");
        require_close(result[0].state.origin[0], 1.0, "BODY[0] integration mismatch");
        require_close(result[1].state.origin[0], 11.0, "BODY[1] integration mismatch");
        require_close(result[2].state.origin[0], 21.0, "BODY[2] integration mismatch");

        bool missing_provider_rejected = false;
        try {
            (void)execute_fun_007b2270_body_array_with_basis_callback(
                bodies,
                timestep,
                BodyBasisRotationCallback{});
        } catch (const std::invalid_argument&) {
            missing_provider_rejected = true;
        }
        if (!missing_provider_rejected) {
            throw std::runtime_error("FUN_007b2270 accepted missing basis provider");
        }

        bool non_finite_provider_rejected = false;
        try {
            (void)execute_fun_007b2270_body_array_with_basis_callback(
                bodies,
                timestep,
                [](const ConstraintRefreshFrame3f& basis,
                   const BodyFrameIntegrationVector3d&) {
                    auto result_basis = basis;
                    result_basis[4] = std::numeric_limits<float>::infinity();
                    return result_basis;
                });
        } catch (const std::invalid_argument&) {
            non_finite_provider_rejected = true;
        }
        if (!non_finite_provider_rejected) {
            throw std::runtime_error("FUN_007b2270 accepted non-finite provider basis");
        }

        bool non_finite_input_rejected = false;
        std::size_t provider_calls = 0u;
        try {
            auto bad_bodies = bodies;
            bad_bodies[0].cross_vector[0] =
                std::numeric_limits<double>::quiet_NaN();
            (void)execute_fun_007b2270_body_array_with_basis_callback(
                bad_bodies,
                timestep,
                [&provider_calls](const ConstraintRefreshFrame3f& basis,
                                  const BodyFrameIntegrationVector3d&) {
                    ++provider_calls;
                    return basis;
                });
        } catch (const std::invalid_argument&) {
            non_finite_input_rejected = true;
        }
        if (!non_finite_input_rejected || provider_calls != 0u) {
            throw std::runtime_error(
                "FUN_007b2270 did not fail before provider on non-finite input");
        }

        std::size_t empty_calls = 0u;
        const auto empty_result =
            execute_fun_007b2270_body_array_with_basis_callback(
                {},
                timestep,
                [&empty_calls](const ConstraintRefreshFrame3f& basis,
                               const BodyFrameIntegrationVector3d&) {
                    ++empty_calls;
                    return basis;
                });
        if (!empty_result.empty() || empty_calls != 0u) {
            throw std::runtime_error("FUN_007b2270 empty array callback mismatch");
        }

        std::cout
            << "{\"format\":\"SHIFT.NativeBodyArrayBasisCallback/1\","
            << "\"ready\":true,"
            << "\"body_array_function\":\"FUN_007b2270\","
            << "\"body_integrator_function\":\"FUN_007bab70\","
            << "\"basis_rotation_function\":\"FUN_007afdd0\","
            << "\"body_stride\":" << kBodyArraySourceStride << ","
            << "\"retail_iteration_order_proven\":true,"
            << "\"basis_provider_inside_each_body_proven\":true,"
            << "\"basis_rotation_arithmetic_external\":true,"
            << "\"non_finite_rejected\":true,"
            << "\"render_frame_scheduler_proven\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << "\n";
        return 1;
    }
}
