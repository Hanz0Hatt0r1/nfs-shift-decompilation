#include "shift_bmw_offset33b_native_selector.hpp"

#include <cmath>
#include <cstdint>
#include <iostream>
#include <stdexcept>

namespace {

using shift::runtime::physics::BmwBody0OuterVehicleRootBind;
using shift::runtime::physics::BmwRaceModeSelector;

constexpr double kTolerance = 1.0e-7;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void require_close(double actual, double expected, const char* message) {
    if (std::fabs(actual - expected) > kTolerance) {
        throw std::runtime_error(message);
    }
}

BmwBody0OuterVehicleRootBind select(bool drift, std::uint32_t difficulty) {
    BmwRaceModeSelector selector{};
    selector.ready = true;
    selector.use_drift_cgheight_scale = drift;
    selector.player_difficulty = difficulty;
    return shift::runtime::physics::select_bmw_body0_outer_vehicle_root_bind(
        selector);
}

void check_common(const BmwBody0OuterVehicleRootBind& bind) {
    require(bind.ready, "selector did not produce ready bind");
    require(bind.selector_source_backed, "selector provenance was lost");
    require(bind.identity_rotation, "BODY0 bind rotation is not identity");
    require(bind.body_index == 0u, "BMW chassis BODY index is not zero");

    const auto& m = bind.body0_local_to_outer_vehicle_root;
    require_close(m[0], 1.0, "matrix[0] is not identity");
    require_close(m[5], 1.0, "matrix[5] is not identity");
    require_close(m[10], 1.0, "matrix[10] is not identity");
    require_close(m[15], 1.0, "matrix[15] is not affine identity");
    require_close(m[3], 0.0, "matrix[3] is not affine zero");
    require_close(m[7], 0.0, "matrix[7] is not affine zero");
    require_close(m[11], 0.0, "matrix[11] is not affine zero");
    require_close(m[12], 0.0, "BMW BODY0 bind X translation changed");
    require_close(
        m[14],
        -0.011470862470862471,
        "BMW BODY0 bind Z translation changed");
}

}  // namespace

int main() {
    const auto native_selector =
        shift::runtime::physics::silverstone_bmw_playable_selector();
    require(native_selector.ready, "Silverstone selector is not ready");
    require(
        !native_selector.use_drift_cgheight_scale,
        "Silverstone playable selector unexpectedly uses drift branch");
    require(
        native_selector.player_difficulty == 1u,
        "Silverstone playable selector difficulty is not source-backed default 1");

    const auto native_bind =
        shift::runtime::physics::select_bmw_body0_outer_vehicle_root_bind(
            native_selector);
    check_common(native_bind);
    require_close(
        native_bind.selected_cgheight_scale,
        0.6,
        "normal difficulty 1 CGHeight scale mismatch");
    require_close(
        native_bind.offset33b[1],
        0.004956085581085581,
        "normal difficulty 1 offset33b Y mismatch");
    require_close(
        native_bind.body0_local_to_outer_vehicle_root[13],
        -0.004956085581085581,
        "normal difficulty 1 bind Y mismatch");

    for (std::uint32_t difficulty = 0u; difficulty <= 2u; ++difficulty) {
        const auto drift = select(true, difficulty);
        check_common(drift);
        require(drift.use_drift_cgheight_scale, "drift selector flag was lost");
        require_close(drift.selected_cgheight_scale, 0.25, "drift scale mismatch");
        require_close(
            drift.body0_local_to_outer_vehicle_root[13],
            -0.018129356754356754,
            "drift bind Y mismatch");
    }

    const auto normal0 = select(false, 0u);
    const auto normal1 = select(false, 1u);
    const auto normal2 = select(false, 2u);
    check_common(normal0);
    check_common(normal1);
    check_common(normal2);
    require_close(normal0.selected_cgheight_scale, 0.6, "normal0 scale mismatch");
    require_close(normal1.selected_cgheight_scale, 0.6, "normal1 scale mismatch");
    require_close(normal2.selected_cgheight_scale, 0.75, "normal2 scale mismatch");
    require_close(
        normal0.body0_local_to_outer_vehicle_root[13],
        -0.004956085581085581,
        "normal0 bind Y mismatch");
    require_close(
        normal1.body0_local_to_outer_vehicle_root[13],
        -0.004956085581085581,
        "normal1 bind Y mismatch");
    require_close(
        normal2.body0_local_to_outer_vehicle_root[13],
        0.0006896020646020646,
        "normal2 bind Y mismatch");

    bool rejected_unbound = false;
    try {
        BmwRaceModeSelector selector{};
        (void)shift::runtime::physics::select_bmw_body0_outer_vehicle_root_bind(
            selector);
    } catch (const std::invalid_argument&) {
        rejected_unbound = true;
    }
    require(rejected_unbound, "unbound selector was accepted");

    bool rejected_difficulty3 = false;
    try {
        (void)select(false, 3u);
    } catch (const std::invalid_argument&) {
        rejected_difficulty3 = true;
    }
    require(rejected_difficulty3, "difficulty 3 was accepted");

    std::cout
        << "{\"format\":\"SHIFT.NativeBMWOffset33bSelector/1\","
        << "\"phase\":714,"
        << "\"silverstone_selector_ready\":true,"
        << "\"selector_source_backed\":true,"
        << "\"BMW_numeric_offset33b_ready\":true,"
        << "\"BODY0_to_outer_vehicle_root_numeric_matrix_ready\":true,"
        << "\"outer_vehicle_root_to_VHF_vehicle_root_ready\":false,"
        << "\"vehicle_world_transform_ready\":false}"
        << std::endl;
    return 0;
}
