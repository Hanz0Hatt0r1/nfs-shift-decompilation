#pragma once

#include "shift_fun_007560c0_motion_read_gate_setup.hpp"
#include "shift_fun_00765c40_external_pass_result.hpp"
#include "shift_fun_007682c0_projection_state.hpp"
#include "shift_fun_00770e80_motion_read_machine_input_provider_chain.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <vector>

namespace shift::runtime {

struct NativeRuntimeState;
struct RetailOuterSchedulerContract;

inline constexpr const char* kNativeVehicleProviderSessionFormat =
    "SHIFT.NativeVehicleProviderSession/1";
inline constexpr std::size_t kNativeVehiclePhysicsPassCount = 2u;

struct NativeVehicleHalfStepRefreshInput {
    physics::Fun00763570MachineInput machine{};
    physics::PreparedGeneratedBodyConstraintFrame source{};
    physics::PreparedConstraintSampleRelationFrame relations{};
    physics::PreparedConstraintRelationResetFrame reset_state{};
    physics::PreparedBuiltinSolverFrame solver_topology{};
    physics::PreparedPostSolveBodyProjection projection{};
    double tolerance = 1e-10;
};

using NativeVehiclePassCallback = std::function<void(std::size_t pass_index)>;
using NativeVehicleFun00765c40Provider =
    std::function<physics::Fun00765c40ExternalPassResult(std::size_t pass_index)>;
using NativeVehicleContactOuterInputProvider =
    std::function<physics::ContactOuterExternalInput(std::size_t pass_index)>;
using NativeVehicleScalarProviderFactory =
    std::function<physics::Fun007afdd0ScalarProvider(std::size_t pass_index)>;
using NativeVehicleHalfStepRefreshProvider =
    std::function<NativeVehicleHalfStepRefreshInput(
        std::size_t pass_index,
        double half_timestep,
        const std::vector<std::uint8_t>& current_body_bytes)>;

struct NativeVehicleExternalProviderBundle {
    // FUN_00765c40 remains one external pass boundary. Do not call this a
    // contact-factor provider: the nested FUN_00758ad0 factor arithmetic is
    // already native. The external pass now has to expose the source-backed
    // FUN_007b0710 query input it consumed (world position, prior cache handle,
    // +0x38e8 miss fallback) together with the four proven wheel+0x738 outputs.
    // The upstream transform producing world_position and the collision-provider
    // implementation remain unresolved and external.
    NativeVehicleFun00765c40Provider fun_00765c40{};
    NativeVehiclePassCallback wheel_update{};
    NativeVehiclePassCallback contact_response{};

    // FUN_007675f0 arithmetic remains native. Its provider now supplies only the
    // still-external non-BODY fields; speed_x/speed_z are read from the current
    // persistent BODY0 +0x78/+0x88 immediately before each recovered pass.
    NativeVehicleContactOuterInputProvider contact_outer_input{};

    // FUN_007560c0 writes HDVehicle+0xe0 during vehicle setup. This is immutable
    // session setup state, not a per-pass provider boundary. Its upstream value
    // remains explicit until the selected settings producer is proven.
    physics::Fun007560c0MotionReadGateSetup motion_read_setup{};

    // No late raw FUN_007682c0 provider remains for the selected native session.
    // DAT_00c128cc now comes from the already-bound native Player Difficulty
    // policy through SHIFT.BMWNativeSessionPlayerDifficulty/1. Gate, steering,
    // four load terms, selected-BMW +0x4054 and +0x4084/+0x408c likewise come
    // from earlier proven owners.
    NativeVehicleScalarProviderFactory scalar_provider_factory{};
    NativeVehicleHalfStepRefreshProvider half_step_refresh{};
    physics::Fun007b8810PostHalfStepCallback post_half_step{};
};

struct NativeVehicleProviderSessionTelemetry {
    std::size_t fun_00765c40_call_count = 0u;
    std::size_t fun_00765c40_query_input_capture_count = 0u;
    std::size_t wheel_update_call_count = 0u;
    std::size_t contact_response_call_count = 0u;
    std::size_t contact_outer_input_call_count = 0u;
    std::size_t motion_read_native_effect_call_count = 0u;
    std::size_t motion_read_delta_application_call_count = 0u;
    std::size_t scalar_provider_factory_call_count = 0u;
    std::size_t half_step_refresh_call_count = 0u;
    std::size_t post_half_step_call_count = 0u;
};

struct NativeVehicleProviderSessionResult {
    physics::Fun00770e80MotionReadMachineInputProviderChainResult joined{};
    std::array<physics::Fun00765c40QueryInputBoundary, kNativeVehiclePhysicsPassCount>
        fun_00765c40_query_inputs{};
    std::array<bool, kNativeVehiclePhysicsPassCount>
        fun_00765c40_query_input_present{};
    std::uint64_t session_step_count = 0u;
    NativeVehicleProviderSessionTelemetry telemetry{};
};

struct NativeVehicleRetailInnerBatchResult {
    std::size_t recovered_substep_count = 0u;
    double inner_substep_seconds = 0.0;
    std::uint64_t session_step_count_before = 0u;
    std::uint64_t session_step_count_after = 0u;
    std::uint64_t explicit_update_count_before = 0u;
    std::uint64_t explicit_update_count_after = 0u;
    bool scheduler_accumulator_committed = false;
};

class NativeVehicleProviderSession {
public:
    explicit NativeVehicleProviderSession(
        NativeVehicleExternalProviderBundle providers);

    NativeVehicleProviderSessionResult execute_explicit_step(
        NativeRuntimeState& runtime,
        double outer_timestep);

    NativeVehicleRetailInnerBatchResult execute_ready_retail_inner_batch(
        NativeRuntimeState& runtime,
        RetailOuterSchedulerContract& scheduler);

    NativeVehicleRetailInnerBatchResult execute_retail_outer_dispatch(
        NativeRuntimeState& runtime,
        RetailOuterSchedulerContract& scheduler);

    std::uint64_t step_count() const { return step_count_; }
    const NativeVehicleProviderSessionTelemetry& last_telemetry() const {
        return last_telemetry_;
    }
    const physics::Fun007682c0DerivedProjectionState&
    motion_read_projection_state() const {
        return motion_read_projection_state_;
    }

private:
    NativeVehicleExternalProviderBundle providers_{};
    physics::Fun007682c0DerivedProjectionState motion_read_projection_state_{};
    std::uint64_t step_count_ = 0u;
    NativeVehicleProviderSessionTelemetry last_telemetry_{};
};

}  // namespace shift::runtime
