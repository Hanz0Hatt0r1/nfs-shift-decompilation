#pragma once

#include "materialized_selected_session_physics_tweaker_rate.hpp"
#include "runtime_loop_policy.hpp"
#include "selected_session_physics_tweaker_rate_handoff.hpp"
#include "shift_native_vehicle_provider_session.hpp"

#include <stdexcept>

namespace shift::runtime {

inline constexpr const char* kSelectedSessionRetailVehicleExecutionFormat =
    "SHIFT.SelectedSessionRetailVehicleExecution/1";

// Own the persistent retail scheduler state for explicit outer-manager dispatches.
// Construction consumes only the materialized, hash-verified PC PhysicsTweaker
// handoff. It does not derive timing from the host/render 1/60 loop and it does
// not provide or promote any of the nine external vehicle-provider semantics.
class SelectedSessionRetailVehicleExecution {
public:
    SelectedSessionRetailVehicleExecution()
        : scheduler_(make_retail_outer_scheduler_contract(
              true,
              kRetailOuterNominalFrequencyHz,
              kRetailOuterGatePeriodMs,
              kRetailNormalOuterIncrementSeconds,
              kRetailSteadySchedulerInvocationsPerDispatch)) {
        const double admitted_rate = admit_selected_session_physics_tweaker_rate(
            scheduler_,
            kMaterializedSelectedSessionPhysicsTweakerRateHandoff);
        if (!scheduler_.inner_rate_ready() ||
            admitted_rate != scheduler_.loaded_inner_rate_hz ||
            admitted_rate != static_cast<double>(
                kMaterializedSelectedSessionPhysicsTweakerRateHandoff.rate_hz)) {
            throw std::logic_error(
                "materialized selected-session retail rate was not admitted exactly");
        }
    }

    const RetailOuterSchedulerContract& scheduler() const noexcept {
        return scheduler_;
    }

    RetailOuterSchedulerContract& scheduler() noexcept {
        return scheduler_;
    }

    NativeVehicleRetailInnerBatchResult execute_outer_dispatch(
        NativeVehicleProviderSession& session,
        NativeRuntimeState& runtime) {
        // The caller supplies the recovered outer-manager dispatch event. This
        // seam deliberately never treats a rendered frame or host 1/60 tick as
        // that event. NativeVehicleProviderSession owns the atomic accumulator +
        // persistent BODY batch transaction and preserves its existing rollback.
        return session.execute_retail_outer_dispatch(runtime, scheduler_);
    }

private:
    RetailOuterSchedulerContract scheduler_{};
};

}  // namespace shift::runtime
