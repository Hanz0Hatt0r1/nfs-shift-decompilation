#pragma once

#include <cstddef>
#include <functional>

namespace shift::runtime::physics {

inline constexpr const char* kNativeFun0076d100AnchorSequenceFormat =
    "SHIFT.NativeFun0076d100AnchorSequence/1";
inline constexpr const char* kFun0076d100PhysicsPassFunction = "FUN_0076d100";
inline constexpr const char* kFun00765c40ContactFactorFunction = "FUN_00765c40";
inline constexpr const char* kFun00758b50WheelUpdateFunction = "FUN_00758b50";
inline constexpr const char* kFun00766510ContactResponseFunction = "FUN_00766510";
inline constexpr const char* kFun00769ef0TailFunction = "FUN_00769ef0";
inline constexpr const char* kFun007675f0ContactOuterFunction = "FUN_007675f0";
inline constexpr const char* kFun007682c0MotionReadGateFunction = "FUN_007682c0";

using Fun0076d100AnchorCallback = std::function<void()>;

struct Fun0076d100AnchorSequenceResult {
    std::size_t contact_factor_count = 0u;
    std::size_t wheel_update_count = 0u;
    std::size_t contact_response_count = 0u;
    std::size_t tail_invocation_count = 0u;
    std::size_t contact_outer_count = 0u;
    std::size_t motion_read_gate_count = 0u;
};

Fun0076d100AnchorSequenceResult execute_fun_0076d100_required_anchor_sequence(
    const Fun0076d100AnchorCallback& contact_factor,
    const Fun0076d100AnchorCallback& wheel_update,
    const Fun0076d100AnchorCallback& contact_response,
    const Fun0076d100AnchorCallback& contact_outer,
    const Fun0076d100AnchorCallback& motion_read_gate);

}  // namespace shift::runtime::physics
