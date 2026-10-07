#pragma once

#include <cstdint>

namespace shift::runtime::physics {

inline constexpr const char* kBmwNativeSessionPlayerDifficultyFormat =
    "SHIFT.BMWNativeSessionPlayerDifficulty/1";

// The selected native Silverstone + BMW_M3_E36 vertical slice already binds
// Player Difficulty=1 through SHIFT.BMWOffset33bNativeSessionSelection/1.
// PC retail static evidence independently proves RaceModeInfo+0x6c is copied to
// DAT_00c128cc, which FUN_007682c0 reads as its angle-limit selector. This is a
// native-session policy value validated against the retail {0,1,2} domain; it is
// not a claim that every retail session uses the profile initialization default.
inline constexpr std::int32_t kBmwNativeSilverstonePlayerDifficulty = 1;

static_assert(
    kBmwNativeSilverstonePlayerDifficulty >= 0 &&
        kBmwNativeSilverstonePlayerDifficulty <= 2,
    "selected native Player Difficulty must remain in the proven retail domain");

inline constexpr std::int32_t selected_bmw_native_session_player_difficulty() {
    return kBmwNativeSilverstonePlayerDifficulty;
}

}  // namespace shift::runtime::physics
