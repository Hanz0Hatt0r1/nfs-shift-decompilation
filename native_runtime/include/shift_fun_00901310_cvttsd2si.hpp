#pragma once

#include <cmath>
#include <cstdint>
#include <limits>

namespace shift::runtime::physics {

inline constexpr const char* kFun00901310Cvttsd2siFormat =
    "SHIFT.Fun00901310Cvttsd2si/1";
inline constexpr std::uintptr_t kFun00901310Entry = 0x00901310u;
inline constexpr std::uintptr_t kFun00901310X87SpillSite = 0x00901322u;
inline constexpr std::uintptr_t kFun00901310Cvttsd2siSite = 0x00901325u;
inline constexpr std::int32_t kFun00901310IntegerIndefinite =
    std::numeric_limits<std::int32_t>::min();

// Retail FUN_00901310 spills the incoming x87 ST0 value to an f64 stack slot
// and executes CVTTSD2SI EAX,m64. Model the returned EAX value exactly.
// MXCSR exception/status-flag side effects are intentionally outside this
// value contract because P2.4 callers consume only the returned integer.
inline std::int32_t execute_fun_00901310_cvttsd2si(double value) {
    if (!std::isfinite(value)) {
        return kFun00901310IntegerIndefinite;
    }

    const double truncated = std::trunc(value);
    constexpr double kInt32Min =
        static_cast<double>(std::numeric_limits<std::int32_t>::min());
    constexpr double kInt32Max =
        static_cast<double>(std::numeric_limits<std::int32_t>::max());

    if (truncated < kInt32Min || truncated > kInt32Max) {
        return kFun00901310IntegerIndefinite;
    }
    return static_cast<std::int32_t>(truncated);
}

static_assert(kFun00901310Entry == 0x00901310u);
static_assert(kFun00901310X87SpillSite == 0x00901322u);
static_assert(kFun00901310Cvttsd2siSite == 0x00901325u);
static_assert(kFun00901310IntegerIndefinite ==
              std::numeric_limits<std::int32_t>::min());

}  // namespace shift::runtime::physics
