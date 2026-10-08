#pragma once

#include "shift_fun_007560c0_motion_read_gate_setup.hpp"
#include "shift_fun_00765c40_external_pass_result.hpp"
#include "shift_fun_00766510_external_pass_input.hpp"
#include "shift_fun_007675f0_distance_filter_cap_setup.hpp"
#include "shift_fun_007675f0_distance_state_setup.hpp"
#include "shift_fun_007682c0_projection_state.hpp"
#include "shift_fun_00770e80_motion_read_machine_input_provider_chain.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <optional>
#include <type_traits>
#include <utility>
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
    std::function<physics::Fun00765c40ExternalPassResult(
        std::size_t pass_index,
        const physics::Fun00765c40ExternalPassInput& input)>;

class NativeVehicleContactResponseProvider {
public:
    NativeVehicleContactResponseProvider() = default;

    template <typename Fn,
              typename = std::enable_if_t<!std::is_same_v<
                  std::decay_t<Fn>, NativeVehicleContactResponseProvider>>>
    NativeVehicleContactResponseProvider(Fn&& fn) {
        assign(std::forward<Fn>(fn));
    }

    template <typename Fn>
    NativeVehicleContactResponseProvider& operator=(Fn&& fn) {
        assign(std::forward<Fn>(fn));
        return *this;
    }

    explicit operator bool() const { return static_cast<bool>(callback_); }

    void operator()(
        std::size_t pass_index,
        const physics::Fun00766510ExternalPassInput& input) const {
        if (!callback_) {
            throw std::bad_function_call();
        }
        callback_(pass_index, input);
    }

private:
    template <typename Fn>
    void assign(Fn&& fn) {
        using Decayed = std::decay_t<Fn>;
        if constexpr (std::is_invocable_v<
                          Decayed&,
                          std::size_t,
                          const physics::Fun00766510ExternalPassInput&>) {
            callback_ = std::forward<Fn>(fn);
        } else if constexpr (std::is_invocable_v<Decayed&, std::size_t>) {
            callback_ = [legacy = std::forward<Fn>(fn)](
                            std::size_t pass_index,
                            const physics::Fun00766510ExternalPassInput&) mutable {
                legacy(pass_index);
            };
        } else {
            static_assert(
                std::is_invocable_v<Decayed&, std::size_t>,
                "contact response provider must accept pass or pass+typed input");
        }
    }

    std::function<void(
        std::size_t,
        const physics::Fun00766510ExternalPassInput&)> callback_{};
};

using NativeVehicleContactOuterInputProvider =
    std::function<physics::ContactOuterSessionInput(std::size_t pass_index)>;
using NativeVehicleScalarProviderFactory =
    std::function<physics::Fun007afdd0ScalarProvider(std::size_t pass_index)>;
using NativeVehicleHalfStepRefreshProvider =
    std::function<NativeVehicleHalfStepRefreshInput(
        std::size_t pass_index,
        double half_timestep,
        const std::vector<std::uint8_t>& current_body_bytes)>;

struct NativeVehicleExternalProviderBundle {
    NativeVehicleFun00765c40Provider fun_00765c40{};
    NativeVehiclePassCallback wheel_update{};

    // FUN_00766510 remains a residual external boundary. Phase745 no longer
    // lets it hide the selected same-pass query result or the already-native
    // HDVehicle+0x38f0 application point: both arrive through a typed input.
    // The wrapper accepts historical pass-only callbacks for fixture compatibility,
    // but production session dispatch always uses the typed two-argument form.
    NativeVehicleContactResponseProvider contact_response{};

    NativeVehicleContactOuterInputProvider contact_outer_input{};
    physics::Fun007675f0DistanceStateSetup contact_outer_distance_setup{};
    physics::Fun007675f0DistanceFilterCapSetup contact_outer_filter_cap_setup{};

    physics::Fun007560c0MotionReadGateSetup motion_read_setup{};

    NativeVehicleScalarProviderFactory scalar_provider_factory{};
    NativeVehicleHalfStepRefreshProvider half_step_refresh{};
    physics::Fun007b8810PostHalfStepCallback post_half_step{};
};

struct NativeVehicleProviderSessionTelemetry {
    std::size_t fun_00765c40_call_count = 0u;
    std::size_t fun_00765c40_query_input_capture_count = 0u;
    std::size_t fun_00765c40_cache_commit_count = 0u;
    std::size_t wheel_update_call_count = 0u;
    std::size_t contact_response_call_count = 0u;
    std::size_t contact_outer_input_call_count = 0u;
    std::size_t contact_outer_distance_state_commit_count = 0u;
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
    std::array<std::optional<std::uint64_t>, kNativeVehiclePhysicsPassCount>
        fun_00765c40_returned_cache_handles{};
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
    double contact_outer_distance_state() const {
        return contact_outer_distance_state_;
    }
    double contact_outer_distance_filter_cap() const {
        return providers_.contact_outer_filter_cap_setup.distance_filter_cap;
    }
    std::optional<std::uint64_t> fun_00765c40_query_cache_handle() const {
        return fun_00765c40_query_cache_handle_;
    }

private:
    NativeVehicleExternalProviderBundle providers_{};
    physics::Fun007682c0DerivedProjectionState motion_read_projection_state_{};
    double contact_outer_distance_state_ = 0.0;
    std::optional<std::uint64_t> fun_00765c40_query_cache_handle_{};
    std::uint64_t step_count_ = 0u;
    NativeVehicleProviderSessionTelemetry last_telemetry_{};
};

}  // namespace shift::runtime
