#include "shift_bmw_offset33b_race_mode_selector.hpp"

#include <array>
#include <stdexcept>

namespace shift::runtime::physics {
namespace {

constexpr double kBmwCgHeight = 0.28;
constexpr double kBmwTargetCgX = 0.0;
constexpr double kBmwTargetCgZ = -0.081;
constexpr double kBmwAuxiliaryMass = 173.0;
constexpr double kBmwBody0Mass = 1287.0;
constexpr double kBmwMassRatio = kBmwAuxiliaryMass / kBmwBody0Mass;

constexpr std::array<double, 3> kBmwAuxiliaryWeightedCom{
    0.0,
    0.20486983897605284888521882741535920726672171758877,
    0.0043352601156069364161849710982658959537572254335260,
};

// Player Difficulty is source-backed as the reflected domain (0-2).  The
// fourth PhysicsTweaker array lane is deliberately not admitted here.
constexpr std::array<double, 3> kNormalCgHeightScale{
    0.6,
    0.6,
    0.75,
};
constexpr std::array<double, 3> kDriftCgHeightScale{
    0.25,
    0.25,
    0.25,
};

shift::runtime::render::VehicleWorldMatrix translation_matrix(
    const std::array<double, 3>& translation) {
    return {
        1.0f, 0.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f, 0.0f,
        0.0f, 0.0f, 1.0f, 0.0f,
        static_cast<float>(translation[0]),
        static_cast<float>(translation[1]),
        static_cast<float>(translation[2]),
        1.0f,
    };
}

}  // namespace

BmwBody0OuterVehicleBindSelection
select_bmw_body0_outer_vehicle_bind(
    const BmwOffset33bRaceModeSelector& selector) {
    if (!selector.ready) {
        throw std::invalid_argument(
            "BMW offset33b race-mode selector is not source-backed/ready");
    }
    if (selector.player_difficulty > 2u) {
        throw std::out_of_range(
            "BMW offset33b Player Difficulty must be in the retail domain 0..2");
    }

    const auto& scales = selector.use_drift_cgheight_scale
        ? kDriftCgHeightScale
        : kNormalCgHeightScale;
    const double scale = scales[selector.player_difficulty];

    BmwBody0OuterVehicleBindSelection out{};
    out.selector = selector;
    out.cgheight_scale = scale;
    out.target_cg = {
        kBmwTargetCgX,
        kBmwCgHeight * scale,
        kBmwTargetCgZ,
    };
    out.auxiliary_weighted_com = kBmwAuxiliaryWeightedCom;

    for (std::size_t axis = 0; axis < out.offset33b.size(); ++axis) {
        out.offset33b[axis] =
            (out.auxiliary_weighted_com[axis] - out.target_cg[axis]) *
            kBmwMassRatio;
        out.body0_to_outer_vehicle_translation[axis] = -out.offset33b[axis];
    }
    out.body0_local_to_outer_vehicle_root =
        translation_matrix(out.body0_to_outer_vehicle_translation);
    return out;
}

}  // namespace shift::runtime::physics
