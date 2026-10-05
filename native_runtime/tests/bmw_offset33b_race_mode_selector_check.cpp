#include "shift_bmw_offset33b_race_mode_selector.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

using namespace shift::runtime::physics;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void require_close(double actual, double expected, const char* label) {
    if (std::fabs(actual - expected) > 1.0e-12) {
        throw std::runtime_error(
            std::string(label) + " mismatch: " +
            std::to_string(actual) + " vs " + std::to_string(expected));
    }
}

void require_matrix_translation(
    const BmwBody0OuterVehicleBindSelection& selected,
    double x,
    double y,
    double z) {
    const auto& matrix = selected.body0_local_to_outer_vehicle_root;
    require_close(matrix[0], 1.0, "m00");
    require_close(matrix[5], 1.0, "m11");
    require_close(matrix[10], 1.0, "m22");
    require_close(matrix[15], 1.0, "m33");
    require_close(matrix[1], 0.0, "m01");
    require_close(matrix[4], 0.0, "m10");
    require_close(matrix[3], 0.0, "m03");
    require_close(matrix[7], 0.0, "m13");
    require_close(matrix[11], 0.0, "m23");
    require_close(matrix[12], x, "tx");
    require_close(matrix[13], y, "ty");
    require_close(matrix[14], z, "tz");
}

BmwBody0OuterVehicleBindSelection select(
    bool drift,
    std::uint32_t difficulty) {
    return select_bmw_body0_outer_vehicle_bind(
        BmwOffset33bRaceModeSelector{true, drift, difficulty});
}

}  // namespace

int main() {
    try {
        const auto normal0 = select(false, 0u);
        const auto normal1 = select(false, 1u);
        const auto normal2 = select(false, 2u);
        const auto drift0 = select(true, 0u);
        const auto drift1 = select(true, 1u);
        const auto drift2 = select(true, 2u);

        require_close(normal0.cgheight_scale, 0.6, "normal0 scale");
        require_close(normal1.cgheight_scale, 0.6, "normal1 scale");
        require_close(normal2.cgheight_scale, 0.75, "normal2 scale");
        require_close(drift0.cgheight_scale, 0.25, "drift0 scale");
        require_close(drift1.cgheight_scale, 0.25, "drift1 scale");
        require_close(drift2.cgheight_scale, 0.25, "drift2 scale");

        require_close(normal1.target_cg[0], 0.0, "normal1 target x");
        require_close(normal1.target_cg[1], 0.168, "normal1 target y");
        require_close(normal1.target_cg[2], -0.081, "normal1 target z");
        require_close(normal2.target_cg[1], 0.210, "normal2 target y");
        require_close(drift2.target_cg[1], 0.070, "drift2 target y");

        constexpr double kZ = -0.011470862470862470862470862470862471;
        require_matrix_translation(
            normal0,
            0.0,
            -0.004956085581085581085581085581085581,
            kZ);
        require_matrix_translation(
            normal1,
            0.0,
            -0.004956085581085581085581085581085581,
            kZ);
        require_matrix_translation(
            normal2,
            0.0,
            0.000689602064602064602064602064602065,
            kZ);
        require_matrix_translation(
            drift0,
            0.0,
            -0.018129356754356754356754356754356754,
            kZ);
        require_matrix_translation(
            drift1,
            0.0,
            -0.018129356754356754356754356754356754,
            kZ);
        require_matrix_translation(
            drift2,
            0.0,
            -0.018129356754356754356754356754356754,
            kZ);

        require(
            normal0.body0_to_outer_vehicle_translation ==
                normal1.body0_to_outer_vehicle_translation,
            "normal difficulty 0/1 must select the same proven bind");
        require(
            drift0.body0_to_outer_vehicle_translation ==
                drift1.body0_to_outer_vehicle_translation &&
            drift1.body0_to_outer_vehicle_translation ==
                drift2.body0_to_outer_vehicle_translation,
            "all admitted drift difficulties must select the same proven bind");
        require(
            normal2.body0_to_outer_vehicle_translation !=
                normal1.body0_to_outer_vehicle_translation,
            "normal difficulty 2 must retain its distinct proven bind");

        bool unready_rejected = false;
        try {
            (void)select_bmw_body0_outer_vehicle_bind(
                BmwOffset33bRaceModeSelector{false, false, 1u});
        } catch (const std::invalid_argument&) {
            unready_rejected = true;
        }
        require(unready_rejected,
                "unbound race-mode selector was accepted");

        bool difficulty3_rejected = false;
        try {
            (void)select_bmw_body0_outer_vehicle_bind(
                BmwOffset33bRaceModeSelector{true, false, 3u});
        } catch (const std::out_of_range&) {
            difficulty3_rejected = true;
        }
        require(difficulty3_rejected,
                "PhysicsTweaker array lane 3 was admitted as Player Difficulty");

        std::cout
            << "{\"format\":\""
            << kNativeBmwOffset33bRaceModeSelectorFormat << "\","
            << "\"source_contract\":\"SHIFT.BMWOffset33bSelectorCompleteNumeric/1\","
            << "\"player_difficulty_domain\":[0,1,2],"
            << "\"selector_combinations\":6,"
            << "\"unique_translations\":3,"
            << "\"selector_required\":true,"
            << "\"difficulty_3_rejected\":true,"
            << "\"body0_to_outer_vehicle_ready_when_selector_bound\":true,"
            << "\"outer_vehicle_to_vhf_ready\":false,"
            << "\"vehicle_world_transform_ready\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << "bmw_offset33b_race_mode_selector_check: "
                  << exc.what() << '\n';
        return 1;
    }
}
