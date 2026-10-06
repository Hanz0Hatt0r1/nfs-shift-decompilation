#pragma once

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <thread>

namespace shift::runtime {

// Compatibility/source contract retained from Phase 710.  The value is host
// development pacing only; it is not a recovered retail scheduler/cadence.
inline constexpr double kNativeContinuousFixedDt = 1.0 / 60.0;
inline constexpr double kHostDevelopmentFixedDt = kNativeContinuousFixedDt;

enum class RuntimeSchedulerAuthority {
    HostDevelopment,
    RetailEvidence,
};

// Positive S5 outer-scheduler evidence is deliberately distinct from both the
// host-development loop clock and the resource-loaded inner physics rate.
inline constexpr double kRetailOuterNominalFrequencyHz = 30.0;
inline constexpr int kRetailOuterGatePeriodMs = 33;
inline constexpr double kRetailNormalOuterIncrementSeconds =
    0.03333333507180214;
inline constexpr int kRetailSteadySchedulerInvocationsPerDispatch = 1;

struct RetailOuterSchedulerContract {
    RuntimeSchedulerAuthority scheduler_authority =
        RuntimeSchedulerAuthority::HostDevelopment;
    bool retail_outer_cadence_admitted = false;
    double nominal_frequency_hz = 0.0;
    int gate_period_ms = 0;
    double normal_outer_increment_seconds = 0.0;
    int steady_scheduler_invocations_per_dispatch = 0;

    // This value may only come from a selected-session loaded-rate proof.  The
    // PhysicsTweaker constructor default is intentionally not encoded here.
    bool loaded_inner_rate_admitted = false;
    double loaded_inner_rate_hz = 0.0;
    double pending_accumulator_seconds = 0.0;

    bool uses_admitted_retail_outer_scheduler() const noexcept {
        return scheduler_authority == RuntimeSchedulerAuthority::RetailEvidence &&
               retail_outer_cadence_admitted;
    }

    bool inner_rate_ready() const noexcept {
        return uses_admitted_retail_outer_scheduler() &&
               loaded_inner_rate_admitted &&
               std::isfinite(loaded_inner_rate_hz) &&
               loaded_inner_rate_hz > 0.0;
    }

    void admit_outer_dispatch() {
        if (!uses_admitted_retail_outer_scheduler()) {
            throw std::logic_error(
                "retail outer dispatch requires admitted RetailEvidence authority");
        }
        if (steady_scheduler_invocations_per_dispatch != 1) {
            throw std::logic_error(
                "retail outer dispatch multiplicity is not the proven steady value");
        }
        if (!std::isfinite(pending_accumulator_seconds) ||
            pending_accumulator_seconds < 0.0) {
            throw std::logic_error(
                "retail outer accumulator is not a finite non-negative value");
        }
        if (!std::isfinite(normal_outer_increment_seconds) ||
            !(normal_outer_increment_seconds > 0.0) ||
            pending_accumulator_seconds >
                std::numeric_limits<double>::max() -
                    normal_outer_increment_seconds) {
            throw std::overflow_error(
                "retail outer accumulator cannot accept another dispatch");
        }
        pending_accumulator_seconds += normal_outer_increment_seconds;
    }

    void admit_loaded_inner_rate(double rate_hz) {
        if (!uses_admitted_retail_outer_scheduler()) {
            throw std::logic_error(
                "inner rate cannot be admitted before retail outer authority");
        }
        // The recovered PhysicsTweaker loader stores this property through a
        // uint16 field.  Mirror the selected-session materializer contract here
        // so a fractional/oversized synthetic value cannot cross the native seam.
        if (!std::isfinite(rate_hz) || !(rate_hz > 0.0) ||
            rate_hz != std::floor(rate_hz) || rate_hz > 65535.0) {
            throw std::invalid_argument(
                "loaded retail inner rate must be a positive integral uint16 value");
        }
        loaded_inner_rate_hz = rate_hz;
        loaded_inner_rate_admitted = true;
    }

