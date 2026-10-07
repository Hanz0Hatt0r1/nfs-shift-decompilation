#pragma once

#include "shift_fun_007682c0_projection_state.hpp"
#include "shift_fun_00770e80_motion_read_machine_input_provider_chain.hpp"

#include <cstddef>
#include <cstdint>
#include <functional>
#include <vector>

namespace shift::runtime {

struct NativeRuntimeState;
struct RetailOuterSchedulerContract;

inline constexpr const char* kNativeVehicleProviderSessionFormat =
    "SHIFT.NativeVehicleProviderSession/1";

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
using NativeVehicleContactOuterInputProvider =
    std::function<physics::ContactOuterKernelInput(std::size_t pass_index)>;
using NativeVehicleMotionReadInputProvider =
    std::function<physics::Fun007682c0ExternalMachineInput(std::size_t pass_index)>;
using NativeVehicleScalarProviderFactory =
    std::function<physics::Fun007afdd0ScalarProvider(std::size_t pass_index)>;
using NativeVehicleHalfStepRefreshProvider =
    std::function<NativeVehicleHalfStepRefreshInput(
        std::size_t pass_index,
        double half_timestep,
        const std::vector<std::uint8_t>& current_body_bytes)>;

struct NativeVehicleExternalProviderBundle {
    NativeVehiclePassCallback contact_factor{};
    NativeVehiclePassCallback wheel_update{};
    NativeVehiclePassCallback contact_response{};
    NativeVehicleContactOuterInputProvider contact_outer_input{};
    // Remaining exact external PC fields consumed by FUN_00769ef0/FUN_007682c0.
    // HDVehicle+0x4068 is derived from current BODY0 once before both passes by
    // native FUN_007594e0 machine-angle production. HDVehicle+0x4084/+0x408c
    // are session-owned persistent derived state refreshed after both passes.
    // Selected BMW HDVehicle+0x4054 is setup-fixed and session-owned too.
    NativeVehicleMotionReadInputProvider motion_read_input{};
    NativeVehicleScalarProviderFactory scalar_provider_factory{};
    NativeVehicleHalfStepRefreshProvider half_step_refresh{};
    physics::Fun007b8810PostHalfStepCallback post_half_step{};
};

struct NativeVehicleProviderSessionTelemetry {
    std::size_t contact_factor_call_count = 0u;
    std::size_t wheel_update_call_count = 0u;
    std::size_t contact_response_call_count = 0u;
    std::size_t contact_outer_input_call_count = 0u;
    std::size_t motion_read_input_call_count = 0u;
    std::size_t motion_read_native_effect_call_count = 0u;
    std::size_t motion_read_delta_application_call_count = 0u;
    std::size_t scalar_provider_factory_call_count = 0u;
    std::size_t half_step_refresh_call_count = 0u;
    std::size_t post_half_step_call_count = 0u;
};

struct NativeVehicleProviderSessionResult {
    physics::Fun00770e80MotionReadMachineInputProviderChainResult joined{};
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
    float response_field_4054() const { return response_field_4054_; }
    const NativeVehicleProviderSessionTelemetry& last_telemetry() const {
        return last_telemetry_;
    }
    const physics::Fun007682c0DerivedProjectionState&
    motion_read_projection_state() const {
        return motion_read_projection_state_;
    }

private:
    NativeVehicleExternalProviderBundle providers_{};
    float response_field_4054_ = 0.0f;
    physics::Fun007682c0DerivedProjectionState motion_read_projection_state_{};
    std::uint64_t step_count_ = 0u;
    NativeVehicleProviderSessionTelemetry last_telemetry_{};
};

}  // namespace shift::runtime
