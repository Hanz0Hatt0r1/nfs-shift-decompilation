#pragma once

#include "materialized_selected_session_physics_tweaker_rate.hpp"
#include "materialized_selected_session_race_mode.hpp"
#include "runtime_loop_policy.hpp"
#include "selected_session_physics_tweaker_rate_handoff.hpp"
#include "shift_native_vehicle_provider_session.hpp"

#include <stdexcept>

namespace shift::runtime {

inline constexpr const char* kSelectedSessionRetailVehicleExecutionFormat =
    "SHIFT.SelectedSessionRetailVehicleExecution/1";

// Own the selected persistent retail scheduling/session policy handoffs for
// explicit outer-manager dispatches. Timing comes from the hash-verified PC
// PhysicsTweaker resource; Player Difficulty comes from the already-admitted
// BMW native-session selector family. Neither is derived from host/render 1/60.
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
        physics::validate_race_mode_player_difficulty(
            kMaterializedSelectedSessionPlayerDifficulty);
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

    const physics::RaceModePlayerDifficulty& race_mode() const noexcept {
        return kMaterializedSelectedSessionPlayerDifficulty;
    }

    NativeVehicleRetailInnerBatchResult execute_outer_dispatch(
        NativeVehicleProviderSession& session,
        NativeRuntimeState& runtime) {
        return session.execute_retail_outer_dispatch(runtime, scheduler_);
    }

private:
    RetailOuterSchedulerContract scheduler_{};
};

}  // namespace shift::runtime
