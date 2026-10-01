#pragma once

#include "shift_constraint_sample_refresh.hpp"
#include "shift_generated_body_constraint_frame.hpp"

#include <array>
#include <cstddef>
#include <string>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeConstraintSampleRelationFrameFormat =
    "SHIFT.NativeConstraintSampleRelationFrame/1";
inline constexpr const char*
    kNativeConstraintSampleRelationFramePacketFormat =
        "SHIFT.NativeConstraintSampleRelationFramePacket/1";

struct ConstraintSampleEndpointRef {
    std::size_t body_index = 0;
    std::size_t sample_index = 0;
};

struct PreparedJointConstraintRelation {
    ConstraintSampleEndpointRef positive{};
    ConstraintSampleEndpointRef negative{};
    ConstraintRefreshVector3d positive_local_position{};
    ConstraintRefreshVector3d negative_local_position{};
};

struct PreparedHingeConstraintRelation {
    ConstraintSampleEndpointRef positive{};
    ConstraintSampleEndpointRef negative{};
    ConstraintRefreshVector3d positive_angular_local{};
    ConstraintRefreshVector3d positive_linear_local{};
};

struct PreparedBarConstraintRelation {
    ConstraintSampleEndpointRef positive{};
    ConstraintSampleEndpointRef negative{};
    ConstraintRefreshVector3d positive_local_point{};
    ConstraintRefreshVector3d negative_local_point{};
};

struct PreparedConstraintSampleRelationFrame {
    std::size_t body_count = 0;
    std::vector<PreparedJointConstraintRelation> joints;
    std::vector<PreparedHingeConstraintRelation> hinges;
    std::vector<PreparedBarConstraintRelation> bars;
};

struct RefreshedGeneratedBodyConstraintFrame {
    PreparedGeneratedBodyConstraintFrame frame;
    std::size_t joint_relation_count = 0;
    std::size_t hinge_relation_count = 0;
    std::size_t bar_relation_count = 0;
    std::size_t refreshed_joint_sample_count = 0;
    std::size_t refreshed_hinge_sample_count = 0;
    std::size_t refreshed_bar_sample_count = 0;
};

PreparedConstraintSampleRelationFrame
load_prepared_constraint_sample_relation_frame(
    const std::string& path);

RefreshedGeneratedBodyConstraintFrame
refresh_generated_body_constraint_frame(
    const PreparedGeneratedBodyConstraintFrame& source,
    const PreparedConstraintSampleRelationFrame& relations);

}  // namespace shift::runtime::physics
