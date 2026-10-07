#pragma once

#include <cstdint>

namespace shift::runtime::physics {

inline constexpr const char* kSelectedSessionAngleModeFormat =
    "SHIFT.SelectedSessionAngleMode/1";
inline constexpr const char* kSelectedSessionTarget =
    "Silverstone+BMW_M3_E36";
inline constexpr std::int32_t kSelectedSessionPlayerDifficulty = 1;

static_assert(
    kSelectedSessionPlayerDifficulty >= 0 &&
        kSelectedSessionPlayerDifficulty <= 2,
    "selected native session difficulty must remain inside the proven retail domain");

// PC retail copies RaceModeInfo+0x6c to DAT_00c128cc and FUN_007682c0 compares
// that value against 1. The target native Silverstone slice already owns an
// explicit Player Difficulty=1 policy validated against the retail {0,1,2}
// domain. This is a native session selection, not a claim about an observed
// retail live-session default.
inline constexpr std::int32_t selected_session_fun_007682c0_angle_mode() {
    return kSelectedSessionPlayerDifficulty;
}

}  // namespace shift::runtime::physics
