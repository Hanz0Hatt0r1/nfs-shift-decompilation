#include "fun_00770e80_outer_update_fixture.hpp"
#include "shift_native_vehicle_provider_session_v2.hpp"

#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

using namespace shift::runtime;
using namespace shift::runtime::physics;
using namespace shift::runtime::test_fixture;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

double read_f64(
    const std::vector<std::uint8_t>& bytes,
    std::size_t offset) {
    if (offset + sizeof(double) > bytes.size()) {
        throw std::runtime_error("Phase 707 f64 read is out of range");
    }
    double value = 0.0;
    std::memcpy(&value, bytes.data() + offset, sizeof(value));
    return value;
}

GlobalVehicleBodyOwnerIdentityHandoff positive_owner() {
    GlobalVehicleBodyOwnerIdentityHandoff handoff{};
    handoff.outer_receiver_to_body_owner_continuity_proven = true;
    handoff.vehicle_body_selection_ready = true;
    handoff.selected_body_index_present = true;
    handoff.selected_body_index = 0u;
    handoff.phase698_positive_selection_admissible = true;
    handoff.phase700_runtime_handoff_admissible = true;
    handoff.phase703_update_child_equality_gate_required = false;
    handoff.phase703_gate_rewrite_ready = true;
    return handoff;
}

