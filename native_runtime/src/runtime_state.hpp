#pragma once

#include "runtime_body_feedback_scheduler.hpp"
#include "runtime_explicit_outer_update_state.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace shift::runtime {

inline float f32_from_bits(uint32_t bits) {
    float value = 0.0f;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

struct VehicleControlIntent {
    bool throttle = false;
    bool brake = false;
    bool steer_left = false;
    bool steer_right = false;

    float steer_axis() const {
        return static_cast<float>(steer_right) - static_cast<float>(steer_left);
    }
};

struct CameraState {
    // FUN_0080e040 word0 is an opaque 32-bit runtime camera reference.
    // The native shell never dereferences or fabricates retail pointer identity.
    uint32_t camera_source_token = 0;

    // Projection defaults are recovered from CCameraView's initializer:
    // FOV=0.7853982, AspectRatio=1.3333334, NearZ=0.1, FarZ=750.0.
    uint32_t fov_bits = 0x3F490FDBu;
    uint32_t aspect_ratio_bits = 0x3FAAAAABu;
    uint32_t near_z_bits = 0x3DCCCCCDu;
    uint32_t far_z_bits = 0x443B8000u;

    // Manager-level snapshot fields are kept opaque/integer-shaped.
    int32_t manager_mode = 0;
    int32_t buffer_sub_index = -1;
    int32_t camera_id = -1;
    int32_t active_group = -1;
    int32_t group_restore_value = -1;
    uint8_t active_buffer_sub_flag = 0;

    float fov() const { return f32_from_bits(fov_bits); }
    float aspect_ratio() const { return f32_from_bits(aspect_ratio_bits); }
    float near_z() const { return f32_from_bits(near_z_bits); }
    float far_z() const { return f32_from_bits(far_z_bits); }
};

struct CameraManagerSnapshot {
    // Exact six-word shape written by FUN_0080e040.
    uint32_t camera_source_token = 0;
    int32_t manager_mode = 0;
    int32_t buffer_sub_index = -1;
    int32_t camera_id = -1;
    int32_t active_group = -1;
    int32_t group_restore_value = -1;
};

struct CameraBufferRuntime {
    static constexpr uint32_t buffer_count = 2;
    CameraState buffers[buffer_count]{};
    uint32_t active_index = 0;
    bool update_in_progress = false;

    // Native-only observability counters. These do not claim retail timing.
    uint64_t snapshot_count = 0;
    uint64_t native_update_count = 0;
    CameraManagerSnapshot last_snapshot{};

    CameraManagerSnapshot snapshot_active() const {
        const CameraState& state = buffers[active_index];
        CameraManagerSnapshot snapshot{};
        snapshot.camera_source_token = state.camera_source_token;
        snapshot.manager_mode = state.manager_mode;
        snapshot.buffer_sub_index = state.buffer_sub_index;
        snapshot.camera_id = state.camera_id;
        snapshot.active_group = state.active_group;
        snapshot.group_restore_value = state.group_restore_value;
        return snapshot;
    }

    bool begin_swap() {
        if (update_in_progress) {
            return false;
        }

        // Native scheduler policy: retain the source-backed six-word snapshot
        // immediately before the source-backed guarded buffer flip/copy.
        // This ordering is a native handoff choice, not a claim about
        // FUN_0080c920 timestamp/controller scheduling.
        last_snapshot = snapshot_active();
        ++snapshot_count;

        const uint32_t next = 1u - active_index;
        buffers[next] = buffers[active_index];
        active_index = next;
        update_in_progress = true;
        ++native_update_count;
        return true;
    }

    void complete_update() {
        update_in_progress = false;
    }

    bool apply_evidence_snapshot(
        uint32_t index,
        bool update_busy,
        int32_t manager_mode,
        int32_t buffer_sub_index,
        int32_t camera_id,
        int32_t active_group,
        int32_t group_restore_value,
        uint8_t active_buffer_sub_flag) {
        if (index >= buffer_count || update_busy) {
            // A recovered busy guard proves only that retail was mid-update.
            // Native continuation/completion semantics are not proven. Seeding
            // this state would make every begin_swap() return false forever,
            // so reject it instead of inventing a completion policy.
            return false;
        }

        CameraState state = buffers[index];
        // FUN_0080e040 word0 remains opaque and is intentionally not
        // transported by SHIFT.NativeCameraStateBridge/1.
        state.camera_source_token = 0;
        state.manager_mode = manager_mode;
        state.buffer_sub_index = buffer_sub_index;
        state.camera_id = camera_id;
        state.active_group = active_group;
        state.group_restore_value = group_restore_value;
        state.active_buffer_sub_flag =
            active_buffer_sub_flag;
        buffers[index] = state;
        active_index = index;
        update_in_progress = false;
        return true;
    }

    const CameraState& active() const {
        return buffers[active_index];
    }
};

struct PhysicsWorkspaceBoundary {
    uint32_t body_count = 0;
    uint32_t joint_hinge_count = 0;
    uint32_t bar_count = 0;
    uint32_t scalar_count = 0;
    size_t matrix_bytes = 0;
    size_t row_pointer_bytes = 0;
    bool ready = false;

    void configure(
        uint32_t bodies,
        uint32_t joint_hinges,
        uint32_t bars) {
        const uint64_t scalar_count64 =
            static_cast<uint64_t>(joint_hinges) * 5u + bars;
        if (bodies == 0 || scalar_count64 == 0 ||
            scalar_count64 > 4096) {
            ready = false;
            return;
        }
        body_count = bodies;
        joint_hinge_count = joint_hinges;
        bar_count = bars;
        scalar_count = static_cast<uint32_t>(scalar_count64);
        matrix_bytes = static_cast<size_t>(scalar_count) *
            static_cast<size_t>(scalar_count) * sizeof(double);
        row_pointer_bytes = static_cast<size_t>(scalar_count) * sizeof(uint32_t);
        ready = true;
    }
};

struct PhysicsTickBoundary {
    static constexpr double fixed_dt = 1.0 / 60.0;

    uint64_t fixed_step = 0;
    VehicleControlIntent last_input{};
    uint64_t throttle_steps = 0;
    uint64_t brake_steps = 0;
    uint64_t steer_left_steps = 0;
    uint64_t steer_right_steps = 0;
    uint64_t neutral_input_steps = 0;

    // Structural participant ABI may be admitted independently from an
    // observed retail participant instance.
    bool participant_contract_ready = false;
    bool participant_registry_ready = false;
    bool selector_context_separate = false;
    uint32_t registry_slot_stride = 0;
    uint32_t participant_descriptor_type = 0;

    // These identity domains remain capture-gated and deliberately distinct.
    bool participant_identity_join_proven = false;
    bool participant_ready = false;
    int32_t participant_registry_index = -1;
    int32_t selector_ordinal = -1;
    int32_t participant_process_state = -1;

    // Legacy compatibility aliases. Static structural admission must never
    // populate these from either identity domain.
    int32_t participant_index = -1;
    int32_t participant_mode = -1;

    uint64_t participant_topology_steps = 0;
    uint64_t participant_ready_steps = 0;
    uint64_t participant_unresolved_steps = 0;
    PhysicsWorkspaceBoundary workspace{};

    void tick(const VehicleControlIntent& input) {
        last_input = input;
        ++fixed_step;
        if (input.throttle) ++throttle_steps;
        if (input.brake) ++brake_steps;
        if (input.steer_left) ++steer_left_steps;
        if (input.steer_right) ++steer_right_steps;
        if (!input.throttle &&
            !input.brake &&
            !input.steer_left &&
            !input.steer_right) {
            ++neutral_input_steps;
        }
        if (participant_contract_ready) {
            ++participant_topology_steps;
            if (participant_ready) {
                ++participant_ready_steps;
            } else {
                ++participant_unresolved_steps;
            }
        }
        // Source-backed provider-absent solver feedback may be scheduled by
        // NativeRuntimeState below. Vehicle transform/orientation integration
        // and provider-present semantics remain outside this boundary.
    }
};

struct NativeRuntimeState {
    CameraBufferRuntime camera{};
    PhysicsTickBoundary physics{};
    BodyFeedbackScheduler body_feedback{};
    ExplicitOuterUpdateRuntimeState outer_update{};

    static constexpr const char* format =
        "SHIFT.NativeRuntimeState/1";

    bool begin_camera_update() {
        return camera.begin_swap();
    }

    void complete_camera_update() {
        camera.complete_update();
    }

    void initialize_explicit_outer_update_body_state(
        const std::vector<std::uint8_t>& initial_body_bytes) {
        outer_update.initialize_body_state(
            initial_body_bytes,
            physics.workspace.body_count,
            physics.workspace.ready);
    }

    physics::Fun00770e80ComposedAnchorChainResult execute_explicit_outer_update(
        double outer_timestep,
        const physics::Fun0076d100AnchorProvider& physics_pass_provider,
        const physics::Fun00765470MachineHalfStepProvider& half_step_provider,
        const physics::Fun007b8810PostHalfStepCallback& post_half_step) {
        return outer_update.execute(
            physics.workspace.body_count,
            physics.workspace.ready,
            physics.participant_ready,
            physics.participant_identity_join_proven,
            outer_timestep,
            physics_pass_provider,
            half_step_provider,
            post_half_step);
    }

    physics::Fun00770e80ScalarProviderAnchorChainResult
    execute_explicit_outer_update_with_fun_007afdd0_scalar_provider(
        double outer_timestep,
        const physics::Fun0076d100AnchorProvider& physics_pass_provider,
        const physics::Fun00765470MachineScalarHalfStepProvider& half_step_provider,
        const physics::Fun007b8810PostHalfStepCallback& post_half_step) {
        return outer_update.execute_with_fun_007afdd0_scalar_provider(
            physics.workspace.body_count,
            physics.workspace.ready,
            physics.participant_ready,
            physics.participant_identity_join_proven,
            outer_timestep,
            physics_pass_provider,
            half_step_provider,
            post_half_step);
    }

    physics::Fun00770e80ContactOuterProviderChainResult
    execute_explicit_outer_update_with_fun_007675f0_contact_outer_provider(
        double outer_timestep,
        const physics::Fun0076d100ContactOuterProvider& physics_pass_provider,
        const physics::Fun00765470MachineScalarHalfStepProvider& half_step_provider,
        const physics::Fun007b8810PostHalfStepCallback& post_half_step) {
        return outer_update.execute_with_fun_007675f0_contact_outer_provider(
            physics.workspace.body_count,
            physics.workspace.ready,
            physics.participant_ready,
            physics.participant_identity_join_proven,
            outer_timestep,
            physics_pass_provider,
            half_step_provider,
            post_half_step);
    }

    physics::Fun00770e80MotionReadEffectProviderChainResult
    execute_explicit_outer_update_with_fun_007682c0_motion_read_effect_provider(
        double outer_timestep,
        const physics::Fun0076d100MotionReadEffectProvider& physics_pass_provider,
        const physics::Fun00765470MachineScalarHalfStepProvider& half_step_provider,
        const physics::Fun007b8810PostHalfStepCallback& post_half_step) {
        return outer_update.execute_with_fun_007682c0_motion_read_effect_provider(
            physics.workspace.body_count,
            physics.workspace.ready,
            physics.participant_ready,
            physics.participant_identity_join_proven,
            outer_timestep,
            physics_pass_provider,
            half_step_provider,
            post_half_step);
    }

    void fixed_step(const VehicleControlIntent& input) {
        body_feedback.initialize_from_environment();
        body_feedback.validate_runtime_boundary(
            physics.workspace.body_count,
            physics.workspace.scalar_count,
            physics.workspace.ready,
            physics.participant_ready,
            physics.participant_identity_join_proven);

        // fixed_step() is a native transaction across the state that this
        // shell mutates directly. BODY feedback computes its result before
        // committing scheduler state, so only the lightweight camera/physics
        // boundaries need explicit rollback if that downstream step rejects.
        const CameraBufferRuntime camera_before = camera;
        const PhysicsTickBoundary physics_before = physics;

        try {
            const bool camera_update_started =
                begin_camera_update();

            physics.tick(input);
            body_feedback.fixed_step();

            if (camera_update_started) {
                complete_camera_update();
            }
        } catch (...) {
            camera = camera_before;
            physics = physics_before;
            throw;
        }
    }
};

}  // namespace shift::runtime
