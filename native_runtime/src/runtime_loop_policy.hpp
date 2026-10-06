#pragma once

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <thread>

namespace shift::runtime {

// Compatibility/source contract retained from Phase 710. The value is host
// development pacing only; it is not a recovered retail scheduler/cadence.
inline constexpr double kNativeContinuousFixedDt = 1.0 / 60.0;
inline constexpr double kHostDevelopmentFixedDt = kNativeContinuousFixedDt;

// S5 recovered retail outer-manager scheduling contract. These are deliberately
// distinct quantities: BManager stores ROUND(1000 / 30) == 33 ms for the
// manager timing gate, while the normal physics-scheduler accumulator receives
// approximately 1/30 s. The inner physics substep remains 1/rate and is not
// represented by either constant here.
inline constexpr double kRetailOuterNominalFrequencyHz = 30.0;
inline constexpr int kRetailOuterGatePeriodMilliseconds = 33;
inline constexpr double kRetailOuterNormalIncrementSeconds = 1.0 / 30.0;

enum class RuntimeSchedulerAuthority {
    HostDevelopment,
    RetailEvidence,
};

// Explicit consumer for SHIFT.RetailOuterUpdateCadence/1 plus
// SHIFT.RetailOuterUpdateCadenceCompletion/1. It models the proven default
// BManager mode as a quantized 33 ms gate which may release at most one outer
// update per poll. If a poll is late, deadlines advance one gate at a time so
// subsequent polls can catch up without dropping an admitted outer update.
//
// This component intentionally does not call NativeRuntimeState::fixed_step()
// and does not own any Phase 699/S6 provider semantics. S6 attaches the existing
// explicit outer-update/provider-session callback to this gate.
struct RetailOuterUpdateScheduler {
    using Clock = std::chrono::steady_clock;

    RuntimeSchedulerAuthority scheduler_authority =
        RuntimeSchedulerAuthority::RetailEvidence;
    bool retail_cadence_admitted = true;
    bool gate_started = false;
    Clock::time_point next_gate{};
    std::uint64_t dispatch_count = 0;

    bool uses_admitted_retail_scheduler() const noexcept {
        return scheduler_authority == RuntimeSchedulerAuthority::RetailEvidence &&
               retail_cadence_admitted;
    }

    template <typename Callback>
    bool poll(Clock::time_point now, Callback&& callback) {
        if (!uses_admitted_retail_scheduler()) {
            throw std::logic_error(
                "retail outer scheduler requires admitted RetailEvidence authority");
        }

        const auto gate = std::chrono::milliseconds(
            kRetailOuterGatePeriodMilliseconds);
        if (!gate_started) {
            gate_started = true;
            next_gate = now + gate;
            return false;
        }
        if (now < next_gate) {
            return false;
        }

        callback(kRetailOuterNormalIncrementSeconds);
        ++dispatch_count;
        next_gate += gate;
        return true;
    }

    template <typename Callback>
    bool wait_and_poll(Callback&& callback) {
        if (!uses_admitted_retail_scheduler()) {
            throw std::logic_error(
                "retail outer scheduler requires admitted RetailEvidence authority");
        }
        auto now = Clock::now();
        if (!gate_started) {
            gate_started = true;
            next_gate = now + std::chrono::milliseconds(
                kRetailOuterGatePeriodMilliseconds);
        }
        if (now < next_gate) {
            std::this_thread::sleep_until(next_gate);
            now = Clock::now();
        }
        return poll(now, callback);
    }
};

inline RetailOuterUpdateScheduler make_retail_outer_update_scheduler() {
    return RetailOuterUpdateScheduler{};
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
        // Preserve every native tick. If rendering is late, do not invent a
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
        // This factory remains host-development scheduling. Retail cadence uses
        // RetailOuterUpdateScheduler and therefore never inherits this 1/60
        // wall-clock pacer.
        RuntimeLoopPolicy policy{true, frames_explicit, requested_frames};
        policy.continuous_wall_clock_pacing = true;
        policy.scheduler_authority = RuntimeSchedulerAuthority::HostDevelopment;
        policy.retail_cadence_admitted = false;
        return policy;
    }

    return RuntimeLoopPolicy{false, true, requested_frames};
}

}  // namespace shift::runtime
