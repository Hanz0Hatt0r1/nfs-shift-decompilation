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

Fun0076d100MotionReadEffectProvider make_motion_read_pass_provider(
    std::size_t* contact_input_calls,
    std::size_t* effect_provider_calls,
    std::size_t* delta_consumer_calls) {
    return [=](std::size_t pass_index) {
        const auto base = make_contact_outer_pass_provider(contact_input_calls)(pass_index);
        Fun0076d100MotionReadEffectProviderCallbacks callbacks{};
        callbacks.contact_factor = base.contact_factor;
        callbacks.wheel_update = base.wheel_update;
        callbacks.contact_response = base.contact_response;
        callbacks.contact_outer_input_provider = base.contact_outer_input_provider;
        callbacks.motion_read_effect_provider = [effect_provider_calls] {
            if (effect_provider_calls != nullptr) {
                ++(*effect_provider_calls);
            }
            return Fun007682c0AccumulatorEffect{true, -2.5};
        };
        callbacks.motion_read_delta_consumer = [delta_consumer_calls](double value) {
            if (value != -2.5) {
                throw std::runtime_error("Phase 697 motion-read delta mismatch");
            }
            if (delta_consumer_calls != nullptr) {
                ++(*delta_consumer_calls);
            }
        };
        return callbacks;
    };
}

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

        if (runtime.outer_update.explicit_update_count != 0u ||
            runtime.outer_update.body_pose_snapshot_generation != 0u ||
            runtime.outer_update.last_motion_read_effect_provider_call_count != 0u ||
            runtime.outer_update.last_motion_read_delta_consumer_call_count != 0u ||
            runtime.outer_update.last_motion_read_gate_open_count != 0u) {
            throw std::runtime_error("Phase 697 initial telemetry mismatch");
        }

        std::array<std::vector<std::uint8_t>, 2> first_half_inputs{};
        std::size_t scalar_calls = 0u;
        std::size_t contact_input_calls = 0u;
        std::size_t effect_provider_calls = 0u;
        std::size_t delta_consumer_calls = 0u;

        auto run_outer = [&](std::size_t outer_index) {
            return runtime.execute_explicit_outer_update_with_fun_007682c0_motion_read_effect_provider(
                outer_timestep,
                make_motion_read_pass_provider(
                    &contact_input_calls,
                    &effect_provider_calls,
                    &delta_consumer_calls),
                [&](std::size_t pass_index,
                    double half_timestep,
                    const std::vector<std::uint8_t>& body_bytes) {
                    if (half_timestep != outer_timestep * 0.5) {
                        throw std::runtime_error("Phase 697 half timestep mismatch");
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
                                throw std::runtime_error("Phase 697 BODY index mismatch");
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
        if (first.motion_read_effect_provider_call_count != 2u ||
            first.motion_read_delta_consumer_call_count != 2u ||
            first.motion_read_gate_open_count != 2u ||
            first.joined.contact_outer_input_provider_call_count != 2u ||
            first.joined.contact_outer_native_call_count != 2u ||
            first.joined.joined.scalar_provider_call_count != 4u ||
            first.joined.joined.zero_noop_count != 4u) {
            throw std::runtime_error("Phase 697 first provider counts mismatch");
        }
        if (runtime.outer_update.explicit_update_count != 1u ||
            runtime.outer_update.body_pose_snapshot_generation != 1u ||
            runtime.outer_update.last_motion_read_effect_provider_call_count != 2u ||
            runtime.outer_update.last_motion_read_delta_consumer_call_count != 2u ||
            runtime.outer_update.last_motion_read_gate_open_count != 2u ||
            runtime.outer_update.last_contact_outer_input_provider_call_count != 2u ||
            runtime.outer_update.last_contact_outer_native_call_count != 2u ||
            runtime.outer_update.last_scalar_provider_call_count != 4u ||
            runtime.outer_update.last_half_step_provider_call_count != 2u ||
            runtime.outer_update.last_physics_pass_provider_call_count != 2u) {
            throw std::runtime_error("Phase 697 first runtime telemetry mismatch");
        }
        if (first_half_inputs[0] != initial_body_bytes) {
            throw std::runtime_error("Phase 697 first persistent input mismatch");
        }

        const auto first_persistent = first.joined.joined.joined.final_body_bytes;
        if (runtime.outer_update.body_bytes != first_persistent ||
            first_persistent == initial_body_bytes ||
            runtime.outer_update.body_pose_snapshots.size() != 2u) {
            throw std::runtime_error("Phase 697 first persistent BODY commit mismatch");
        }

        const auto second = run_outer(1u);
        if (first_half_inputs[1] != first_persistent) {
            throw std::runtime_error(
                "Phase 697 second update did not receive first persistent BODY bytes");
        }
        if (second.motion_read_effect_provider_call_count != 2u ||
            second.motion_read_delta_consumer_call_count != 2u ||
            second.joined.contact_outer_native_call_count != 2u ||
            second.joined.joined.scalar_provider_call_count != 4u ||
            runtime.outer_update.explicit_update_count != 2u ||
            runtime.outer_update.body_pose_snapshot_generation != 2u ||
            runtime.outer_update.body_bytes !=
                second.joined.joined.joined.final_body_bytes ||
            runtime.outer_update.body_bytes == first_persistent ||
            contact_input_calls != 4u ||
            effect_provider_calls != 4u ||
            delta_consumer_calls != 4u ||
            scalar_calls != 8u) {
            throw std::runtime_error("Phase 697 second persistent update mismatch");
        }

        if (runtime.physics.fixed_step != 0u) {
            throw std::runtime_error("Phase 697 outer update leaked into fixed_step scheduling");
        }

        const auto committed_body_bytes = runtime.outer_update.body_bytes;
        const auto committed_pose_generation =
            runtime.outer_update.body_pose_snapshot_generation;
        runtime.physics.participant_ready = false;
        std::size_t gated_provider_calls = 0u;
        bool participant_gate_rejected = false;
        try {
            (void)runtime.execute_explicit_outer_update_with_fun_007682c0_motion_read_effect_provider(
                outer_timestep,
                [&](std::size_t) {
                    ++gated_provider_calls;
                    return make_motion_read_pass_provider(nullptr, nullptr, nullptr)(0u);
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
        if (!participant_gate_rejected ||
            gated_provider_calls != 0u ||
            runtime.outer_update.explicit_update_count != 2u ||
            runtime.outer_update.body_pose_snapshot_generation != committed_pose_generation ||
            runtime.outer_update.body_bytes != committed_body_bytes) {
            throw std::runtime_error("Phase 697 participant admission failed open");
        }

        std::size_t incomplete_bundle_calls = 0u;
        std::size_t unexpected_half_step_calls = 0u;
        bool missing_effect_provider_rejected = false;
        try {
            (void)runtime.execute_explicit_outer_update_with_fun_007682c0_motion_read_effect_provider(
                outer_timestep,
                [&](std::size_t pass_index) {
                    ++incomplete_bundle_calls;
                    auto callbacks =
                        make_motion_read_pass_provider(nullptr, nullptr, nullptr)(pass_index);
                    callbacks.motion_read_effect_provider = {};
                    return callbacks;
                },
                [&](std::size_t,
                    double,
                    const std::vector<std::uint8_t>&) {
                    ++unexpected_half_step_calls;
                    return Fun00765470MachineScalarHalfStepInput{};
                },
                [](std::size_t) {});
        } catch (const std::invalid_argument&) {
            missing_effect_provider_rejected = true;
        }
        if (!missing_effect_provider_rejected ||
            incomplete_bundle_calls != 1u ||
            unexpected_half_step_calls != 0u ||
            runtime.outer_update.explicit_update_count != 2u ||
            runtime.outer_update.body_pose_snapshot_generation != committed_pose_generation ||
            runtime.outer_update.body_bytes != committed_body_bytes) {
            throw std::runtime_error("Phase 697 incomplete typed pass admitted state");
        }

        std::cout
            << "{\"format\":\"SHIFT.NativeFun00770e80MotionReadRuntimeState/1\","
            << "\"ready\":true,"
            << "\"explicit_update_count\":"
            << runtime.outer_update.explicit_update_count << ","
            << "\"body_pose_snapshot_generation\":"
            << runtime.outer_update.body_pose_snapshot_generation << ","
            << "\"motion_read_effect_provider_call_count\":"
            << second.motion_read_effect_provider_call_count << ","
            << "\"motion_read_delta_consumer_call_count\":"
            << second.motion_read_delta_consumer_call_count << ","
            << "\"persistent_body_bytes_carried_between_explicit_updates\":true,"
            << "\"persistent_pose_snapshots_committed\":true,"
            << "\"participant_gate_before_provider_side_effects\":true,"
            << "\"phase696_motion_read_chain_reused\":true,"
            << "\"fixed_step_auto_schedule\":false,"
            << "\"motion_read_body_identity_application_external\":true,"
            << "\"motion_read_machine_scalar_production_external\":true,"
            << "\"host_sqrt_substitution_allowed\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
