#pragma once

#include <array>

namespace shift::runtime::physics {

inline constexpr const char* kNativeSurfaceProbeFormat =
    "SHIFT.NativeSurfaceProbe/1";
inline constexpr const char* kSurfaceProbeFunction = "FUN_00759210";
inline constexpr const char* kHorizontalPerpendicularFunction = "FUN_007ade70";
inline constexpr unsigned int kHorizontalPerpendicularThresholdBits = 0x3C23D70Au;

using SurfaceProbeVector3d = std::array<double, 3>;

struct SurfaceProbeNode {
    SurfaceProbeVector3d point{};
    SurfaceProbeVector3d normal{};
    double distance = 0.0;
    double radius = 0.0;
    const SurfaceProbeNode* parent = nullptr;
    const SurfaceProbeNode* child = nullptr;
};

struct HorizontalPerpendicularResult {
    SurfaceProbeVector3d cross{};
    double length = 0.0;
    bool normalized = false;
    SurfaceProbeVector3d direction{};
};

struct SurfaceProbeResult {
    SurfaceProbeVector3d point{};
    double scalar = 0.0;
    bool used_parent = false;
};

HorizontalPerpendicularResult execute_fun_007ade70_horizontal_perpendicular(
    const SurfaceProbeVector3d& source_direction);

SurfaceProbeResult execute_fun_00759210_surface_probe(
    const SurfaceProbeVector3d& point,
    const SurfaceProbeNode& node);

}  // namespace shift::runtime::physics
