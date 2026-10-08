#pragma once

#include "shift_post_solve_projection.hpp"

#include <array>

namespace shift::runtime::physics {

inline constexpr const char* kNativeBodyAccumulatorPrimitivesFormat =
    "SHIFT.NativeBodyAccumulatorPrimitives/1";
inline constexpr const char* kBodyPointAccumulatorSourceFunction =
    "FUN_007ba9e0";
inline constexpr const char* kBodyPositiveAccumulatorSourceFunction =
    "FUN_007baa70";
inline constexpr const char* kBodyNegativeAccumulatorSourceFunction =
    "FUN_007baaf0";
inline constexpr const char* kBodyCrossProductSourceFunction =
    "FUN_00753650";

using BodyAccumulatorVector3d = std::array<double, 3>;

BodyAccumulatorVector3d execute_fun_00753650_cross_product(
    const BodyAccumulatorVector3d& left,
    const BodyAccumulatorVector3d& right);

void apply_fun_007baa70_body_accumulator(
    BodyAccumulatorState& body,
    const BodyAccumulatorVector3d& point_or_lever_arm,
    const BodyAccumulatorVector3d& contribution);

void apply_fun_007baaf0_body_accumulator(
    BodyAccumulatorState& body,
    const BodyAccumulatorVector3d& point_or_lever_arm,
    const BodyAccumulatorVector3d& contribution);

void apply_fun_007ba9e0_point_accumulator(
    BodyAccumulatorState& body,
    const BodyAccumulatorVector3d& world_point,
    const BodyAccumulatorVector3d& body_origin,
    const BodyAccumulatorVector3d& contribution);

}  // namespace shift::runtime::physics
