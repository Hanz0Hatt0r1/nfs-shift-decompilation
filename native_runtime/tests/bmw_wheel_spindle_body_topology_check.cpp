#include "shift_bmw_wheel_spindle_body_topology.hpp"

#include <array>
#include <cstddef>
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

}  // namespace

int main() {
    try {
        const auto& topology = bmw_m3_e36_retail_wheel_spindle_body_topology();
        const std::array<std::size_t, 4> expected_wheels{{3u, 4u, 7u, 8u}};
        const std::array<std::size_t, 4> expected_spindles{{1u, 2u, 5u, 6u}};

        require(topology.body_count == 11u,
                "Phase 702 BMW retail BODY count mismatch");
        require(topology.wheel_body_indices == expected_wheels,
                "Phase 702 BMW wheel BODY indices mismatch");
        require(topology.spindle_body_indices == expected_spindles,
                "Phase 702 BMW spindle BODY indices mismatch");
        require(topology.wheel_spindle_body_indices_ready,
                "Phase 702 lost proven wheel/spindle readiness");
        require(!topology.rear_axle_body_index_ready,
                "Phase 702 invented a retail rear-axle BODY index");
        require(topology.main_chassis_body_selected &&
                topology.main_chassis_body_index == 0u,
                "Phase 702 lost Process 1 proven main chassis BODY 0");
        require(!topology.update_child_to_vehicle_solver_base_continuity_proven &&
                !topology.vehicle_body_selection_ready,
                "Phase 702 bypassed the remaining update-child continuity gate");

        bool unresolved_rejected = false;
        try {
            (void)complete_bmw_vehicle_constraint_body_identity_map(
                topology,
                ProvenRearAxleBodyIndex{false, 0u});
        } catch (const std::invalid_argument& exc) {
            unresolved_rejected =
                std::string(exc.what()).find("proven rear-axle BODY index") !=
                std::string::npos;
        }
        require(unresolved_rejected,
                "Phase 702 full relation map failed open without rear-axle proof");

        bool range_rejected = false;
        try {
            (void)complete_bmw_vehicle_constraint_body_identity_map(
                topology,
                ProvenRearAxleBodyIndex{true, 11u});
        } catch (const std::out_of_range&) {
            range_rejected = true;
        }
        require(range_rejected,
                "Phase 702 accepted rear-axle index outside retail BODY domain");

        // Synthetic positive rear-axle proof exercises only the completion
        // transport. BODY 9 is not promoted as the retail rear_axle identity.
        const auto synthetic = complete_bmw_vehicle_constraint_body_identity_map(
            topology,
            ProvenRearAxleBodyIndex{true, 9u});
        require(synthetic.wheel_body_indices == expected_wheels &&
                synthetic.spindle_body_indices == expected_spindles &&
                synthetic.rear_axle_body_index == 9u,
                "Phase 702 synthetic completion changed proven named indices");

        std::cout
            << "{\"format\":\""
            << kNativeBmwWheelSpindleBodyTopologyFormat << "\","
            << "\"ready\":true,"
            << "\"retail_sdf_body_count\":11,"
            << "\"wheel_body_indices\":[3,4,7,8],"
            << "\"spindle_body_indices\":[1,2,5,6],"
            << "\"wheel_spindle_body_indices_ready\":true,"
            << "\"rear_axle_body_index_ready\":false,"
            << "\"main_chassis_body_selected\":true,"
            << "\"main_chassis_body_index\":0,"
            << "\"update_child_to_vehicle_solver_base_continuity_proven\":false,"
            << "\"vehicle_body_selection_ready\":false,"
            << "\"full_vehicle_constraint_body_map_ready\":false,"
            << "\"synthetic_completion_only\":true,"
            << "\"distinct_body_indices_assumed\":false,"
            << "\"phase698_positive_selection_admissible\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
