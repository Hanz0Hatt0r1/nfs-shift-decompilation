#include "runtime_state.hpp"
#include "shift_global_vehicle_body_owner_selection.hpp"
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
    if (!condition) throw std::runtime_error(message);
}

bool snapshots_equal(const std::vector<PersistentBodyPoseSnapshot>& lhs,
                     const std::vector<PersistentBodyPoseSnapshot>& rhs) {
    if (lhs.size() != rhs.size()) return false;
    for (std::size_t index = 0u; index < lhs.size(); ++index) {
        if (lhs[index].body_index != rhs[index].body_index ||
            lhs[index].origin != rhs[index].origin ||
            lhs[index].basis != rhs[index].basis) return false;
    }
    return true;
}

GlobalVehicleBodyOwnerIdentityHandoff synthetic_positive_identity() {
    GlobalVehicleBodyOwnerIdentityHandoff handoff{};
    handoff.outer_receiver_to_body_owner_continuity_proven = true;
    handoff.vehicle_body_selection_ready = true;
    handoff.selected_body_index_present = true;
    handoff.selected_body_index = 0u;
    handoff.phase698_positive_selection_admissible = true;
    handoff.phase700_runtime_handoff_admissible = true;
    handoff.phase703_gate_rewrite_ready = true;
    return handoff;
}
}  // namespace

int main() {
    try {
        NativeRuntimeState runtime{};
        bool blocked_rejected_before_runtime_read = false;
        try {
            (void)build_global_vehicle_body_pose_runtime_handoff(
                runtime, GlobalVehicleBodyOwnerIdentityHandoff{});
        } catch (const std::invalid_argument& exc) {
            blocked_rejected_before_runtime_read =
                std::string(exc.what()).find("not retail-ready") != std::string::npos;
        }
        require(blocked_rejected_before_runtime_read,
                "Phase 703 did not reject blocked identity before Phase 700 runtime reads");

        runtime.physics.workspace.configure(2u, 1u, 1u);
        runtime.physics.participant_ready = true;
        runtime.physics.participant_identity_join_proven = true;
        const auto source = make_frame();
        const auto relations = make_relations();
        const auto projection = make_projection(source, relations);
        runtime.initialize_explicit_outer_update_body_state(make_raw_bodies(projection.bodies));

        const auto committed_bytes = runtime.outer_update.body_bytes;
        const auto committed_snapshots = runtime.outer_update.body_pose_snapshots;
        const auto committed_generation = runtime.outer_update.body_pose_snapshot_generation;
        const auto committed_updates = runtime.outer_update.explicit_update_count;

        const auto handoff = build_global_vehicle_body_pose_runtime_handoff(
            runtime, synthetic_positive_identity());
        require(handoff.pose.body_index == 0u,
                "Phase 703 positive identity did not select BODY 0");
        require(handoff.pose.origin == committed_snapshots[0].origin &&
                handoff.pose.basis == committed_snapshots[0].basis,
                "Phase 703 changed BODY 0 pose values");
        require(handoff.runtime_body_count == 2u &&
                handoff.explicit_update_count == committed_updates,
                "Phase 703 changed Phase 700 runtime counters");
        require(runtime.outer_update.body_bytes == committed_bytes &&
                snapshots_equal(runtime.outer_update.body_pose_snapshots, committed_snapshots) &&
                runtime.outer_update.body_pose_snapshot_generation == committed_generation &&
                runtime.outer_update.explicit_update_count == committed_updates,
                "Phase 703 runtime handoff mutated persistent state");

        auto contradictory = synthetic_positive_identity();
        contradictory.phase700_runtime_handoff_admissible = false;
        bool contradictory_rejected = false;
        try { (void)build_global_vehicle_body_pose_runtime_handoff(runtime, contradictory); }
        catch (const std::invalid_argument& exc) {
            contradictory_rejected = std::string(exc.what()).find("readiness flags disagree") != std::string::npos;
        }
        require(contradictory_rejected,
                "Phase 703 accepted contradictory Process 1 flags");

        auto obsolete = synthetic_positive_identity();
        obsolete.phase703_update_child_equality_gate_required = true;
        bool obsolete_rejected = false;
        try { (void)build_global_vehicle_body_pose_runtime_handoff(runtime, obsolete); }
        catch (const std::invalid_argument& exc) {
            obsolete_rejected = std::string(exc.what()).find("obsolete update-child equality gate") != std::string::npos;
        }
        require(obsolete_rejected,
                "Phase 703 reaccepted obsolete update-child equality proof");

        std::cout
            << "{\"format\":\"" << kNativeGlobalVehicleBodyOwnerSelectionFormat << "\","
            << "\"phase\":703,"
            << "\"process1_contract\":\"SHIFT.GlobalVehicleBodyOwnerIdentity/1\","
            << "\"current_retail_identity_ready\":false,"
            << "\"current_retail_selection_emitted\":false,"
            << "\"synthetic_positive_identity_is_retail_proof\":false,"
            << "\"synthetic_selected_body_index\":0,"
            << "\"phase698_selector_reused\":true,"
            << "\"phase700_runtime_handoff_reused\":true,"
            << "\"obsolete_update_child_gate_required\":false,"
            << "\"runtime_state_mutated\":false,"
            << "\"phase645_vhf_is_dynamic_pose\":false,"
            << "\"dynamic_body0_to_vhf_composition_proven\":false,"
            << "\"fixed_step_auto_schedule\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
