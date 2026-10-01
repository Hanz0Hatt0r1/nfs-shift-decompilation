#pragma once

#include "shift_body_constraint_assembly.hpp"
#include "shift_constraint_sample_refresh.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace shift::runtime::physics {

struct ConstraintRelationBodyInput {
    ConstraintRefreshFrame3f body_frame{};
    ConstraintRefreshVector3d body_position{};
};

struct JointConstraintRelationInput {
    std::size_t positive_body_index = 0;
    std::size_t negative_body_index = 0;
    ConstraintRefreshVector3d world_anchor{};
    std::size_t scalar_base = 0;
};

struct HingeConstraintRelationInput {
    std::size_t positive_body_index = 0;
    std::size_t negative_body_index = 0;
    ConstraintRefreshVector3d world_axis{};
    std::size_t scalar_base = 0;
};

struct BarConstraintRelationInput {
    std::size_t positive_body_index = 0;
    std::size_t negative_body_index = 0;
    ConstraintRefreshVector3d positive_world_anchor{};
    ConstraintRefreshVector3d negative_world_anchor{};
    std::size_t scalar_base = 0;
};

struct ConstraintRelationSampleOwnership {
    std::size_t relation_index = 0;
    std::size_t body_index = 0;
    std::size_t body_sample_ordinal = 0;
    std::size_t scalar_base = 0;
    std::uint8_t side_flag = 0;
};

struct ConstraintRelationFrameInput {
    std::size_t scalar_count = 0;
    std::vector<ConstraintRelationBodyInput> bodies;
    std::vector<JointConstraintRelationInput> joints;
    std::vector<HingeConstraintRelationInput> hinges;
    std::vector<BarConstraintRelationInput> bars;
};

struct ConstraintRelationFrameResult {
    ConstraintSampleRefreshFrameInput refresh_input{};
    ConstraintSampleRefreshFrameResult refreshed{};
    std::vector<std::vector<PreparedJointSample>> body_joints;
    std::vector<std::vector<PreparedHingeSample>> body_hinges;
    std::vector<std::vector<PreparedBarSample>> body_bars;
    std::vector<std::vector<ConstraintRelationSampleOwnership>> joint_ownership;
    std::vector<std::vector<ConstraintRelationSampleOwnership>> hinge_ownership;
    std::vector<std::vector<ConstraintRelationSampleOwnership>> bar_ownership;
    std::size_t body_sample_count = 0;
};

ConstraintRefreshVector3d inverse_transform_fun_007afcd0_relation(
    const ConstraintRefreshFrame3f& body_frame,
    const ConstraintRefreshVector3d& body_position,
    const ConstraintRefreshVector3d& world_value);

std::array<ConstraintRefreshVector3d, 3> build_fun_007b1230_relation_basis(
    const ConstraintRefreshVector3d& local_primary);

ConstraintRelationFrameResult build_fun_007b3820_constraint_relation_frame(
    const ConstraintRelationFrameInput& input);

}  // namespace shift::runtime::physics
