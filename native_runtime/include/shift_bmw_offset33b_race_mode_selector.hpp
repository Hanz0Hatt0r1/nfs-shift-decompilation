#pragma once

#include "shift_vehicle_world_transform_transport.hpp"

#include <array>
#include <cstdint>

namespace shift::runtime::physics {

inline constexpr const char* kNativeBmwOffset33bRaceModeSelectorFormat =
    "SHIFT.NativeBMWOffset33bRaceModeSelector/1";

// Source-backed selector shape carried by retail ChangeRaceMode state:
//   RaceModeInfo+0x0e -> normal/drift CGHeight-scale selector
//   RaceModeInfo+0x6c -> Player Difficulty (0-2)
// No default is inferred here.  `ready` must be set by a producer that owns
// those session semantics.
struct BmwOffset33bRaceModeSelector {
    bool ready = false;
    bool use_drift_cgheight_scale = false;
    std::uint32_t player_difficulty = 0u;
};

struct BmwBody0OuterVehicleBindSelection {
    BmwOffset33bRaceModeSelector selector{};
    double cgheight_scale = 0.0;
    std::array<double, 3> target_cg{};
    std::array<double, 3> auxiliary_weighted_com{};
    std::array<double, 3> offset33b{};
    std::array<double, 3> body0_to_outer_vehicle_translation{};
    shift::runtime::render::VehicleWorldMatrix
        body0_local_to_outer_vehicle_root{};
};

// Consume the selector-complete Process 1 BMW family.  This is intentionally
// only BODY0-local -> outer Vehicle.  It does not claim outer Vehicle -> VHF
// vehicle-root identity and therefore cannot by itself manufacture a
// ProvenBmwBody0BindFrame.
BmwBody0OuterVehicleBindSelection
select_bmw_body0_outer_vehicle_bind(
    const BmwOffset33bRaceModeSelector& selector);

}  // namespace shift::runtime::physics
