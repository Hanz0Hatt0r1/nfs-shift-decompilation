#pragma once

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
    // Structural participant ABI may be admitted independently from an
    // observed retail participant instance.
    bool participant_contract_ready = false;
    bool participant_registry_ready = false;
    bool selector_context_separate = false;
    uint32_t registry_slot_stride = 0;
    uint32_t participant_descriptor_type = 0;

    // These remain capture-gated. Structural admission must not promote them.
    bool participant_ready = false;
    int32_t participant_index = -1;
    int32_t participant_mode = -1;
    PhysicsWorkspaceBoundary workspace{};

    void tick(const VehicleControlIntent& input) {
        last_input = input;
        ++fixed_step;
        // Physics integration intentionally remains outside this shell.
        // The retail participant/provider semantics are not synthesized here.
    }
};

struct NativeRuntimeState {
    CameraBufferRuntime camera{};
    PhysicsTickBoundary physics{};

    static constexpr const char* format =
        "SHIFT.NativeRuntimeState/1";

    bool begin_camera_update() {
        return camera.begin_swap();
    }

    void complete_camera_update() {
        camera.complete_update();
    }

    void fixed_step(const VehicleControlIntent& input) {
        const bool camera_update_started =
            begin_camera_update();

        physics.tick(input);

        if (camera_update_started) {
            complete_camera_update();
        }
    }
};

}  // namespace shift::runtime
