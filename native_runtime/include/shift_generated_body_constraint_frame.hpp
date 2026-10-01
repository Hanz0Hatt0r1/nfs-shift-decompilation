#pragma once

#include "shift_builtin_solver_frame.hpp"
#include "shift_generated_body_solver_export.hpp"

#include <cstddef>
#include <string>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeGeneratedBodyConstraintFrameFormat =
    "SHIFT.NativeGeneratedBodyConstraintFrame/1";
inline constexpr const char*
    kNativeGeneratedBodyConstraintFramePacketFormat =
        "SHIFT.NativeGeneratedBodyConstraintFramePacket/1";

struct PreparedGeneratedBodyConstraintFrame {
    std::size_t scalar_count = 0;
    std::size_t matrix_double_count = 0;
    std::vector<GeneratedBodySolverExportInput> bodies;
};

struct GeneratedBodyConstraintFrameResult {
    std::vector<double> solver_vector;
    std::vector<double> solver_matrix;
    std::size_t body_count = 0;
    std::size_t joint_sample_count = 0;
    std::size_t hinge_sample_count = 0;
    std::size_t bar_sample_count = 0;
};

struct GeneratedBodySolverFrameJoinResult {
    std::size_t scalar_count = 0;
    std::size_t matrix_double_count = 0;
    std::size_t body_count = 0;
    std::size_t joint_sample_count = 0;
    std::size_t hinge_sample_count = 0;
    std::size_t bar_sample_count = 0;
    double max_rhs_join_error = 0.0;
    double max_matrix_join_error = 0.0;
};

PreparedGeneratedBodyConstraintFrame
load_prepared_generated_body_constraint_frame(
    const std::string& path);

GeneratedBodyConstraintFrameResult
execute_prepared_generated_body_constraint_frame(
    const PreparedGeneratedBodyConstraintFrame& frame);

GeneratedBodySolverFrameJoinResult
verify_generated_body_constraint_frame_matches_builtin_solver_frame(
    const PreparedGeneratedBodyConstraintFrame& generated_frame,
    const PreparedBuiltinSolverFrame& solver_frame,
    double tolerance = 1e-12);

}  // namespace shift::runtime::physics
