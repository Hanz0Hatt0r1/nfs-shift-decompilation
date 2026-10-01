#pragma once

#include <array>
#include <cstddef>
#include <string>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativePostSolveProjectionFormat =
    "SHIFT.NativePostSolveBodyProjection/1";
inline constexpr const char* kNativePostSolveProjectionPacketFormat =
    "SHIFT.NativePostSolveBodyProjectionPacket/1";
inline constexpr const char* kPostSolveSourceFunction = "FUN_007b4110";

struct BodyAccumulatorState {
    std::array<double, 3> angular{};
    std::array<double, 3> linear{};
};

struct JointProjectionRow {
    std::size_t positive_body = 0;
    std::size_t negative_body = 0;
    std::size_t scalar_base = 0;
    std::array<double, 3> positive_lever_arm{};
    std::array<double, 3> negative_lever_arm{};
};

struct HingeProjectionRow {
    std::size_t positive_body = 0;
    std::size_t negative_body = 0;
    std::size_t scalar_base = 0;
    std::array<double, 3> positive_angular_row{};
    std::array<double, 3> positive_linear_row{};
    std::array<double, 3> negative_angular_row{};
    std::array<double, 3> negative_linear_row{};
};

struct BarProjectionRow {
    std::size_t positive_body = 0;
    std::size_t negative_body = 0;
    std::size_t scalar_base = 0;
    std::array<double, 3> positive_lever_arm{};
    std::array<double, 3> negative_lever_arm{};
    std::array<double, 3> direction{};
};

struct PreparedPostSolveBodyProjection {
    std::vector<BodyAccumulatorState> bodies;
    std::vector<double> solver_vector;
    std::vector<JointProjectionRow> joints;
    std::vector<HingeProjectionRow> hinges;
    std::vector<BarProjectionRow> bars;
    std::vector<BodyAccumulatorState> expected_bodies;
};

struct PostSolveBodyProjectionResult {
    std::vector<BodyAccumulatorState> bodies;
    double max_absolute_error = 0.0;
};

PreparedPostSolveBodyProjection load_prepared_post_solve_body_projection(
    const std::string& path);

PostSolveBodyProjectionResult execute_prepared_post_solve_body_projection(
    const PreparedPostSolveBodyProjection& projection,
    double tolerance = 1e-10);

}  // namespace shift::runtime::physics
