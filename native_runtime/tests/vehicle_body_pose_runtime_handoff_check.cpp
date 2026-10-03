#include "runtime_state.hpp"
#include "shift_vehicle_body_pose_runtime_handoff.hpp"
#include "fun_00770e80_outer_update_fixture.hpp"

#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using namespace shift::runtime;
using namespace shift::runtime::physics;
using namespace shift::runtime::test_fixture;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

bool snapshots_equal(
    const std::vector<PersistentBodyPoseSnapshot>& lhs,
    const std::vector<PersistentBodyPoseSnapshot>& rhs) {
    if (lhs.size() != rhs.size()) {
        return false;
    }
    for (std::size_t index = 0u; index < lhs.size(); ++index) {
        if (lhs[index].body_index != rhs[index].body_index ||
            lhs[index].origin != rhs[index].origin ||
            lhs[index].basis != rhs[index].basis) {
            return false;
        }
    }
    return true;
}

}  // namespace

int main() {
    try {
        NativeRuntimeState runtime{};
        runtime.physics.workspace.configure(2u, 1u, 1u);
        runtime.physics.participant_ready = true;
        runtime.physics.participant_identity_join_proven = true;

        bool uninitialized_rejected = false;
        try {
            (void)build_vehicle_body_pose_runtime_handoff(
                runtime,
                VehicleBodyIdentitySelection{true, 1u});
        } catch (const std::runtime_error& exc) {
            uninitialized_rejected =
                std::string(exc.what()).find("persistent outer state") != std::string::npos;
        }
        require(uninitialized_rejected,
                "Phase 700 accepted runtime handoff before persistent outer initialization");

        const auto source = make_frame();
        const auto relations = make_relations();
        const auto projection = make_projection(source, relations);
        const auto initial_body_bytes = make_raw_bodies(projection.bodies);
        runtime.initialize_explicit_outer_update_body_state(initial_body_bytes);

        const auto committed_bytes = runtime.outer_update.body_bytes;
        const auto committed_snapshots = runtime.outer_update.body_pose_snapshots;
        const auto committed_generation = runtime.outer_update.body_pose_snapshot_generation;

        runtime.physics.participant_ready = false;
        bool participant_rejected = false;
        try {
            (void)build_vehicle_body_pose_runtime_handoff(
                runtime,
                VehicleBodyIdentitySelection{true, 1u});
        } catch (const std::runtime_error& exc) {
            participant_rejected =
                std::string(exc.what()).find("participant identity") != std::string::npos;
        }
        require(participant_rejected,
                "Phase 700 accepted runtime handoff without participant admission");
        runtime.physics.participant_ready = true;

        bool unproven_rejected = false;
        try {
            (void)build_vehicle_body_pose_runtime_handoff(
                runtime,
                VehicleBodyIdentitySelection{false, 1u});
        } catch (const std::invalid_argument&) {
            unproven_rejected = true;
        }
        require(unproven_rejected,
                "Phase 700 bypassed Phase 698 BODY identity proof gate");

        const auto handoff = build_vehicle_body_pose_runtime_handoff(
            runtime,
            VehicleBodyIdentitySelection{true, 1u});
        require(handoff.runtime_body_count == 2u,
                "Phase 700 runtime BODY count mismatch");
        require(handoff.explicit_update_count == 0u,
                "Phase 700 changed explicit update count");
        require(handoff.pose.body_index == 1u,
                "Phase 700 selected the wrong BODY pose");
        require(handoff.pose.origin == committed_snapshots[1].origin,
                "Phase 700 changed selected BODY origin");
        require(handoff.pose.basis == committed_snapshots[1].basis,
                "Phase 700 changed selected BODY basis");
        require(runtime.outer_update.body_bytes == committed_bytes &&
                snapshots_equal(runtime.outer_update.body_pose_snapshots, committed_snapshots) &&
                runtime.outer_update.body_pose_snapshot_generation == committed_generation,
                "Phase 700 read-only handoff mutated persistent runtime state");

        ++runtime.outer_update.body_pose_snapshot_generation;
        bool generation_rejected = false;
        try {
            (void)build_vehicle_body_pose_runtime_handoff(
                runtime,
                VehicleBodyIdentitySelection{true, 1u});
        } catch (const std::logic_error&) {
            generation_rejected = true;
        }
        require(generation_rejected,
                "Phase 700 accepted unsynchronized persistent pose generation");
        runtime.outer_update.body_pose_snapshot_generation = committed_generation;

        runtime.physics.workspace.configure(3u, 1u, 1u);
        bool cardinality_rejected = false;
        try {
            (void)build_vehicle_body_pose_runtime_handoff(
                runtime,
                VehicleBodyIdentitySelection{true, 1u});
        } catch (const std::logic_error&) {
            cardinality_rejected = true;
        }
        require(cardinality_rejected,
                "Phase 700 accepted workspace/persistent BODY cardinality mismatch");

        std::cout
            << "{\"format\":\"" << kNativeVehicleBodyPoseRuntimeHandoffFormat << "\","
            << "\"phase\":700,"
            << "\"ready\":true,"
            << "\"phase698_selector_reused\":true,"
            << "\"phase699_provider_frontier_preserved\":true,"
            << "\"native_runtime_state_admission_required\":true,"
            << "\"runtime_state_mutated\":false,"
            << "\"selected_body_index\":" << handoff.pose.body_index << ","
            << "\"current_process1_chassis_body_selected\":false,"
            << "\"vehicle_world_transform_proven\":false,"
            << "\"renderer_transport_enabled\":false,"
            << "\"camera_follow_enabled\":false,"
            << "\"fixed_step_auto_schedule\":false,"
            << "\"deep_outer_update_executable_schedule_enabled\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
