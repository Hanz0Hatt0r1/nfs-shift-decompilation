#pragma once

#include <cstddef>
#include <optional>

namespace shift::runtime::physics {

inline constexpr const char* kNativeSpringGapStateFormat =
    "SHIFT.NativeSpringGapState/1";
inline constexpr const char* kSpringGapFunction = "FUN_007555b0";
inline constexpr const char* kSpringGapCallerFunction = "FUN_00755950";
inline constexpr std::size_t kSpringGapCurrentOffset = 0x248u;
inline constexpr std::size_t kSpringGapPreviousOffset = 0x250u;
inline constexpr std::size_t kSpringGapTriggerOffset = 0x258u;
inline constexpr std::size_t kSpringGapCrossingFlagOffset = 0x260u;
inline constexpr std::size_t kSpringGapLowerBoundaryOffset = 0x238u;
inline constexpr std::size_t kSpringGapUpperBoundaryOffset = 0x240u;

struct SpringGapStateInput {
    int spring_type = 0;
    double displacement = 0.0;
    double lower_boundary = 0.0;
    double upper_boundary = 0.0;
    double previous_gap = 0.0;
    double trigger_value = 0.0;
};

struct SpringGapStateResult {
    int spring_type = 0;
    double displacement = 0.0;
    double previous_gap = 0.0;
    double current_gap = 0.0;
    bool transition_triggered = false;
    std::optional<double> trigger_value{};
};

double compute_fun_007555b0_gap(
    double displacement,
    double lower_boundary,
    double upper_boundary);

SpringGapStateResult execute_fun_007555b0_gap_state(
    const SpringGapStateInput& input);

}  // namespace shift::runtime::physics
