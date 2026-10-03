#pragma once

#include "runtime_state.hpp"

#include <cstddef>
#include <cstdint>
#include <functional>
#include <vector>

namespace shift::runtime {

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
using NativeVehicleMotionReadEffectProvider =
    std::function<physics::Fun007682c0AccumulatorEffect(std::size_t pass_index)>;
using NativeVehicleMotionReadDeltaConsumer =
    std::function<void(std::size_t pass_index, double accumulator_y_delta)>;
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
    NativeVehicleMotionReadEffectProvider motion_read_effect{};
    NativeVehicleMotionReadDeltaConsumer motion_read_delta_consumer{};
    NativeVehicleScalarProviderFactory scalar_provider_factory{};
    NativeVehicleHalfStepRefreshProvider half_step_refresh{};
    physics::Fun007b8810PostHalfStepCallback post_half_step{};
};

struct NativeVehicleProviderSessionTelemetry {
    std::size_t contact_factor_call_count = 0u;
    std::size_t wheel_update_call_count = 0u;
    std::size_t contact_response_call_count = 0u;
    std::size_t contact_outer_input_call_count = 0u;
    std::size_t motion_read_effect_call_count = 0u;
    std::size_t motion_read_delta_consumer_call_count = 0u;
    std::size_t scalar_provider_factory_call_count = 0u;
    std::size_t half_step_refresh_call_count = 0u;
    std::size_t post_half_step_call_count = 0u;
};

struct NativeVehicleProviderSessionResult {
    physics::Fun00770e80MotionReadEffectProviderChainResult joined{};
    std::uint64_t session_step_count = 0u;
    NativeVehicleProviderSessionTelemetry telemetry{};
};

class NativeVehicleProviderSession {
public:
    explicit NativeVehicleProviderSession(
        NativeVehicleExternalProviderBundle providers);

    NativeVehicleProviderSessionResult execute_explicit_step(
        NativeRuntimeState& runtime,
        double outer_timestep);

    std::uint64_t step_count() const { return step_count_; }
    const NativeVehicleProviderSessionTelemetry& last_telemetry() const {
        return last_telemetry_;
    }

private:
    NativeVehicleExternalProviderBundle providers_{};
    std::uint64_t step_count_ = 0u;
    NativeVehicleProviderSessionTelemetry last_telemetry_{};
};

}  // namespace shift::runtime
