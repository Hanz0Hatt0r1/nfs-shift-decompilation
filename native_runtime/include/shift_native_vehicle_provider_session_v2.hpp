#pragma once

#include "shift_native_body0_delta_runtime.hpp"
#include "shift_native_vehicle_provider_session.hpp"

#include <cstddef>
#include <cstdint>
#include <functional>
#include <vector>

namespace shift::runtime {

inline constexpr const char* kNativeVehicleProviderSessionV2Format =
    "SHIFT.NativeVehicleProviderSession/2";

struct NativeVehicleExternalProviderBundleV2 {
    NativeVehiclePassCallback contact_factor{};
    NativeVehiclePassCallback wheel_update{};
    NativeVehiclePassCallback contact_response{};
    NativeVehicleContactOuterInputProvider contact_outer_input{};
    NativeVehicleMotionReadEffectProvider motion_read_effect{};
    NativeVehicleScalarProviderFactory scalar_provider_factory{};
    NativeVehicleHalfStepRefreshProvider half_step_refresh{};
    physics::Fun007b8810PostHalfStepCallback post_half_step{};
};

struct NativeVehicleProviderSessionV2Telemetry {
    std::size_t contact_factor_call_count = 0u;
    std::size_t wheel_update_call_count = 0u;
    std::size_t contact_response_call_count = 0u;
    std::size_t contact_outer_input_call_count = 0u;
    std::size_t motion_read_effect_call_count = 0u;
    std::size_t scalar_provider_factory_call_count = 0u;
    std::size_t half_step_refresh_call_count = 0u;
    std::size_t post_half_step_call_count = 0u;
    std::size_t native_body0_delta_application_count = 0u;
};

struct NativeVehicleProviderSessionV2Result {
    physics::Fun007682c0Body0DeltaConsumerChainResult joined{};
    std::uint64_t session_step_count = 0u;
    NativeVehicleProviderSessionV2Telemetry telemetry{};
};

class NativeVehicleProviderSessionV2 {
public:
    NativeVehicleProviderSessionV2(
        NativeVehicleExternalProviderBundleV2 providers,
        physics::GlobalVehicleBodyOwnerIdentityHandoff owner_handoff);

    NativeVehicleProviderSessionV2Result execute_explicit_step(
        NativeRuntimeState& runtime,
        double outer_timestep);

    std::uint64_t step_count() const { return step_count_; }
    const NativeVehicleProviderSessionV2Telemetry& last_telemetry() const {
        return last_telemetry_;
    }

private:
    NativeVehicleExternalProviderBundleV2 providers_{};
    physics::GlobalVehicleBodyOwnerIdentityHandoff owner_handoff_{};
    std::uint64_t step_count_ = 0u;
    NativeVehicleProviderSessionV2Telemetry last_telemetry_{};
};

}  // namespace shift::runtime
