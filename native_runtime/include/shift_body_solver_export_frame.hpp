#pragma once

#include <cstddef>
#include <string>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeBodySolverExportFrameFormat =
    "SHIFT.NativeBodySolverExportFrame/1";
inline constexpr const char* kNativeBodySolverExportFramePacketFormat =
    "SHIFT.NativeBodySolverExportFramePacket/1";

struct PreparedBodySolverContribution {
    std::size_t body_index = 0;
    std::vector<double> solver_vector;
    std::vector<double> solver_matrix;
};

struct PreparedBodySolverExportFrame {
    std::size_t scalar_count = 0;
    std::size_t matrix_double_count = 0;
    std::vector<PreparedBodySolverContribution> bodies;
    std::vector<double> expected_solver_vector;
    std::vector<double> expected_solver_matrix;
};

struct PreparedBodySolverExportFrameResult {
    std::vector<double> solver_vector;
    std::vector<double> solver_matrix;
    std::size_t body_count = 0;
    double max_absolute_error = 0.0;
};

PreparedBodySolverExportFrame load_prepared_body_solver_export_frame(
    const std::string& path);

PreparedBodySolverExportFrameResult execute_prepared_body_solver_export_frame(
    const PreparedBodySolverExportFrame& frame,
    double tolerance = 1e-12);

}  // namespace shift::runtime::physics
