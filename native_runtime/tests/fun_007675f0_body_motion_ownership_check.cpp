#include "fun_00770e80_outer_update_fixture.hpp"
#include "shift_contact_outer_kernel.hpp"
#include "shift_fun_00770e80_contact_outer_provider_chain.hpp"

#include <cmath>
#include <cstddef>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

namespace {

using namespace shift::runtime::physics;
using namespace shift::runtime::test_fixture;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void require_near(double actual, double expected, const char* message) {
    if (!std::isfinite(actual) || std::abs(actual - expected) > 1e-12) {
        throw std::runtime_error(message);
    }
}

Fun00765470MachineScalarHalfStepInput make_half_step_input(
    const Fun00763570MachineInput& machine,
    const PreparedGeneratedBodyConstraintFrame& source,
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& reset_state,
    const PreparedBuiltinSolverFrame& solver_topology,
    const PreparedPostSolveBodyProjection& projection) {
    Fun00765470MachineScalarHalfStepInput input{};
    input.machine = machine;
    input.source = source;
    input.relations = relations;
    input.reset_state = reset_state;
    input.solver_topology = solver_topology;
    input.projection = projection;
    input.scalar_provider = [](
        std::size_t,
        const ConstraintRefreshFrame3f&,
        const BodyFrameIntegrationVector3d&) {
        Fun007afdd0ScalarBoundary scalars{};
        scalars.squared_magnitude_test = 0.0f;
        scalars.sqrt_magnitude = 0.0f;
        scalars.sine = 0.0f;
        scalars.cosine = 1.0f;
        return scalars;
    };
    return input;
}

Fun0076d100ContactOuterProvider make_contact_outer_motion_pass_provider() {
    return [](std::size_t) {
        Fun0076d100ContactOuterProviderCallbacks callbacks{};
        callbacks.contact_factor = [] {};
        callbacks.wheel_update = [] {};
        callbacks.contact_response = [] {};
        callbacks.contact_outer_input_provider = [] {
            ContactOuterKernelInput legacy = make_contact_outer_input();
            legacy.speed_x = 999.0;
            legacy.speed_z = -777.0;
            return ContactOuterExternalInput{legacy};
        };
        callbacks.motion_read_gate = [] {};
        return callbacks;
    };
}

}  // namespace

int main() {
    try {
        const auto source = make_frame();
        const auto relations = make_relations();
        const auto projection = make_projection(source, relations);
        const auto solver_topology = make_solver_topology(source, relations);
        const auto reset_state = make_reset_state();
        const auto machine = make_machine_input();
        auto initial_body_bytes = make_raw_bodies(projection.bodies);

        const auto initial_motion =
            derive_fun_007675f0_body0_motion(initial_body_bytes);
        require_near(initial_motion.speed_x, 4.0,
                     "FUN_007675f0 BODY0 +0x78 decode mismatch");
        require_near(initial_motion.speed_z, 6.0,
                     "FUN_007675f0 BODY0 +0x88 decode mismatch");

        ContactOuterKernelInput legacy = make_contact_outer_input();
        legacy.speed_x = 123.0;
        legacy.speed_z = -456.0;
        const ContactOuterExternalInput external{legacy};
        const auto composed = compose_fun_007675f0_input(
            external,
            Fun007675f0BodyMotion{3.0, 4.0});
        require_near(composed.speed_x, 3.0,
                     "legacy external speed X overrode BODY motion");
        require_near(composed.speed_z, 4.0,
                     "legacy external speed Z overrode BODY motion");
        const auto composed_result =
            execute_fun_007675f0_outer_arithmetic(composed);
        require_near(composed_result.speed, 5.0,
                     "composed FUN_007675f0 speed did not use BODY motion");

        bool malformed_rejected = false;
        try {
            (void)derive_fun_007675f0_body0_motion(
                std::vector<std::uint8_t>(1u, 0u));
        } catch (const std::invalid_argument&) {
            malformed_rejected = true;
        }
        require(malformed_rejected,
                "malformed BODY buffer accepted by FUN_007675f0 motion owner");

        auto non_finite_body = initial_body_bytes;
        put_f64(
            non_finite_body,
            kFun007675f0Body0SpeedXOffset,
            std::numeric_limits<double>::quiet_NaN());
        bool non_finite_rejected = false;
        try {
            (void)derive_fun_007675f0_body0_motion(non_finite_body);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        require(non_finite_rejected,
                "non-finite BODY0 motion accepted by FUN_007675f0 owner");

        constexpr double outer_timestep = 0.5;
        const auto chained = execute_fun_00770e80_contact_outer_provider_chain(
            outer_timestep,
            initial_body_bytes,
            make_contact_outer_motion_pass_provider(),
            [&](std::size_t,
                double,
                const std::vector<std::uint8_t>&) {
                return make_half_step_input(
                    machine,
                    source,
                    relations,
                    reset_state,
                    solver_topology,
                    projection);
            },
            [](std::size_t) {});

        require(chained.body_motion_input_present[0] &&
                    chained.body_motion_input_present[1],
                "per-pass FUN_007675f0 BODY motion snapshots missing");
        require(chained.joined.joined.current_body_observer_call_count == 2u,
                "current BODY observer did not run once per physics pass");
        require_near(chained.body_motion_inputs[0].speed_x, 4.0,
                     "pass 0 did not consume initial BODY0 +0x78");
        require_near(chained.body_motion_inputs[0].speed_z, 6.0,
                     "pass 0 did not consume initial BODY0 +0x88");
        require_near(
            chained.contact_outer_results[0].speed,
            std::hypot(4.0, 6.0),
            "pass 0 FUN_007675f0 speed used external sentinel values");

        const auto after_first_half =
            chained.joined.joined.half_steps[0]
                .joined.half_step.feedback_integration.body_bytes;
        const auto expected_pass1_motion =
            derive_fun_007675f0_body0_motion(after_first_half);
        require_near(
            chained.body_motion_inputs[1].speed_x,
            expected_pass1_motion.speed_x,
            "pass 1 did not refresh BODY0 +0x78 after first half-step");
        require_near(
            chained.body_motion_inputs[1].speed_z,
            expected_pass1_motion.speed_z,
            "pass 1 did not refresh BODY0 +0x88 after first half-step");

        std::cout
            << "{\"format\":\"" << kFun007675f0BodyMotionOwnershipFormat << "\","
            << "\"ready\":true,"
            << "\"speed_x_source\":\"BODY0+0x78\","
            << "\"speed_z_source\":\"BODY0+0x88\","
            << "\"external_speed_fields_removed\":true,"
            << "\"legacy_speed_values_ignored\":true,"
            << "\"pass0_reads_current_body\":true,"
            << "\"pass1_reads_post_half_step_body\":true,"
            << "\"malformed_body_rejected\":true,"
            << "\"non_finite_body_motion_rejected\":true,"
            << "\"external_provider_count_reduced\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
