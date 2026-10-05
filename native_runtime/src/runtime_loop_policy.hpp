#pragma once

#include <chrono>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <thread>

namespace shift::runtime {

// Current continuous pacing is a host-development mechanism only.  It is not a
// recovered retail scheduler/cadence and must never become one by implication.
inline constexpr double kHostDevelopmentFixedDt = 1.0 / 60.0;
// Compatibility name retained for existing non-retail callers/tests.
inline constexpr double kNativeContinuousFixedDt = kHostDevelopmentFixedDt;

enum class RuntimeSchedulerAuthority {
    HostDevelopment,
    RetailEvidence,
};

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
        RuntimeLoopPolicy policy{false, true, script_frames};
        policy.scheduler_authority = RuntimeSchedulerAuthority::HostDevelopment;
        policy.retail_cadence_admitted = false;
        return policy;
    }

    if (continuous) {
        // An explicit --frames value is an optional regression/safety cap only.
        // Without it, X11 quit/destroy events are the sole normal session end.
        // This factory intentionally produces host-development scheduling only;
        // a future positive retail cadence handoff must select RetailEvidence
        // explicitly and must disable this wall-clock pacer rather than inherit it.
        RuntimeLoopPolicy policy{true, frames_explicit, requested_frames};
        policy.continuous_wall_clock_pacing = true;
        policy.scheduler_authority = RuntimeSchedulerAuthority::HostDevelopment;
        policy.retail_cadence_admitted = false;
        return policy;
    }

    RuntimeLoopPolicy policy{false, true, requested_frames};
    policy.scheduler_authority = RuntimeSchedulerAuthority::HostDevelopment;
    policy.retail_cadence_admitted = false;
    return policy;
}

}  // namespace shift::runtime
