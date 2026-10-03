#include "runtime_state.hpp"
#include "shift_vehicle_body_pose_selection.hpp"
#include "fun_00770e80_outer_update_fixture.hpp"

#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

namespace {

using namespace shift::runtime;
using namespace shift::runtime::physics;
using namespace shift::runtime::test_fixture;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

}  // namespace

int main() {
    try {
        const auto source = make_frame();
        const auto relations = make_relations();
        const auto projection = make_projection(source, relations);
        const auto initial_body_bytes = make_raw_bodies(projection.bodies);

        NativeRuntimeState runtime{};
        runtime.physics.workspace.configure(2u, 1u, 1u);
        runtime.initialize_explicit_outer_update_body_state(initial_body_bytes);

        require(runtime.outer_update.body_pose_snapshots.size() == 2u,
                "Phase 698 requires the Phase 695 persistent pose snapshot set");
        require(runtime.outer_update.body_pose_snapshot_generation == 0u,
                "Phase 698 initial snapshot generation mismatch");
        require(runtime.outer_update.explicit_update_count == 0u,
                "Phase 698 initial explicit update count mismatch");

        bool unproven_rejected = false;
        try {
            (void)select_proven_vehicle_body_pose(
                runtime.outer_update.body_pose_snapshots,
                runtime.outer_update.body_pose_snapshot_generation,
                runtime.outer_update.explicit_update_count,
                VehicleBodyIdentitySelection{false, 1u});
        } catch (const std::invalid_argument&) {
            unproven_rejected = true;
        }
        require(unproven_rejected,
                "Phase 698 accepted a BODY selection without identity proof");

        const auto selected = select_proven_vehicle_body_pose(
            runtime.outer_update.body_pose_snapshots,
            runtime.outer_update.body_pose_snapshot_generation,
            runtime.outer_update.explicit_update_count,
            VehicleBodyIdentitySelection{true, 1u});
        require(selected.body_index == 1u,
                "Phase 698 selected the wrong BODY index");
        require(selected.snapshot_generation == 0u,
                "Phase 698 changed snapshot generation");
        require(selected.origin == runtime.outer_update.body_pose_snapshots[1].origin,
                "Phase 698 changed selected BODY origin");
        require(selected.basis == runtime.outer_update.body_pose_snapshots[1].basis,
                "Phase 698 changed selected BODY basis");

        bool generation_rejected = false;
        try {
            (void)select_proven_vehicle_body_pose(
                runtime.outer_update.body_pose_snapshots,
                1u,
                runtime.outer_update.explicit_update_count,
                VehicleBodyIdentitySelection{true, 1u});
        } catch (const std::logic_error&) {
            generation_rejected = true;
        }
        require(generation_rejected,
                "Phase 698 accepted stale/mismatched BODY pose generation");

        bool range_rejected = false;
        try {
            (void)select_proven_vehicle_body_pose(
                runtime.outer_update.body_pose_snapshots,
                0u,
                0u,
                VehicleBodyIdentitySelection{true, 2u});
        } catch (const std::out_of_range&) {
            range_rejected = true;
        }
        require(range_rejected,
                "Phase 698 accepted a BODY index outside the snapshot domain");

        auto mismatched = runtime.outer_update.body_pose_snapshots;
        mismatched[1].body_index = 0u;
        bool identity_rejected = false;
        try {
            (void)select_proven_vehicle_body_pose(
                mismatched,
                0u,
                0u,
                VehicleBodyIdentitySelection{true, 1u});
        } catch (const std::logic_error&) {
            identity_rejected = true;
        }
        require(identity_rejected,
                "Phase 698 accepted mismatched snapshot/BODY identity");

        auto non_finite = runtime.outer_update.body_pose_snapshots;
        non_finite[1].origin[1] = std::numeric_limits<double>::infinity();
        bool non_finite_rejected = false;
        try {
            (void)select_proven_vehicle_body_pose(
                non_finite,
                0u,
                0u,
                VehicleBodyIdentitySelection{true, 1u});
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        require(non_finite_rejected,
                "Phase 698 accepted a non-finite selected BODY pose");

        std::cout
            << "{\"format\":\"" << kNativeVehicleBodyPoseSelectionFormat << "\","
            << "\"ready\":true,"
            << "\"persistent_pose_snapshot_transport_reused\":true,"
            << "\"selection_requires_identity_proof\":true,"
            << "\"selected_body_index\":" << selected.body_index << ","
            << "\"snapshot_generation\":" << selected.snapshot_generation << ","
            << "\"current_process1_frontier_admitted\":false,"
            << "\"vehicle_world_transform_proven\":false,"
            << "\"basis_transpose_or_axis_remap\":false,"
            << "\"renderer_transport_enabled\":false,"
            << "\"camera_follow_enabled\":false,"
            << "\"fixed_step_auto_schedule\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