    double inner_substep_seconds() const {
        if (!inner_rate_ready()) {
            throw std::logic_error(
                "loaded PhysicsTweaker tick rate is required before inner substeps");
        }
        return 1.0 / loaded_inner_rate_hz;
    }

    double inner_accumulator_tolerance_seconds() const {
        const double scale = std::max(
            1.0,
            std::max(
                std::abs(pending_accumulator_seconds),
                std::abs(inner_substep_seconds())));
        return 64.0 * std::numeric_limits<double>::epsilon() * scale;
    }

    bool has_ready_inner_substep() const {
        if (!inner_rate_ready()) {
            throw std::logic_error(
                "loaded PhysicsTweaker tick rate is required before inner substeps");
        }
        if (!std::isfinite(pending_accumulator_seconds) ||
            pending_accumulator_seconds < 0.0) {
            throw std::logic_error(
                "retail inner accumulator is not a finite non-negative value");
        }
        return pending_accumulator_seconds +
                   inner_accumulator_tolerance_seconds() >=
               inner_substep_seconds();
    }

    template <typename StepFn>
    std::size_t drain_ready_inner_substeps(StepFn&& step_fn) {
        if (!inner_rate_ready()) {
            throw std::logic_error(
                "loaded PhysicsTweaker tick rate is required before inner substeps");
        }

        std::size_t executed = 0;
        while (has_ready_inner_substep()) {
            if (executed == std::numeric_limits<std::size_t>::max()) {
                throw std::overflow_error(
                    "retail inner substep execution count overflow");
            }

            const double substep_seconds = inner_substep_seconds();
            const double tolerance = inner_accumulator_tolerance_seconds();
            double next_pending =
                pending_accumulator_seconds - substep_seconds;
            if (next_pending < 0.0) {
                if (-next_pending > tolerance) {
                    throw std::logic_error(
                        "retail inner substep would over-consume the accumulator");
                }
                next_pending = 0.0;
            }

            // Commit accumulator consumption only after the consumer accepted
            // the exact 1/rate step.  A throwing physics step therefore leaves
            // scheduler time pending for a deterministic retry instead of
            // silently dropping a selected-session substep.
            step_fn(substep_seconds);
            pending_accumulator_seconds = next_pending;
            ++executed;
        }
        return executed;
    }
};

inline RetailOuterSchedulerContract make_retail_outer_scheduler_contract(
    bool evidence_ready,
    double nominal_frequency_hz,
    int gate_period_ms,
    double normal_outer_increment_seconds,
    int steady_scheduler_invocations_per_dispatch) {

    constexpr double kFrequencyTolerance = 1e-12;
    constexpr double kIncrementTolerance = 1e-12;
    if (!evidence_ready ||
        !std::isfinite(nominal_frequency_hz) ||
        std::abs(nominal_frequency_hz - kRetailOuterNominalFrequencyHz) >
            kFrequencyTolerance ||
        gate_period_ms != kRetailOuterGatePeriodMs ||
        !std::isfinite(normal_outer_increment_seconds) ||
        std::abs(
            normal_outer_increment_seconds -
            kRetailNormalOuterIncrementSeconds) > kIncrementTolerance ||
        steady_scheduler_invocations_per_dispatch !=
            kRetailSteadySchedulerInvocationsPerDispatch) {
        throw std::invalid_argument(
            "retail outer scheduler handoff does not match the proven S5 contract");
    }

    RetailOuterSchedulerContract contract{};
    contract.scheduler_authority = RuntimeSchedulerAuthority::RetailEvidence;
    contract.retail_outer_cadence_admitted = true;
    contract.nominal_frequency_hz = nominal_frequency_hz;
    contract.gate_period_ms = gate_period_ms;
    contract.normal_outer_increment_seconds = normal_outer_increment_seconds;
    contract.steady_scheduler_invocations_per_dispatch =
        steady_scheduler_invocations_per_dispatch;
    return contract;
}

struct RuntimeLoopPolicy {
    bool continuous = false;
    bool frame_limit_enabled = true;
    int frame_limit = 120;
    bool continuous_wall_clock_pacing = false;
    double fixed_tick_seconds = kHostDevelopmentFixedDt;
    RuntimeSchedulerAuthority scheduler_authority =
        RuntimeSchedulerAuthority::HostDevelopment;
    bool retail_cadence_admitted = false;

