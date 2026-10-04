#include "runtime_state.hpp"
#include "shift_bmw_vehicle_world_matrix_runtime_handoff.hpp"
#include "fun_00770e80_outer_update_fixture.hpp"

#include <cmath>
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

void require_close(float actual, float expected, const char* label) {
    if (std::fabs(actual - expected) > 1.0e-5f) {
        throw std::runtime_error(
            std::string(label) + " mismatch: " +
            std::to_string(actual) + " vs " + std::to_string(expected));
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

ProvenBmwVhfBindFrame vhf_bind_fixture() {
    return ProvenBmwVhfBindFrame{
        true,
        {
            0.0f, 2.0f, 0.0f, 0.0f,
            -1.0f, 0.0f, 0.0f, 0.0f,
            0.0f, 0.0f, 0.5f, 0.0f,
            5.0f, 6.0f, 7.0f, 1.0f,
        },
    };
}

ProvenBmwBody0BindFrame body0_bind_fixture() {
    return ProvenBmwBody0BindFrame{
        true,
        true,
        0u,
        false,
        {
            1.0f, 0.0f, 0.0f, 0.0f,
            0.0f, 2.0f, 0.0f, 0.0f,
            0.0f, 0.0f, 1.0f, 0.0f,
            1.0f, 2.0f, 3.0f, 1.0f,
        },
    };
}

}  // namespace

int main() {
    try {
        NativeRuntimeState runtime{};

        // Phase 703 must reject the currently blocked retail identity before
        // Phase 700 attempts to inspect uninitialized runtime pose state.
        bool current_identity_rejected_first = false;
        try {
            auto missing_bind = body0_bind_fixture();
            missing_bind.ready = false;
            (void)build_bmw_vehicle_world_matrix_runtime_handoff(
                runtime,
                GlobalVehicleBodyOwnerIdentityHandoff{},
                vhf_bind_fixture(),
                missing_bind);
        } catch (const std::invalid_argument& exc) {
            current_identity_rejected_first =
                std::string(exc.what()).find("not retail-ready") != std::string::npos;
        }
        require(
            current_identity_rejected_first,
            "Phase 705 did not preserve Phase 703 identity-first fail-closed ordering");

        // With identity admitted, Phase 700 remains responsible for runtime
        // initialization/admission rather than Phase 705 bypassing it.
        bool uninitialized_runtime_rejected = false;
        try {
            (void)build_bmw_vehicle_world_matrix_runtime_handoff(
                runtime,
                synthetic_positive_identity(),
                vhf_bind_fixture(),
                body0_bind_fixture());
        } catch (const std::runtime_error& exc) {
            uninitialized_runtime_rejected =
                std::string(exc.what()).find("persistent outer state") != std::string::npos;
        }
        require(
            uninitialized_runtime_rejected,
            "Phase 705 bypassed Phase 700 persistent-state admission");

        runtime.physics.workspace.configure(2u, 1u, 1u);
        runtime.physics.participant_ready = true;
        runtime.physics.participant_identity_join_proven = true;
        const auto source = make_frame();
        const auto relations = make_relations();
        const auto projection = make_projection(source, relations);
        runtime.initialize_explicit_outer_update_body_state(
            make_raw_bodies(projection.bodies));

        const auto committed_bytes = runtime.outer_update.body_bytes;
        const auto committed_snapshots = runtime.outer_update.body_pose_snapshots;
        const auto committed_generation =
            runtime.outer_update.body_pose_snapshot_generation;
        const auto committed_updates = runtime.outer_update.explicit_update_count;

        const auto result = build_bmw_vehicle_world_matrix_runtime_handoff(
            runtime,
            synthetic_positive_identity(),
            vhf_bind_fixture(),
            body0_bind_fixture());

        require(result.pose.body_index == 0u,
                "Phase 705 did not transport selected BODY0 pose");
        require(result.pose.origin == committed_snapshots[0].origin &&
                    result.pose.basis == committed_snapshots[0].basis,
                "Phase 705 changed selected BODY0 pose");
        require(result.runtime_body_count == 2u,
                "Phase 705 changed runtime BODY cardinality");
        require(result.explicit_update_count == committed_updates,
                "Phase 705 changed explicit update count");

        // The fixture runtime pose comes from the existing Phase 700 fixture,
        // so assert the output against a direct Phase 704 composition of the
        // exact selected pose rather than assuming a synthetic runtime pose.
        const auto direct = compose_bmw_body0_pose_to_vehicle_world_matrix(
            result.pose,
            vhf_bind_fixture(),
            body0_bind_fixture());
        require(result.body0_runtime_row == direct.body0_runtime_row &&
                    result.vehicle_world_matrix == direct.vehicle_world_matrix,
                "Phase 705 drifted from the Phase 704 composition result");

        require(runtime.outer_update.body_bytes == committed_bytes &&
                    snapshots_equal(
                        runtime.outer_update.body_pose_snapshots,
                        committed_snapshots) &&
                    runtime.outer_update.body_pose_snapshot_generation ==
                        committed_generation &&
                    runtime.outer_update.explicit_update_count == committed_updates,
                "Phase 705 mutated persistent runtime state");

        bool missing_bind_rejected = false;
        try {
            auto missing_bind = body0_bind_fixture();
            missing_bind.ready = false;
            (void)build_bmw_vehicle_world_matrix_runtime_handoff(
                runtime,
                synthetic_positive_identity(),
                vhf_bind_fixture(),
                missing_bind);
        } catch (const std::invalid_argument& exc) {
            missing_bind_rejected =
                std::string(exc.what()).find("proven-static") != std::string::npos;
        }
        require(missing_bind_rejected,
                "Phase 705 bypassed Phase 704 BODY0 bind proof gate");
        require(runtime.outer_update.body_bytes == committed_bytes &&
                    snapshots_equal(
                        runtime.outer_update.body_pose_snapshots,
                        committed_snapshots) &&
                    runtime.outer_update.body_pose_snapshot_generation ==
                        committed_generation,
                "Phase 705 failure path mutated persistent state");

        // Expose a small deterministic matrix fingerprint without asserting a
        // particular fixture pose value beyond direct Phase 704 parity.
        require_close(
            result.vehicle_world_matrix[15],
            1.0f,
            "Phase 705 homogeneous component");

        std::cout
            << "{\"format\":\""
            << kNativeBmwVehicleWorldMatrixRuntimeHandoffFormat << "\","
            << "\"phase\":705,"
            << "\"phase703_identity_admission_reused\":true,"
            << "\"phase700_runtime_pose_handoff_reused\":true,"
            << "\"phase704_composition_reused\":true,"
            << "\"selected_body_index\":0,"
            << "\"current_retail_identity_ready\":false,"
            << "\"current_retail_body0_bind_ready\":false,"
            << "\"current_retail_world_matrix_ready\":false,"
            << "\"runtime_state_mutated\":false,"
            << "\"phase646_matrix_output\":true,"
            << "\"live_vulkan_buffer_mutation_enabled\":false,"
            << "\"fixed_step_auto_schedule\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << "bmw_vehicle_world_matrix_runtime_handoff_check: "
                  << exc.what() << '\n';
        return 1;
    }
}
