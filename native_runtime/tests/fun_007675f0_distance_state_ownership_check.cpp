#include "fun_00770e80_outer_update_fixture.hpp"
#include "shift_fun_007675f0_distance_state_setup.hpp"
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

}  // namespace

int main() {
    try {
        Fun007675f0DistanceStateSetup missing{};
        bool missing_rejected = false;
        try {
            validate_fun_007675f0_distance_state_setup(missing);
        } catch (const std::invalid_argument&) {
            missing_rejected = true;
        }
        require(missing_rejected,
                "FUN_007675f0 missing distance-state setup failed open");

        Fun007675f0DistanceStateSetup non_finite{};
        non_finite.ready = true;
        non_finite.previous_distance_state =
            std::numeric_limits<double>::quiet_NaN();
        bool non_finite_rejected = false;
        try {
            validate_fun_007675f0_distance_state_setup(non_finite);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        require(non_finite_rejected,
                "FUN_007675f0 non-finite setup seed failed open");

        ContactOuterKernelInput legacy = make_contact_outer_input();
        legacy.previous_distance_state = 91.0;
        const ContactOuterSessionInput session_input{legacy};
        require(session_input.compatibility_previous_distance_seed_present &&
                    session_input.compatibility_previous_distance_seed == 91.0,
                "legacy compatibility seed was not preserved exactly");
        const auto resolved = compose_fun_007675f0_external_input(session_input, 2.0);
        require_near(resolved.previous_distance_state, 2.0,
                     "session-owned state did not override legacy seed");

        const auto source = make_frame();
        const auto relations = make_relations();
        const auto projection = make_projection(source, relations);
        const auto solver_topology = make_solver_topology(source, relations);
        const auto reset_state = make_reset_state();
        const auto machine = make_machine_input();
        const auto body_bytes = make_raw_bodies(projection.bodies);

        double persistent_state = 2.0;
        std::vector<double> consumed_previous;
        std::vector<double> committed_states;

        const auto result = execute_fun_00770e80_contact_outer_provider_chain(
            0.5,
            body_bytes,
            [&](std::size_t) {
                Fun0076d100ContactOuterProviderCallbacks callbacks{};
                callbacks.contact_factor = [] {};
                callbacks.wheel_update = [] {};
                callbacks.contact_response = [] {};
                callbacks.contact_outer_input_provider = [&] {
                    ContactOuterSessionInput per_pass{};
                    per_pass.planar_delta = {10.0, 0.0, 0.0};
                    per_pass.distance_filter_cap = 1.0;
                    per_pass.surface_scalar = 10.0;
                    per_pass.base_scalar = 4.0;
                    per_pass.projected_scalar = 1.0;
                    per_pass.alignment_scalar = 0.5;
                    per_pass.param_3 = 2.0;
                    consumed_previous.push_back(persistent_state);
                    return compose_fun_007675f0_external_input(
                        per_pass,
                        persistent_state);
                };
                callbacks.contact_outer_distance_state_commit = [&](double next) {
                    persistent_state = next;
                    committed_states.push_back(next);
                };
                callbacks.motion_read_gate = [] {};
                return callbacks;
            },
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

        const double pass0_expected =
            execute_fun_00783a30_distance_filter(2.0, 10.0, 1.0, 0.5);
        const double pass1_expected =
            execute_fun_00783a30_distance_filter(pass0_expected, 10.0, 1.0, 0.5);
        require(consumed_previous.size() == 2u && committed_states.size() == 2u,
                "FUN_007675f0 distance state cardinality mismatch");
        require_near(consumed_previous[0], 2.0,
                     "pass 0 did not consume setup-owned distance state");
        require_near(committed_states[0], pass0_expected,
                     "pass 0 distance-state commit mismatch");
        require_near(consumed_previous[1], pass0_expected,
                     "pass 1 did not consume pass 0 distance-state result");
        require_near(committed_states[1], pass1_expected,
                     "pass 1 distance-state commit mismatch");
        require_near(persistent_state, pass1_expected,
                     "persistent distance state did not retain pass 1 result");
        require(result.contact_outer_distance_state_commit_count == 2u &&
                    result.contact_outer_distance_state_commit_counts[0] == 1u &&
                    result.contact_outer_distance_state_commit_counts[1] == 1u,
                "distance-state commit telemetry mismatch");

        ContactOuterKernelInput over_limit{};
        over_limit.planar_delta = {201.0, 0.0, 0.0};
        over_limit.previous_distance_state = 3.0;
        over_limit.distance_filter_cap = 1.0;
        over_limit.speed_x = 4.0;
        over_limit.speed_z = 6.0;
        over_limit.surface_scalar = 10.0;
        over_limit.base_scalar = 4.0;
        over_limit.projected_scalar = 1.0;
        over_limit.alignment_scalar = 0.5;
        over_limit.param_3 = 2.0;
        require_near(
            execute_fun_007675f0_outer_arithmetic(over_limit).filtered_distance_state,
            kContactDistanceLimit,
            "distance > 200 did not clamp persistent state to 200");

        std::cout
            << "{\"format\":\"" << kFun007675f0DistanceStateOwnershipFormat << "\","
            << "\"ready\":true,"
            << "\"state_offset\":\"HDVehicle+0x4080\","
            << "\"pass0_commits_before_pass1\":true,"
            << "\"commit_count_per_step\":2,"
            << "\"distance_over_200_clamps_state\":true,"
            << "\"setup_seed_fail_closed\":true,"
            << "\"legacy_seed_is_compatibility_only\":true,"
            << "\"external_provider_count_reduced\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
