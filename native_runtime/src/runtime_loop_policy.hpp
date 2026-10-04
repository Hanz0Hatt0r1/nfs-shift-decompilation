#pragma once

#include <cstddef>
#include <limits>
#include <stdexcept>

namespace shift::runtime {

struct RuntimeLoopPolicy {
    bool continuous = false;
    bool frame_limit_enabled = true;
    int frame_limit = 120;

    bool should_continue(bool quit, int rendered_frames) const {
        if (quit) {
            return false;
        }
        return !frame_limit_enabled || rendered_frames < frame_limit;
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
        return RuntimeLoopPolicy{
            true,
            frames_explicit,
            requested_frames,
        };
    }

    return RuntimeLoopPolicy{false, true, requested_frames};
}

}  // namespace shift::runtime
