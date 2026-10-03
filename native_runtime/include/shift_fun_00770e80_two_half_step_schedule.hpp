#pragma once

#include <cstddef>
#include <functional>

namespace shift::runtime::physics {

inline constexpr const char* kNativeFun00770e80TwoHalfStepScheduleFormat =
    "SHIFT.NativeFun00770e80TwoHalfStepSchedule/1";
inline constexpr const char* kFun00770e80OuterUpdate = "FUN_00770e80";
inline constexpr const char* kFun0076d100PhysicsPass = "FUN_0076d100";
inline constexpr const char* kFun00765470HalfStep = "FUN_00765470";
inline constexpr const char* kFun007b8810PostHalfStep = "FUN_007b8810";
inline constexpr std::size_t kFun00770e80PassCount = 2u;

using Fun0076d100PassCallback = std::function<void(std::size_t pass_index)>;
using Fun00765470HalfStepCallback =
    std::function<void(std::size_t pass_index, double half_timestep)>;
using Fun007b8810PostHalfStepCallback =
    std::function<void(std::size_t pass_index)>;

struct Fun00770e80TwoHalfStepScheduleResult {
    double outer_timestep = 0.0;
    double half_timestep = 0.0;
    std::size_t physics_pass_count = 0u;
    std::size_t half_step_count = 0u;
    std::size_t post_half_step_count = 0u;
};

Fun00770e80TwoHalfStepScheduleResult
execute_fun_00770e80_two_half_step_schedule(
    double outer_timestep,
    const Fun0076d100PassCallback& physics_pass,
    const Fun00765470HalfStepCallback& half_step,
    const Fun007b8810PostHalfStepCallback& post_half_step);

}  // namespace shift::runtime::physics
