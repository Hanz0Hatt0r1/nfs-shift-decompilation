#pragma once

#include <cstdint>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kRaceModePlayerDifficultyFormat =
    "SHIFT.RaceModePlayerDifficulty/1";

// PC ChangeRaceMode carries Player Difficulty in RaceModeInfo+0x6c. The same
// dword is staged at PhysicsParticipantManager+0x420 (= +0x3b4 + 0x6c) and is
// published by FUN_00714ed0 to DAT_00c128cc. Keep it explicit session state:
// zero is a valid difficulty, so `ready` is required to avoid a silent default.
struct RaceModePlayerDifficulty {
    bool ready = false;
    std::int32_t player_difficulty = 0;
};

inline void validate_race_mode_player_difficulty(
    const RaceModePlayerDifficulty& selector) {
    if (!selector.ready) {
        throw std::invalid_argument(
            "RaceModeInfo Player Difficulty must be explicitly admitted");
    }
    if (selector.player_difficulty < 0 || selector.player_difficulty > 2) {
        throw std::invalid_argument(
            "RaceModeInfo Player Difficulty must be in the retail domain 0..2");
    }
}

}  // namespace shift::runtime::physics
