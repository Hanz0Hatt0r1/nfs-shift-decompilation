#include "runtime_state.hpp"
#include "shift_bmw_chassis_body_selection_gate.hpp"
#include "shift_vehicle_body_pose_runtime_handoff.hpp"
#include "fun_00770e80_outer_update_fixture.hpp"

#include <cstddef>
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
        const auto& topology = bmw_m3_e36_retail_wheel_spindle_body_topology();
        require(topology.main_chassis_body_selected,
                "Phase 703 lost Process 1 chassis BODY selection");
        require(topology.main_chassis_body_index == 0u,
                "Phase 703 BMW chassis BODY index mismatch");
        require(!topology.update_child_to_vehicle_solver_base_continuity_proven,
                "Phase 703 current topology invented vehicle-base continuity");
        require(!topology.vehicle_body_selection_ready,
                "Phase 703 current topology invented ready vehicle selection");

        bool current_frontier_rejected = false;
        try {
            (void)build_bmw_main_chassis_body_identity_selection(
                topology,
                ProvenUpdateChildVehicleSolverBaseContinuity{false});
        } catch (const std::invalid_argument& exc) {
            current_frontier_rejected =
                std::string(exc.what()).find(
                    "update-child to vehicle solver-base continuity") !=
                std::string::npos;
        }
        require(current_frontier_rejected,
                "Phase 703 failed open on the current Process 1 continuity frontier");

        auto drifted = topology;
        drifted.vehicle_body_selection_ready = true;
        bool topology_drift_rejected = false;
        try {
            (void)build_bmw_main_chassis_body_identity_selection(
                drifted,
                ProvenUpdateChildVehicleSolverBaseContinuity{true});
        } catch (const std::invalid_argument& exc) {
            topology_drift_rejected =
                std::string(exc.what()).find("proven retail BODY topology") !=
                std::string::npos;
        }
        require(topology_drift_rejected,
                "Phase 703 accepted self-promoted upstream selection state");

        NativeRuntimeState runtime{};
        runtime.physics.workspace.configure(2u, 1u, 1u);
        runtime.physics.participant_ready = true;
        runtime.physics.participant_identity_join_proven = true;

        const auto source = make_frame();
        const auto relations = make_relations();
        const auto projection = make_projection(source, relations);
        runtime.initialize_explicit_outer_update_body_state(
            make_raw_bodies(projection.bodies));

        const auto committed_body_bytes = runtime.outer_update.body_bytes;
        const auto committed_snapshots = runtime.outer_update.body_pose_snapshots;
        const auto committed_generation =
            runtime.outer_update.body_pose_snapshot_generation;

        const auto synthetic_selection =
            build_bmw_main_chassis_body_identity_selection(
                topology,
                ProvenUpdateChildVehicleSolverBaseContinuity{true});
        require(synthetic_selection.selection_proven &&
                    synthetic_selection.body_index == 0u,
                "Phase 703 synthetic positive continuity selected the wrong BODY");

        const auto handoff = build_vehicle_body_pose_runtime_handoff(
            runtime,
            synthetic_selection);
        require(handoff.pose.body_index == 0u,
                "Phase 703 -> Phase 700 selected the wrong BODY pose");
        require(handoff.runtime_body_count == 2u &&
                    handoff.explicit_update_count == 0u,
                "Phase 703 -> Phase 700 changed runtime counters");
        require(handoff.pose.origin == committed_snapshots[0].origin &&
                    handoff.pose.basis == committed_snapshots[0].basis,
                "Phase 703 -> Phase 700 changed BODY 0 pose values");
        require(runtime.outer_update.body_bytes == committed_body_bytes &&
                    snapshots_equal(
                        runtime.outer_update.body_pose_snapshots,
                        committed_snapshots) &&
                    runtime.outer_update.body_pose_snapshot_generation ==
                        committed_generation,
                "Phase 703 read-only selection path mutated runtime state");

        std::cout
            << "{\"format\":\"SHIFT.NativeBMWChassisBodySelectionGateCheck/1\","
            << "\"gate_format\":\""
            << kNativeBmwChassisBodySelectionGateFormat << "\","
            << "\"ready\":true,"
            << "\"main_chassis_body_selected\":true,"
            << "\"main_chassis_body_index\":0,"
            << "\"current_update_child_to_vehicle_solver_base_continuity_proven\":false,"
            << "\"current_vehicle_body_selection_ready\":false,"
            << "\"current_frontier_rejected\":true,"
            << "\"synthetic_positive_continuity_is_retail_proof\":false,"
            << "\"synthetic_positive_transport_exercised\":true,"
            << "\"phase698_selector_reused\":true,"
            << "\"phase700_runtime_handoff_reused\":true,"
            << "\"selected_body_index\":0,"
            << "\"rear_axle_body_index_required_for_chassis_selection\":false,"
            << "\"world_transform_mapping_proven\":false,"
            << "\"renderer_transport_enabled\":false,"
            << "\"fixed_step_auto_schedule\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
