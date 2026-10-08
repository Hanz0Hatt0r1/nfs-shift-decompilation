#pragma once

#include "shift_constraint_sample_refresh.hpp"

#include <array>
#include <cmath>
#include <cstddef>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00766510SharedReferenceVectorFormat =
    "SHIFT.Fun00766510SharedReferenceVector/1";
inline constexpr std::size_t kFun00766510VehicleOwnerRecordOffset = 0x3fe8u;
inline constexpr std::array<std::size_t, 3>
    kFun00766510ParticipantReferenceSourceOffsets = {
        0x16b4u,
        0x16b8u,
        0x16bcu,
    };

using Fun00766510ParticipantReferenceSource3f = std::array<float, 3>;
using Fun00766510ReferenceVector3d = std::array<double, 3>;

struct Fun00766510SharedReferenceVectorResult {
    Fun00766510ReferenceVector3d widened_participant_source{};
    Fun00766510ReferenceVector3d transformed_reference{};
};

inline Fun00766510SharedReferenceVectorResult
execute_fun_00766510_shared_reference_vector(
    const ConstraintRefreshFrame3f& body_frame,
    const Fun00766510ParticipantReferenceSource3f& participant_source) {

    Fun00766510SharedReferenceVectorResult result{};
    for (std::size_t axis = 0u; axis < participant_source.size(); ++axis) {
        if (!std::isfinite(participant_source[axis])) {
            throw std::invalid_argument(
                "FUN_00766510 participant +0x16b4 reference source contains non-finite f32");
        }
        // PC retail loads each source lane as f32 and then widens each lane to
        // f64 before calling FUN_007af0a0. Preserve that explicit boundary.
        result.widened_participant_source[axis] =
            static_cast<double>(participant_source[axis]);
    }
    result.transformed_reference = transform_fun_007af0a0_refresh(
        body_frame,
        result.widened_participant_source);
    return result;
}

}  // namespace shift::runtime::physics
