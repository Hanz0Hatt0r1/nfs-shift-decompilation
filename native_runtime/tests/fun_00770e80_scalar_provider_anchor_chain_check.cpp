#include "fun_00770e80_outer_update_fixture.hpp"

#include <array>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {

using namespace shift::runtime;
using namespace shift::runtime::physics;
using namespace shift::runtime::test_fixture;

}  // namespace

int main() {
    try {
        constexpr double outer_timestep = 0.5;
        const auto source = make_frame();
        const auto relations = make_relations();
        const auto projection = make_projection(source, relations);
        const auto solver_topology = make_solver_topology(source, relations);
        const auto reset_state = make_reset_state();
        const auto initial_body_bytes = make_raw_bodies(projection.bodies);
        const auto machine_input = make_machine_input();

        NativeRuntimeState runtime{};
        runtime.physics.workspace.configure(2u, 1u, 1u);
        runtime.physics.participant_contract_ready = true;
        runtime.physics.participant_registry_ready = true;
        runtime.physics.selector_context_separate = true;
        runtime.physics.participant_ready = true;
        runtime.physics.participant_identity_join_proven = true;
        runtime.initialize_explicit_outer_update_body_state(initial_body_bytes);

        std::array<std::vector<std::uint8_t>, 2> first_half_inputs{};
        std::size_t scalar_calls = 0u;

        auto run_outer = [&](std::size_t outer_index) {
            return runtime.execute_explicit_outer_update_with_fun_007afdd0_scalar_provider(
                outer_timestep,
                make_pass_provider(),
                [&](std::size_t pass_index,
                    double half_timestep,
                    const std::vector<std::uint8_t>& body_bytes) {
                    if (half_timestep != outer_timestep * 0.5) {
                        throw std::runtime_error("Phase 691 half timestep mismatch");
                    }
                    if (pass_index == 0u) {
                        first_half_inputs[outer_index] = body_bytes;
                    }
                    Fun00765470MachineScalarHalfStepInput input{};
                    input.machine = machine_input;
                    input.source = source;
                    input.relations = relations;
                    input.reset_state = reset_state;
                    input.solver_topology = solver_topology;
                    input.projection = projection;
                    input.scalar_provider =
                        [&](std::size_t body_index,
                            const ConstraintRefreshFrame3f&,
                            const BodyFrameIntegrationVector3d&) {
                            if (body_index >= 2u) {
                                throw std::runtime_error("Phase 691 BODY index mismatch");
                            }
                            ++scalar_calls;
                            Fun007afdd0ScalarBoundary scalars{};
                            scalars.squared_magnitude_test = 0.0f;
                            scalars.sqrt_magnitude = 0.0f;
                            scalars.sine = 0.0f;
                            scalars.cosine = 1.0f;
                            return scalars;
                        };
                    return input;
                },
                [](std::size_t) {});
        };

        const auto first = run_outer(0u);
        if (first.scalar_provider_call_count != 4u ||
            first.applied_rotation_count != 0u ||
            first.zero_noop_count != 4u ||
            first.scalar_provider_call_counts[0] != 2u ||
            first.scalar_provider_call_counts[1] != 2u) {
            throw std::runtime_error("Phase 691 first scalar-provider counts mismatch");
        }
        if (runtime.outer_update.last_scalar_provider_call_count != 4u ||
            runtime.outer_update.last_applied_rotation_count != 0u ||
            runtime.outer_update.last_zero_noop_count != 4u ||
            runtime.outer_update.last_contact_outer_input_provider_call_count != 0u ||
            runtime.outer_update.last_contact_outer_native_call_count != 0u ||
            runtime.outer_update.explicit_update_count != 1u) {
            throw std::runtime_error("Phase 691 first runtime state metadata mismatch");
        }
        if (first_half_inputs[0] != initial_body_bytes) {
            throw std::runtime_error("Phase 691 first outer input mismatch");
        }

        const auto first_body0 = decode_fun_007bab70_body_record(
            record_at(first.joined.final_body_bytes, 0u));
        const std::array<double, 3> expected_first_origin = {
            3.125, 4.65625, 6.1875};
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(
                first_body0.origin[component],
                expected_first_origin[component],
                "Phase 691 first persistent BODY origin mismatch");
        }

        const auto first_persistent = first.joined.final_body_bytes;
        const auto second = run_outer(1u);
        if (first_half_inputs[1] != first_persistent) {
            throw std::runtime_error(
                "Phase 691 second outer update did not receive persistent BODY bytes");
        }
        if (second.scalar_provider_call_count != 4u ||
            second.zero_noop_count != 4u ||
            runtime.outer_update.explicit_update_count != 2u ||
            runtime.outer_update.body_bytes != second.joined.final_body_bytes ||
            runtime.outer_update.body_bytes == first_persistent ||
            scalar_calls != 8u) {
            throw std::runtime_error("Phase 691 second outer update mismatch");
        }

        std::size_t invalid_half_provider_calls = 0u;
        bool missing_scalar_provider_rejected = false;
        try {
            (void)runtime.execute_explicit_outer_update_with_fun_007afdd0_scalar_provider(
                outer_timestep,
                make_pass_provider(),
                [&](std::size_t,
                    double,
                    const std::vector<std::uint8_t>&) {
                    ++invalid_half_provider_calls;
                    Fun00765470MachineScalarHalfStepInput input{};
                    input.machine = machine_input;
                    input.source = source;
                    input.relations = relations;
                    input.reset_state = reset_state;
                    input.solver_topology = solver_topology;
                    input.projection = projection;
                    return input;
                },
                [](std::size_t) {});
        } catch (const std::invalid_argument&) {
            missing_scalar_provider_rejected = true;
        }
        if (!missing_scalar_provider_rejected || invalid_half_provider_calls != 1u) {
            throw std::runtime_error("Phase 691 missing scalar provider accepted");
        }

        runtime.physics.participant_ready = false;
        std::size_t gated_provider_calls = 0u;
        bool participant_gate_rejected = false;
        try {
            (void)runtime.execute_explicit_outer_update_with_fun_007afdd0_scalar_provider(
                outer_timestep,
                [&](std::size_t) {
                    ++gated_provider_calls;
                    return make_pass_provider()(0u);
                },
                [&](std::size_t,
                    double,
                    const std::vector<std::uint8_t>&) {
                    ++gated_provider_calls;
                    return Fun00765470MachineScalarHalfStepInput{};
                },
                [](std::size_t) {});
        } catch (const std::runtime_error&) {
            participant_gate_rejected = true;
        }
        runtime.physics.participant_ready = true;
        if (!participant_gate_rejected || gated_provider_calls != 0u) {
            throw std::runtime_error("Phase 691 participant gate failed open");
        }

        std::cout
            << "{\"format\":\"" << kNativeFun00770e80ScalarProviderAnchorChainFormat << "\","
            << "\"ready\":true,"
            << "\"scalar_provider_call_count\":" << second.scalar_provider_call_count << ","
            << "\"zero_noop_count\":" << second.zero_noop_count << ","
            << "\"applied_rotation_count\":" << second.applied_rotation_count << ","
            << "\"phase689_composed_anchor_chain_reused\":true,"
            << "\"fun_007afdd0_source_core_used\":true,"
            << "\"arbitrary_basis_callback_external\":false,"
            << "\"machine_scalar_production_external\":true,"
            << "\"persistent_body_bytes_carried_between_explicit_updates\":true,"
            << "\"fixed_step_auto_schedule\":false,"
            << "\"host_libm_substitution\":false,"
            << "\"rendered_frame_cadence_proven\":false,"
            << "\"complete_fun_007afdd0_machine_semantics\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
