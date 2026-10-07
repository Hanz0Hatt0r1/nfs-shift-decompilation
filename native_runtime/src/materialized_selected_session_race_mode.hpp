#pragma once

#include "shift_race_mode_player_difficulty.hpp"

namespace shift::runtime {

inline constexpr const char* kSelectedSessionRaceModeSelectionFormat =
    "SHIFT.BMWOffset33bNativeSessionSelection/1";

// Materialized from evidence/bmw_offset33b_native_silverstone_session.json.
// This is the explicit Silverstone+BMW native vertical-slice policy validated
// against the retail Player Difficulty domain. It is deliberately not claimed
// to be an observation of every retail live session.
inline constexpr physics::RaceModePlayerDifficulty
    kMaterializedSelectedSessionPlayerDifficulty{true, 1};

static_assert(kMaterializedSelectedSessionPlayerDifficulty.ready);
static_assert(
    kMaterializedSelectedSessionPlayerDifficulty.player_difficulty == 1);

}  // namespace shift::runtime