    mutable bool tick_clock_started = false;
    mutable std::chrono::steady_clock::time_point next_tick{};

    bool uses_host_development_scheduler() const noexcept {
        return scheduler_authority == RuntimeSchedulerAuthority::HostDevelopment;
    }

    bool uses_admitted_retail_scheduler() const noexcept {
        return scheduler_authority == RuntimeSchedulerAuthority::RetailEvidence &&
               retail_cadence_admitted;
    }

    void pace_continuous_tick() const {
        if (!continuous || !continuous_wall_clock_pacing) {
            return;
        }
        if (!uses_host_development_scheduler() || retail_cadence_admitted) {
            throw std::logic_error(
                "host 1/60 pacing cannot satisfy retail scheduler/cadence authority");
        }
        if (!(fixed_tick_seconds > 0.0)) {
            throw std::logic_error("continuous runtime fixed tick must be positive");
        }

        const auto tick = std::chrono::duration_cast<
            std::chrono::steady_clock::duration>(
                std::chrono::duration<double>(fixed_tick_seconds));
        if (tick <= std::chrono::steady_clock::duration::zero()) {
            throw std::logic_error("continuous runtime fixed tick is below clock resolution");
        }

        const auto now = std::chrono::steady_clock::now();
        if (!tick_clock_started) {
            tick_clock_started = true;
            next_tick = now + tick;
            return;
        }

        if (now < next_tick) {
            std::this_thread::sleep_until(next_tick);
        }
        // Preserve every native tick.  If rendering is late, do not invent a
        // retail catch-up/drop policy: subsequent iterations run without sleep
        // until this explicitly host-only schedule catches up.
        next_tick += tick;
    }

    bool should_continue(bool quit, int rendered_frames) const {
        if (quit) {
            return false;
        }
        if (frame_limit_enabled && rendered_frames >= frame_limit) {
            return false;
        }
        pace_continuous_tick();
        return true;
    }
};

inline RuntimeLoopPolicy make_runtime_loop_policy(
    bool continuous,
    bool frames_explicit,
    int requested_frames,
    bool input_script_mode,
    std::size_t input_script_steps) {

    if (requested_frames <= 0) {
        throw std::invalid_argument("runtime frame limit must be positive");
    }

    if (input_script_mode) {
        if (continuous) {
            throw std::invalid_argument(
                "--continuous cannot be combined with --input-script");
        }
        if (input_script_steps == 0 ||
            input_script_steps > static_cast<std::size_t>(
                std::numeric_limits<int>::max())) {
            throw std::invalid_argument(
                "native input script has invalid fixed-step cardinality");
        }
        const int script_frames = static_cast<int>(input_script_steps);
        if (frames_explicit && requested_frames != script_frames) {
            throw std::invalid_argument(
                "--frames must equal native input script step count");
        }
        return RuntimeLoopPolicy{false, true, script_frames};
    }

    if (continuous) {
        // An explicit --frames value is an optional regression/safety cap only.
        // Without it, X11 quit/destroy events are the sole normal session end.
        // This factory intentionally produces host-development scheduling only;
        // a positive retail cadence handoff is consumed separately through
        // RetailOuterSchedulerContract and must not inherit this wall-clock pacer.
        RuntimeLoopPolicy policy{true, frames_explicit, requested_frames};
        policy.continuous_wall_clock_pacing = true;
        policy.scheduler_authority = RuntimeSchedulerAuthority::HostDevelopment;
        policy.retail_cadence_admitted = false;
        return policy;
    }

    return RuntimeLoopPolicy{false, true, requested_frames};
}

}  // namespace shift::runtime
