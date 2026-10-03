#include "fun_00770e80_outer_update_fixture.hpp"
#include "shift_persistent_body_pose_snapshot.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

namespace {

using namespace shift::runtime;
using namespace shift::runtime::physics;
using namespace shift::runtime::test_fixture;

void require_snapshot_matches_body(
    const PersistentBodyPoseSnapshot& snapshot,
    const std::vector<std::uint8_t>& body_bytes,
    std::size_t body_index) {
    const auto state = decode_fun_007bab70_body_record(
        record_at(body_bytes, body_index));
    if (snapshot.body_index != body_index) {
        throw std::runtime_error("Phase 695 BODY snapshot index mismatch");
    }
    for (std::size_t component = 0u; component < 3u; ++component) {
        require_close(
            snapshot.origin[component],
            state.origin[component],
            "Phase 695 BODY origin snapshot/bytes mismatch");
    }
    for (std::size_t component = 0u; component < 9u; ++component) {
        if (snapshot.basis[component] != state.basis[component]) {
            throw std::runtime_error(
                "Phase 695 BODY basis snapshot/bytes mismatch");
        }
    }
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

        if (runtime.outer_update.body_pose_snapshot_generation != 0u ||
            runtime.outer_update.body_pose_snapshots.size() != 2u) {
            throw std::runtime_error("Phase 695 initial snapshot metadata mismatch");
        }
        require_snapshot_matches_body(
            runtime.outer_update.body_pose_snapshots[0],
            initial_body_bytes,
            0u);
        require_snapshot_matches_body(
            runtime.outer_update.body_pose_snapshots[1],
            initial_body_bytes,
            1u);
        require_close(
            runtime.outer_update.body_pose_snapshots[0].origin[0],
            1.0,
            "Phase 695 initial BODY0 origin.x mismatch");
        require_close(
            runtime.outer_update.body_pose_snapshots[0].origin[1],
            2.0,
            "Phase 695 initial BODY0 origin.y mismatch");
        require_close(
            runtime.outer_update.body_pose_snapshots[0].origin[2],
            3.0,
            "Phase 695 initial BODY0 origin.z mismatch");

        std::size_t scalar_calls = 0u;
        auto run_outer = [&] {
            return runtime.execute_explicit_outer_update_with_fun_007675f0_contact_outer_provider(
                outer_timestep,
                make_contact_outer_pass_provider(),
                [&](std::size_t,
                    double half_timestep,
                    const std::vector<std::uint8_t>&) {
                    if (half_timestep != outer_timestep * 0.5) {
                        throw std::runtime_error("Phase 695 half timestep mismatch");
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
                                throw std::runtime_error("Phase 695 BODY index mismatch");
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

        const auto first = run_outer();
        if (runtime.outer_update.explicit_update_count != 1u ||
            runtime.outer_update.body_pose_snapshot_generation != 1u ||
            runtime.outer_update.body_pose_snapshots.size() != 2u ||
            runtime.outer_update.body_bytes != first.joined.joined.final_body_bytes) {
            throw std::runtime_error("Phase 695 first snapshot commit mismatch");
        }
        require_snapshot_matches_body(
            runtime.outer_update.body_pose_snapshots[0],
            runtime.outer_update.body_bytes,
            0u);
        require_snapshot_matches_body(
            runtime.outer_update.body_pose_snapshots[1],
            runtime.outer_update.body_bytes,
            1u);
        const std::array<double, 3> expected_first_origin = {
            3.125, 4.65625, 6.1875};
        for (std::size_t component = 0u; component < 3u; ++component) {
            require_close(
                runtime.outer_update.body_pose_snapshots[0].origin[component],
                expected_first_origin[component],
                "Phase 695 first BODY0 origin mismatch");
        }
        const auto first_origin =
            runtime.outer_update.body_pose_snapshots[0].origin;
        const auto first_body_bytes = runtime.outer_update.body_bytes;

        const auto second = run_outer();
        if (runtime.outer_update.explicit_update_count != 2u ||
            runtime.outer_update.body_pose_snapshot_generation != 2u ||
            runtime.outer_update.body_bytes != second.joined.joined.final_body_bytes ||
            runtime.outer_update.body_bytes == first_body_bytes ||
            scalar_calls != 8u) {
            throw std::runtime_error("Phase 695 second snapshot commit mismatch");
        }
        require_snapshot_matches_body(
            runtime.outer_update.body_pose_snapshots[0],
            runtime.outer_update.body_bytes,
            0u);
        if (runtime.outer_update.body_pose_snapshots[0].origin == first_origin) {
            throw std::runtime_error("Phase 695 BODY pose did not evolve on second update");
        }
        if (runtime.physics.fixed_step != 0u) {
            throw std::runtime_error("Phase 695 snapshot path claimed fixed-step cadence");
        }

        const auto committed_bytes = runtime.outer_update.body_bytes;
        const auto committed_origin =
            runtime.outer_update.body_pose_snapshots[0].origin;
        const auto committed_generation =
            runtime.outer_update.body_pose_snapshot_generation;
        runtime.physics.participant_ready = false;
        bool admission_rejected = false;
        try {
            (void)run_outer();
        } catch (const std::runtime_error&) {
            admission_rejected = true;
        }
        runtime.physics.participant_ready = true;
        if (!admission_rejected ||
            runtime.outer_update.body_bytes != committed_bytes ||
            runtime.outer_update.body_pose_snapshots[0].origin != committed_origin ||
            runtime.outer_update.body_pose_snapshot_generation != committed_generation) {
            throw std::runtime_error("Phase 695 admission failure mutated committed pose");
        }

        auto nonfinite_body_bytes = initial_body_bytes;
        put_f64(
            nonfinite_body_bytes,
            body_record_offset::kOrigin[0],
            std::numeric_limits<double>::quiet_NaN());
        bool nonfinite_decoder_rejected = false;
        try {
            (void)decode_persistent_body_pose_snapshots(nonfinite_body_bytes, 2u);
        } catch (const std::invalid_argument&) {
            nonfinite_decoder_rejected = true;
        }
        if (!nonfinite_decoder_rejected) {
            throw std::runtime_error("Phase 695 non-finite BODY pose accepted");
        }

        NativeRuntimeState invalid_runtime{};
        invalid_runtime.physics.workspace.configure(2u, 1u, 1u);
        bool nonfinite_initialization_rejected = false;
        try {
            invalid_runtime.initialize_explicit_outer_update_body_state(
                nonfinite_body_bytes);
        } catch (const std::invalid_argument&) {
            nonfinite_initialization_rejected = true;
        }
        if (!nonfinite_initialization_rejected ||
            invalid_runtime.outer_update.initialized ||
            !invalid_runtime.outer_update.body_bytes.empty() ||
            !invalid_runtime.outer_update.body_pose_snapshots.empty()) {
            throw std::runtime_error(
                "Phase 695 non-finite initialization committed partial state");
        }

        std::cout
            << "{\"format\":\"" << kNativePersistentBodyPoseSnapshotFormat << "\","
            << "\"ready\":true,"
            << "\"body_count\":" << runtime.outer_update.body_pose_snapshots.size() << ","
            << "\"snapshot_generation\":"
            << runtime.outer_update.body_pose_snapshot_generation << ","
            << "\"explicit_update_count\":"
            << runtime.outer_update.explicit_update_count << ","
            << "\"origin_storage_f64x3\":true,"
            << "\"basis_storage_f32x9\":true,"
            << "\"persistent_snapshot_matches_committed_body_bytes\":true,"
            << "\"body_to_vehicle_identity_proven\":false,"
            << "\"vehicle_world_transform_proven\":false,"
            << "\"renderer_transport_enabled\":false,"
            << "\"fixed_step_auto_schedule\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
