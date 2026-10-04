#include "runtime_state.hpp"
#include "shift_retail_global_vehicle_body_owner_identity.hpp"
#include "fun_00770e80_outer_update_fixture.hpp"

#include <iostream>
#include <stdexcept>
#include <string>

namespace {

using namespace shift::runtime;
using namespace shift::runtime::physics;
using namespace shift::runtime::test_fixture;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

ProvenBmwVhfBindFrame vhf_bind_fixture() {
    return ProvenBmwVhfBindFrame{
        true,
        {
            1.0f, 0.0f, 0.0f, 0.0f,
            0.0f, 1.0f, 0.0f, 0.0f,
            0.0f, 0.0f, 1.0f, 0.0f,
            0.0f, 0.0f, 0.0f, 1.0f,
        },
    };
}

ProvenBmwBody0BindFrame synthetic_body0_bind_fixture() {
    return ProvenBmwBody0BindFrame{
        true,
        true,
        0u,
        false,
        {
            1.0f, 0.0f, 0.0f, 0.0f,
            0.0f, 1.0f, 0.0f, 0.0f,
            0.0f, 0.0f, 1.0f, 0.0f,
            0.0f, 0.0f, 0.0f, 1.0f,
        },
    };
}

}  // namespace

int main() {
    try {
        const auto retail = retail_global_vehicle_body_owner_identity();
        require(retail.global_vehicle_address == 0x00c13700u,
                "Phase 707 retail global vehicle address drifted");
        require(retail.body_owner_pointer_field_offset == 0x339cu,
                "Phase 707 BODY-owner field offset drifted");
        require(!retail.body_array_owner_is_global_vehicle_base,
                "Phase 707 collapsed BODY owner pointer into global vehicle base");
        require(retail.body_array_owner_pointer_loaded_from_global_vehicle_base,
                "Phase 707 lost proven global vehicle +0x339c field edge");
        require(retail.handoff.outer_receiver_to_body_owner_continuity_proven &&
                    retail.handoff.vehicle_body_selection_ready &&
                    retail.handoff.selected_body_index_present &&
                    retail.handoff.selected_body_index == 0u &&
                    retail.handoff.phase698_positive_selection_admissible &&
                    retail.handoff.phase700_runtime_handoff_admissible &&
                    !retail.handoff.phase703_update_child_equality_gate_required &&
                    retail.handoff.phase703_gate_rewrite_ready,
                "Phase 707 native handoff disagrees with Process 1 #1208");

        NativeRuntimeState runtime{};
        runtime.physics.workspace.configure(2u, 1u, 1u);
        runtime.physics.participant_ready = true;
        runtime.physics.participant_identity_join_proven = true;
        const auto source = make_frame();
        const auto relations = make_relations();
        const auto projection = make_projection(source, relations);
        runtime.initialize_explicit_outer_update_body_state(
            make_raw_bodies(projection.bodies));

        const auto pose_handoff = build_global_vehicle_body_pose_runtime_handoff(
            runtime,
            retail.handoff);
        require(pose_handoff.pose.body_index == 0u,
                "Phase 707 retail producer did not select chassis BODY 0");
        require(pose_handoff.pose.origin == runtime.outer_update.body_pose_snapshots[0].origin &&
                    pose_handoff.pose.basis == runtime.outer_update.body_pose_snapshots[0].basis,
                "Phase 707 retail BODY0 handoff changed persistent pose values");

        bool body0_bind_still_blocks = false;
        try {
            (void)build_retail_bmw_vehicle_world_matrix_runtime_handoff(
                runtime,
                vhf_bind_fixture(),
                ProvenBmwBody0BindFrame{});
        } catch (const std::invalid_argument& exc) {
            body0_bind_still_blocks =
                std::string(exc.what()).find("proven-static") != std::string::npos;
        }
        require(body0_bind_still_blocks,
                "Phase 707 bypassed unresolved retail BODY0 bind proof");

        const auto matrix_handoff =
            build_retail_bmw_vehicle_world_matrix_runtime_handoff(
                runtime,
                vhf_bind_fixture(),
                synthetic_body0_bind_fixture());
        require(matrix_handoff.pose.body_index == 0u,
                "Phase 707 retail matrix handoff lost chassis identity");

        PersistentBmwVehicleWorldTransformState state{};
        const auto committed = commit_retail_bmw_vehicle_world_transform(
            state,
            runtime,
            vhf_bind_fixture(),
            synthetic_body0_bind_fixture());
        require(state.ready && committed.body_index == 0u &&
                    committed.commit_generation == 1u,
                "Phase 707 retail identity wrapper did not reach Phase 706 commit");
        require(committed.vehicle_world_matrix == matrix_handoff.vehicle_world_matrix,
                "Phase 707 retail wrappers disagree on world matrix");

        std::cout
            << "{\"format\":\""
            << kRetailGlobalVehicleBodyOwnerIdentityFormat << "\","
            << "\"phase\":707,"
            << "\"process1_contract\":\"SHIFT.GlobalVehicleBodyOwnerIdentity/1\","
            << "\"process1_pr\":1208,"
            << "\"retail_identity_ready\":true,"
            << "\"retail_global_vehicle_address\":12662528,"
            << "\"retail_BODY_owner_pointer_field_offset\":13212,"
            << "\"BODY_array_owner_is_global_vehicle_base\":false,"
            << "\"retail_selected_BODY_index\":0,"
            << "\"manual_identity_argument_removed_from_retail_wrapper\":true,"
            << "\"phase700_runtime_handoff_reused\":true,"
            << "\"phase706_commit_reused\":true,"
            << "\"current_retail_BODY0_bind_ready\":false,"
            << "\"synthetic_BODY0_bind_is_retail_proof\":false,"
            << "\"fixed_step_auto_schedule\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << "retail_global_vehicle_body_owner_identity_check: "
                  << exc.what() << '\n';
        return 1;
    }
}
