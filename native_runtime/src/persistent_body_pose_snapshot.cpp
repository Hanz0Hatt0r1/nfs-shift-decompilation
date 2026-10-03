#include "shift_persistent_body_pose_snapshot.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <stdexcept>

namespace shift::runtime::physics {
namespace {

void require_finite_snapshot(const PersistentBodyPoseSnapshot& snapshot) {
    for (double value : snapshot.origin) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                "persistent BODY pose origin contains non-finite value");
        }
    }
    for (float value : snapshot.basis) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                "persistent BODY pose basis contains non-finite value");
        }
    }
}

}  // namespace

std::vector<PersistentBodyPoseSnapshot> decode_persistent_body_pose_snapshots(
    const std::vector<std::uint8_t>& body_bytes,
    std::uint32_t body_count) {
    if (body_count == 0u) {
        throw std::invalid_argument(
            "persistent BODY pose snapshot requires non-zero BODY count");
    }
    if (body_count >
        std::numeric_limits<std::size_t>::max() / kBodyRecordSize) {
        throw std::invalid_argument(
            "persistent BODY pose snapshot BODY cardinality overflows size_t");
    }

    const std::size_t expected_bytes =
        static_cast<std::size_t>(body_count) * kBodyRecordSize;
    if (body_bytes.size() != expected_bytes) {
        throw std::invalid_argument(
            "persistent BODY pose snapshot byte cardinality mismatch");
    }

    std::vector<PersistentBodyPoseSnapshot> snapshots;
    snapshots.reserve(body_count);
    for (std::size_t body_index = 0u;
         body_index < static_cast<std::size_t>(body_count);
         ++body_index) {
        const std::size_t base = body_index * kBodyRecordSize;
        BodyRecordBytes record{};
        std::copy_n(
            body_bytes.begin() + static_cast<std::ptrdiff_t>(base),
            kBodyRecordSize,
            record.begin());
        const auto state = decode_fun_007bab70_body_record(record);

        PersistentBodyPoseSnapshot snapshot{};
        snapshot.body_index = body_index;
        snapshot.origin = state.origin;
        snapshot.basis = state.basis;
        require_finite_snapshot(snapshot);
        snapshots.push_back(snapshot);
    }
    return snapshots;
}

}  // namespace shift::runtime::physics
