#include "shift_fun_00766510_shared_reference_vector.hpp"

#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {

using namespace shift::runtime::physics;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void require_near(double actual, double expected, const char* message) {
    if (std::abs(actual - expected) > 1e-12) {
        throw std::runtime_error(message);
    }
}

}  // namespace

int main() {
    try {
        require(kFun00766510VehicleOwnerRecordOffset == 0x3fe8u,
                "FUN_00766510 owner-record offset drift");
        require(kFun00766510ParticipantReferenceSourceOffsets ==
                    std::array<std::size_t, 3>{0x16b4u, 0x16b8u, 0x16bcu},
                "FUN_00766510 participant source offsets drift");

        ConstraintRefreshFrame3f frame = {
            1.0f, 2.0f, 3.0f,
            4.0f, 5.0f, 6.0f,
            7.0f, 8.0f, 9.0f,
        };
        const Fun00766510ParticipantReferenceSource3f source = {
            1.25f, -0.5f, 2.0f};
        const auto result = execute_fun_00766510_shared_reference_vector(
            frame,
            source);

        require_near(result.widened_participant_source[0], 1.25,
                     "participant source X widening drift");
        require_near(result.widened_participant_source[1], -0.5,
                     "participant source Y widening drift");
        require_near(result.widened_participant_source[2], 2.0,
                     "participant source Z widening drift");
        require_near(result.transformed_reference[0], 13.25,
                     "shared reference X transform drift");
        require_near(result.transformed_reference[1], 16.0,
                     "shared reference Y transform drift");
        require_near(result.transformed_reference[2], 18.75,
                     "shared reference Z transform drift");

        bool nonfinite_rejected = false;
        try {
            auto invalid = source;
            invalid[2] = std::numeric_limits<float>::infinity();
            (void)execute_fun_00766510_shared_reference_vector(frame, invalid);
        } catch (const std::invalid_argument&) {
            nonfinite_rejected = true;
        }
        require(nonfinite_rejected,
                "FUN_00766510 shared reference accepted non-finite source");

        std::cout
            << "{\"format\":\"" << kFun00766510SharedReferenceVectorFormat << "\","
            << "\"ready\":true,"
            << "\"owner_record_offset\":\"0x3fe8\","
            << "\"participant_source_offsets\":[\"0x16b4\",\"0x16b8\",\"0x16bc\"],"
            << "\"explicit_f32_to_f64_widening\":true,"
            << "\"body_transform_native\":true,"
            << "\"contact_response_provider_removed\":false,"
            << "\"external_provider_count\":7}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
