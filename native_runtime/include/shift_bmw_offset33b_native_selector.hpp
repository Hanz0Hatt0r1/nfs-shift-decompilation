#pragma once

#include "shift_vehicle_world_transform_transport.hpp"

#include <array>
#include <cstdint>

namespace shift::runtime::physics {

inline constexpr const char* kNativeBmwOffset33bSelectorFormat =
    "SHIFT.NativeBMWOffset33bSelector/1";

struct BmwRaceModeSelector {
    bool ready = false;
    bool use_drift_cgheight_scale = false;
    std::uint32_t player_difficulty = 0u;
};

struct BmwBody0OuterVehicleRootBind {
    bool ready = false;
    bool selector_source_backed = false;
    bool identity_rotation = false;
    std::uint32_t body_index = 0u;
    bool use_drift_cgheight_scale = false;
    std::uint32_t player_difficulty = 0u;
    double selected_cgheight_scale = 0.0;
    std::array<double, 3> offset33b{};
    shift::runtime::render::VehicleWorldMatrix
        body0_local_to_outer_vehicle_root{};
};

// Deterministic policy for the first playable Linux vertical slice.
// It selects one member of the source-backed retail selector family proved by
// Process 1 PR #1276. It is not a claim about a captured retail session.
BmwRaceModeSelector silverstone_bmw_playable_selector();

BmwBody0OuterVehicleRootBind select_bmw_body0_outer_vehicle_root_bind(
    const BmwRaceModeSelector& selector);

}  // namespace shift::runtime::physics