NativeVehicleExternalProviderBundleV2 make_bundle(
    std::vector<std::string>& events,
    const PreparedGeneratedBodyConstraintFrame& source,
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& reset_state,
    const PreparedBuiltinSolverFrame& solver_topology,
    const PreparedPostSolveBodyProjection& projection,
    const Fun00763570MachineInput& machine_input) {
    NativeVehicleExternalProviderBundleV2 bundle{};
    bundle.contact_factor = [&events](std::size_t pass) {
        events.push_back("contact-factor:" + std::to_string(pass));
    };
    bundle.wheel_update = [&events](std::size_t pass) {
        events.push_back("wheel-update:" + std::to_string(pass));
    };
    bundle.contact_response = [&events](std::size_t pass) {
        events.push_back("contact-response:" + std::to_string(pass));
    };
    bundle.contact_outer_input = [&events](std::size_t pass) {
        events.push_back("contact-input:" + std::to_string(pass));
        return make_contact_outer_input();
    };
    bundle.motion_read_effect = [&events](std::size_t pass) {
        events.push_back("motion-effect:" + std::to_string(pass));
        if (pass == 0u) {
            return Fun007682c0AccumulatorEffect{true, -0.5};
        }
        return Fun007682c0AccumulatorEffect{false, 0.0};
    };
    bundle.scalar_provider_factory = [&events](std::size_t pass) {
        events.push_back("scalar-factory:" + std::to_string(pass));
        return [&events, pass](
            std::size_t body_index,
            const ConstraintRefreshFrame3f&,
            const BodyFrameIntegrationVector3d&) {
            if (body_index >= 2u) {
                throw std::runtime_error("Phase 707 scalar BODY index mismatch");
            }
            events.push_back(
                "scalar:" + std::to_string(pass) + ":" +
                std::to_string(body_index));
            Fun007afdd0ScalarBoundary scalars{};
            scalars.squared_magnitude_test = 0.0f;
            scalars.sqrt_magnitude = 0.0f;
            scalars.sine = 0.0f;
            scalars.cosine = 1.0f;
            return scalars;
        };
    };
    bundle.half_step_refresh =
        [&events,
         &source,
         &relations,
         &reset_state,
         &solver_topology,
         &projection,
         &machine_input](
            std::size_t pass,
            double half_timestep,
            const std::vector<std::uint8_t>& current_body_bytes) {
            if (half_timestep != 0.25) {
                throw std::runtime_error("Phase 707 half timestep mismatch");
            }
            if (pass == 0u) {
                const double body0_accumulator_y = read_f64(
                    current_body_bytes,
                    kFun007682c0AccumulatorYOffset);
                require_close(
                    body0_accumulator_y,
                    1.5,
                    "Phase 707 half-step did not observe BODY0 +0x50 delta");
                events.push_back("half-saw-native-delta:0");
            }
            events.push_back("half-refresh:" + std::to_string(pass));
            NativeVehicleHalfStepRefreshInput input{};
            input.machine = machine_input;
            input.source = source;
            input.relations = relations;
            input.reset_state = reset_state;
            input.solver_topology = solver_topology;
            input.projection = projection;
            return input;
        };
    bundle.post_half_step = [&events](std::size_t pass) {
        events.push_back("post-half:" + std::to_string(pass));
    };
    return bundle;
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
        const auto machine_input = make_machine_input();
        const auto initial_body_bytes = make_raw_bodies(projection.bodies);

        // Standalone ABI application: exact f64 BODY0 +0x50 add, no BODY1 write.
        auto lane_bytes = initial_body_bytes;
        const std::size_t body1_offset =
            kBodyRecordSize + kFun007682c0AccumulatorYOffset;
        const double body1_before = read_f64(lane_bytes, body1_offset);
        const double updated = apply_fun_007682c0_body_accumulator_y_delta(
            lane_bytes, 0u, -0.5);
        require_close(updated, 1.5,
                      "Phase 707 standalone BODY0 accumulator result mismatch");
        require_close(
            read_f64(lane_bytes, kFun007682c0AccumulatorYOffset),
            1.5,
            "Phase 707 standalone BODY0 bytes mismatch");
        require_close(
            read_f64(lane_bytes, body1_offset),
            body1_before,
            "Phase 707 standalone application changed BODY1");

        bool malformed_rejected = false;
        try {
            std::vector<std::uint8_t> malformed(kBodyRecordSize - 1u, 0u);
            (void)apply_fun_007682c0_body_accumulator_y_delta(
                malformed, 0u, 1.0);
        } catch (const std::invalid_argument&) {
            malformed_rejected = true;
        }
        require(malformed_rejected,
                "Phase 707 accepted malformed BODY buffer");

        std::vector<std::string> blocked_events;
        auto blocked_handoff = positive_owner();
        blocked_handoff.outer_receiver_to_body_owner_continuity_proven = false;
        blocked_handoff.vehicle_body_selection_ready = false;
        blocked_handoff.selected_body_index_present = false;
        blocked_handoff.phase698_positive_selection_admissible = false;
        blocked_handoff.phase700_runtime_handoff_admissible = false;
        blocked_handoff.phase703_gate_rewrite_ready = false;
        bool identity_rejected = false;
        try {
            NativeVehicleProviderSessionV2 blocked(
                make_bundle(
                    blocked_events,
                    source,
                    relations,
                    reset_state,
                    solver_topology,
                    projection,
                    machine_input),
                blocked_handoff);
            (void)blocked;
        } catch (const std::invalid_argument&) {
            identity_rejected = true;
        }
        require(identity_rejected && blocked_events.empty(),
                "Phase 707 blocked BODY identity reached provider side effects");

        NativeRuntimeState runtime{};
        runtime.physics.workspace.configure(2u, 1u, 1u);
        runtime.physics.participant_contract_ready = true;
        runtime.physics.participant_registry_ready = true;
        runtime.physics.selector_context_separate = true;
        runtime.physics.participant_ready = true;
        runtime.physics.participant_identity_join_proven = true;
        runtime.initialize_explicit_outer_update_body_state(initial_body_bytes);

        std::vector<std::string> events;
        NativeVehicleProviderSessionV2 session(
            make_bundle(
                events,
                source,
                relations,
                reset_state,
                solver_topology,
                projection,
                machine_input),
            positive_owner());

        const auto first = session.execute_explicit_step(runtime, outer_timestep);
        require(first.session_step_count == 1u && session.step_count() == 1u,
                "Phase 707 session step count mismatch");
        require(first.joined.selected_body_index == 0u,
                "Phase 707 did not select retail BMW chassis BODY0");
        require(first.joined.motion_read_effect_provider_call_count == 2u &&
                first.joined.native_delta_application_count == 1u &&
                first.joined.motion_read_gate_open_count == 1u,
                "Phase 707 native motion-read consumer telemetry mismatch");
        require(first.telemetry.contact_factor_call_count == 2u &&
                first.telemetry.wheel_update_call_count == 2u &&
                first.telemetry.contact_response_call_count == 2u &&
                first.telemetry.contact_outer_input_call_count == 2u &&
                first.telemetry.motion_read_effect_call_count == 2u &&
                first.telemetry.scalar_provider_factory_call_count == 2u &&
                first.telemetry.half_step_refresh_call_count == 2u &&
                first.telemetry.post_half_step_call_count == 2u &&
                first.telemetry.native_body0_delta_application_count == 1u,
                "Phase 707 eight-provider telemetry mismatch");
        require(runtime.outer_update.explicit_update_count == 1u &&
                runtime.outer_update.body_pose_snapshot_generation == 1u,
                "Phase 707 persistent runtime state did not commit");
        require(runtime.outer_update.last_motion_read_delta_consumer_call_count == 1u,
                "Phase 707 runtime telemetry did not record native delta application");
        require(std::find(events.begin(), events.end(), "half-saw-native-delta:0") != events.end(),
                "Phase 707 did not execute native delta before first half-step");

        const auto committed_bytes = runtime.outer_update.body_bytes;
        const auto committed_generation =
            runtime.outer_update.body_pose_snapshot_generation;
        events.clear();
        runtime.physics.participant_ready = false;
        bool participant_rejected = false;
        try {
            (void)session.execute_explicit_step(runtime, outer_timestep);
        } catch (const std::runtime_error&) {
            participant_rejected = true;
        }
        runtime.physics.participant_ready = true;
        require(participant_rejected && events.empty(),
                "Phase 707 participant gate allowed provider side effects");
        require(session.step_count() == 1u &&
                runtime.outer_update.explicit_update_count == 1u &&
                runtime.outer_update.body_pose_snapshot_generation == committed_generation &&
                runtime.outer_update.body_bytes == committed_bytes,
                "Phase 707 failed step mutated committed session/runtime state");
        require(runtime.physics.fixed_step == 0u,
                "Phase 707 leaked explicit outer update into fixed_step scheduling");

        std::cout
            << "{\"format\":\"" << kNativeVehicleProviderSessionV2Format << "\","
            << "\"phase\":707,"
            << "\"ready\":true,"
            << "\"external_provider_count\":8,"
            << "\"retail_body_owner_identity_positive\":true,"
            << "\"selected_body_index\":0,"
            << "\"fun_007682c0_body0_delta_consumer_native\":true,"
            << "\"body0_delta_before_half_step\":true,"
            << "\"body1_not_selected\":true,"
            << "\"persistent_runtime_commit_transactional\":true,"
            << "\"fixed_step_auto_schedule\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
