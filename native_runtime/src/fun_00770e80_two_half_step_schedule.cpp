#include "shift_fun_00770e80_two_half_step_schedule.hpp"

#include <cmath>
#include <stdexcept>

namespace shift::runtime::physics {

Fun00770e80TwoHalfStepScheduleResult
execute_fun_00770e80_two_half_step_schedule(
    double outer_timestep,
    const Fun0076d100PassCallback& physics_pass,
    const Fun00765470HalfStepCallback& half_step,
    const Fun007b8810PostHalfStepCallback& post_half_step) {
    if (!std::isfinite(outer_timestep)) {
        throw std::invalid_argument("FUN_00770e80 outer timestep must be finite");
    }
    if (!physics_pass || !half_step || !post_half_step) {
        throw std::invalid_argument(
            "FUN_00770e80 proven schedule requires all three callback boundaries");
    }

    const double half_timestep = outer_timestep * 0.5;
    if (!std::isfinite(half_timestep)) {
        throw std::invalid_argument("FUN_00770e80 half timestep is non-finite");
    }

    Fun00770e80TwoHalfStepScheduleResult result{};
    result.outer_timestep = outer_timestep;
    result.half_timestep = half_timestep;

    for (std::size_t pass_index = 0u;
         pass_index < kFun00770e80PassCount;
         ++pass_index) {
        physics_pass(pass_index);
        ++result.physics_pass_count;

        half_step(pass_index, half_timestep);
        ++result.half_step_count;

        post_half_step(pass_index);
        ++result.post_half_step_count;
    }

    return result;
}

}  // namespace shift::runtime::physics
