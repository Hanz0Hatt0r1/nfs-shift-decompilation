#include "runtime_state.hpp"
#include "shift_persistent_bmw_vehicle_world_transform.hpp"
#include "shift_retail_global_vehicle_body_owner_identity.hpp"
#include "fun_00770e80_outer_update_fixture.hpp"

#include <cstring>
#include <iostream>
#include <limits>
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

void require_same_committed_state(
    const PersistentBmwVehicleWorldTransformState& state,
    const PersistentBmwVehicleWorldTransformSnapshot& expected,
    const char* message) {
    require(
        state.ready &&
            state.body_index == expected.body_index &&
            state.source_runtime_body_count == expected.source_runtime_body_count &&
            state.source_pose_snapshot_generation ==
                expected.source_pose_snapshot_generation &&
            state.source_explicit_update_count ==
                expected.source_explicit_update_count &&
            state.commit_generation == expected.commit_generation &&
            state.source_origin == expected.source_origin &&
            state.source_basis == expected.source_basis &&
            state.vehicle_world_matrix == expected.vehicle_world_matrix,
        message);
}

}  // namespace

int main() {
    try {
        NativeRuntimeState runtime{};
        PersistentBmwVehicleWorldTransformState state{};

        const auto retail_identity = retail_global_vehicle_body_owner_identity();
        require(retail_identity.handoff.vehicle_body_selection_ready &&
                    retail_identity.handoff.selected_body_index == 0u,
                "Phase 706 did not receive positive retail BODY0 identity");

        bool runtime_admission_rejected = false;
        try {
            (void)commit_retail_bmw_vehicle_world_transform(
                state,
                runtime,
                vhf_bind_fixture(),
                body0_bind_fixture());
        } catch (const std::runtime_error& exc) {
            runtime_admission_rejected =
                std::string(exc.what()).find(
                    "vehicle BODY pose runtime handoff requires") !=
                std::string::npos;
        }
        require(runtime_admission_rejected,
                "Phase 706 retail wrapper bypassed Phase 700 runtime admission");
        require(!state.ready && state.commit_generation == 0u,
                "Phase 706 mutated transform state on failed runtime admission");

        runtime.physics.workspace.configure(2u, 1u, 1u);
        runtime.physics.participant_ready = true;
        runtime.physics.participant_identity_join_proven = true;
        const auto source = make_frame();
        const auto relations = make_relations();
        const auto projection = make_projection(source, relations);
        const auto initial_body_bytes = make_raw_bodies(projection.bodies);
        runtime.initialize_explicit_outer_update_body_state(initial_body_bytes);

        bool missing_bind_rejected_before_commit = false;
        try {
            auto missing_bind = body0_bind_fixture();
            missing_bind.ready = false;
            (void)commit_retail_bmw_vehicle_world_transform(
                state,
                runtime,
                vhf_bind_fixture(),
                missing_bind);
        } catch (const std::invalid_argument& exc) {
            missing_bind_rejected_before_commit =
                std::string(exc.what()).find("proven-static") != std::string::npos;
        }
        require(missing_bind_rejected_before_commit,
                "Phase 706 did not stop at unresolved retail BODY0 bind proof");
        require(!state.ready && state.commit_generation == 0u,
                "Phase 706 mutated transform state on missing BODY0 bind proof");

        const auto committed = commit_retail_bmw_vehicle_world_transform(
            state,
            runtime,
            vhf_bind_fixture(),
            body0_bind_fixture());
        require(state.ready && committed.commit_generation == 1u,
                "Phase 706 first transform commit did not become ready");
        require(committed.body_index == 0u,
                "Phase 706 committed non-chassis BODY transform");
        require(committed.source_runtime_body_count == 2u,
                "Phase 706 source BODY cardinality mismatch");
        require(committed.source_pose_snapshot_generation ==
                    runtime.outer_update.body_pose_snapshot_generation &&
                    committed.source_explicit_update_count ==
                        runtime.outer_update.explicit_update_count,
                "Phase 706 source generation telemetry mismatch");

        const auto current = read_current_bmw_vehicle_world_transform(state, runtime);
        require(current.vehicle_world_matrix == committed.vehicle_world_matrix &&
                    current.commit_generation == 1u,
                "Phase 706 current transform read mismatch");

        ++runtime.outer_update.body_pose_snapshot_generation;
        bool stale_generation_rejected = false;
        try {
            (void)read_current_bmw_vehicle_world_transform(state, runtime);
        } catch (const std::logic_error& exc) {
            stale_generation_rejected =
                std::string(exc.what()).find("stale") != std::string::npos;
        }
        require(stale_generation_rejected,
                "Phase 706 accepted stale BODY pose generation");
        --runtime.outer_update.body_pose_snapshot_generation;

        ++runtime.outer_update.explicit_update_count;
        bool stale_update_count_rejected = false;
        try {
            (void)read_current_bmw_vehicle_world_transform(state, runtime);
        } catch (const std::logic_error& exc) {
            stale_update_count_rejected =
                std::string(exc.what()).find("stale") != std::string::npos;
        }
        require(stale_update_count_rejected,
                "Phase 706 accepted stale explicit-update count");
        --runtime.outer_update.explicit_update_count;

        bool failed_recommit_rejected = false;
        try {
            auto missing_bind = body0_bind_fixture();
            missing_bind.ready = false;
            (void)commit_retail_bmw_vehicle_world_transform(
                state,
                runtime,
                vhf_bind_fixture(),
                missing_bind);
        } catch (const std::invalid_argument& exc) {
            failed_recommit_rejected =
                std::string(exc.what()).find("proven-static") != std::string::npos;
        }
        require(failed_recommit_rejected,
                "Phase 706 bypassed Phase 704 bind proof on recommit");
        require_same_committed_state(
            state,
            committed,
            "Phase 706 failed recommit partially mutated persistent transform state");

        const auto recommitted = commit_retail_bmw_vehicle_world_transform(
            state,
            runtime,
            vhf_bind_fixture(),
            body0_bind_fixture());
        require(recommitted.commit_generation == 2u,
                "Phase 706 successful recommit did not advance transform generation");
        require(recommitted.vehicle_world_matrix == committed.vehicle_world_matrix,
                "Phase 706 recommit drifted without a new BODY pose");

        auto reinitialized_bytes = initial_body_bytes;
        const double changed_origin_x = 123.0;
        std::memcpy(
            reinitialized_bytes.data() + body_record_offset::kOrigin[0],
            &changed_origin_x,
            sizeof(changed_origin_x));
        runtime.initialize_explicit_outer_update_body_state(reinitialized_bytes);
        require(runtime.outer_update.explicit_update_count == 0u &&
                    runtime.outer_update.body_pose_snapshot_generation == 0u,
                "Phase 706 reinitialize fixture did not reuse zero generations");
        bool changed_pose_rejected = false;
        try {
            (void)read_current_bmw_vehicle_world_transform(state, runtime);
        } catch (const std::logic_error& exc) {
            changed_pose_rejected =
                std::string(exc.what()).find("source BODY pose changed") !=
                std::string::npos;
        }
        require(changed_pose_rejected,
                "Phase 706 accepted reinitialized BODY pose with reused generation");

        state.commit_generation = std::numeric_limits<std::uint64_t>::max();
        bool overflow_rejected = false;
        try {
            (void)commit_retail_bmw_vehicle_world_transform(
                state,
                runtime,
                vhf_bind_fixture(),
                body0_bind_fixture());
        } catch (const std::overflow_error&) {
            overflow_rejected = true;
        }
        require(overflow_rejected,
                "Phase 706 accepted transform commit-generation overflow");

        std::cout
            << "{\"format\":\""
            << kPersistentBmwVehicleWorldTransformFormat << "\","
            << "\"phase\":706,"
            << "\"transactional_commit\":true,"
            << "\"source_pose_provenance_retained\":true,"
            << "\"stale_snapshot_generation_rejected\":true,"
            << "\"stale_explicit_update_count_rejected\":true,"
            << "\"reinitialize_with_reused_generation_rejected\":true,"
            << "\"phase705_handoff_reused\":true,"
            << "\"current_retail_identity_ready\":true,"
            << "\"retail_identity_injected_by_caller\":false,"
            << "\"current_retail_body0_bind_ready\":false,"
            << "\"automatic_fixed_step_commit\":false,"
            << "\"renderer_mutation_enabled\":false,"
            << "\"camera_follow_enabled\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << "persistent_bmw_vehicle_world_transform_check: "
                  << exc.what() << '\n';
        return 1;
    }
}
