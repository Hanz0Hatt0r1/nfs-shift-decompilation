#include "shift_bmw_offset33b_native_selector.hpp"

#include <stdexcept>

namespace shift::runtime::physics {
namespace {

constexpr std::uint32_t kRetailBmwChassisBodyIndex = 0u;
constexpr double kCommonOffsetZ =
    0.011470862470862470862470862470862471;
constexpr double kNormalLowDifficultyOffsetY =
    0.004956085581085581085581085581085581;
constexpr double kNormalDifficultyTwoOffsetY =
   -0.000689602064602064602064602064602065;
constexpr double kDriftOffsetY =
    0.018129356754356754356754356754356754;

shift::runtime::render::VehicleWorldMatrix make_translation(
    double x,
    double y,
    double z) {
    return {
        1.0f, 0.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f, 0.0f,
        0.0f, 0.0f, 1.0f, 0.0f,
        static_cast<float>(x),
        static_cast<float>(y),
        static_cast<float>(z),
        1.0f,
    };
}

}  // namespace

BmwRaceModeSelector silverstone_bmw_playable_selector() {
    BmwRaceModeSelector selector{};
    selector.ready = true;
    selector.use_drift_cgheight_scale = false;
    // FUN_0041a730 initializes the source-backed Player Difficulty property to
    // 1. The native playable slice deliberately selects that admissible value.
    selector.player_difficulty = 1u;
    return selector;
}

BmwBody0OuterVehicleRootBind select_bmw_body0_outer_vehicle_root_bind(
    const BmwRaceModeSelector& selector) {
    if (!selector.ready) {
        throw std::invalid_argument(
            "BMW offset33b selector is not bound");
    }
    if (selector.player_difficulty > 2u) {
        throw std::invalid_argument(
            "BMW offset33b selector requires Player Difficulty 0..2");
    }

    double offset_y = 0.0;
    double cgheight_scale = 0.0;
    if (selector.use_drift_cgheight_scale) {
        offset_y = kDriftOffsetY;
        cgheight_scale = 0.25;
    } else if (selector.player_difficulty == 2u) {
        offset_y = kNormalDifficultyTwoOffsetY;
        cgheight_scale = 0.75;
    } else {
        offset_y = kNormalLowDifficultyOffsetY;
        cgheight_scale = 0.6;
    }

    BmwBody0OuterVehicleRootBind out{};
    out.ready = true;
    out.selector_source_backed = true;
    out.identity_rotation = true;
    out.body_index = kRetailBmwChassisBodyIndex;
    out.use_drift_cgheight_scale =
        selector.use_drift_cgheight_scale;
    out.player_difficulty = selector.player_difficulty;
    out.selected_cgheight_scale = cgheight_scale;
    out.offset33b = {0.0, offset_y, kCommonOffsetZ};

    // Process 1 proves BODY0-local -> outer-Vehicle-root as identity rotation
    // plus translation -offset33b.  Do not promote this matrix to VHF root:
    // outer Vehicle root -> VHF vehicle root remains an independent blocker.
    out.body0_local_to_outer_vehicle_root = make_translation(
        0.0,
        -offset_y,
        -kCommonOffsetZ);
    return out;
}

}  // namespace shift::runtime::physics
