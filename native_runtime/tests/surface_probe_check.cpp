#include "shift_surface_probe.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {

void require_close(
    double actual,
    double expected,
    double tolerance,
    const char* label,
    double& max_error) {

    const double error = std::abs(actual - expected);
    max_error = std::max(max_error, error);
    if (!std::isfinite(actual) || error > tolerance) {
        throw std::runtime_error(label);
    }
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        double max_error = 0.0;

        const auto horizontal =
            execute_fun_007ade70_horizontal_perpendicular(
                {3.0, 17.0, 4.0});
        if (!horizontal.normalized) {
            throw std::runtime_error("FUN_007ade70 normalized branch not taken");
        }
        require_close(horizontal.cross[0], 4.0, 0.0, "FUN_007ade70 cross X", max_error);
        require_close(horizontal.cross[1], 0.0, 0.0, "FUN_007ade70 cross Y", max_error);
        require_close(horizontal.cross[2], -3.0, 0.0, "FUN_007ade70 cross Z", max_error);
        require_close(horizontal.length, 5.0, 0.0, "FUN_007ade70 length", max_error);
        require_close(horizontal.direction[0], 0.8, 1e-6, "FUN_007ade70 direction X", max_error);
        require_close(horizontal.direction[1], 0.0, 0.0, "FUN_007ade70 direction Y", max_error);
        require_close(horizontal.direction[2], -0.6, 1e-6, "FUN_007ade70 direction Z", max_error);

        const auto below =
            execute_fun_007ade70_horizontal_perpendicular(
                {0.005, 0.0, 0.0});
        const auto above =
            execute_fun_007ade70_horizontal_perpendicular(
                {0.02, 0.0, 0.0});
        if (below.normalized || !above.normalized) {
            throw std::runtime_error("FUN_007ade70 threshold branch mismatch");
        }
        require_close(below.direction[0], 1.0, 0.0, "FUN_007ade70 fallback X", max_error);
        require_close(above.direction[2], -1.0, 0.0, "FUN_007ade70 normalized threshold Z", max_error);

        const SurfaceProbeNode candidate_node = {
            {0.0, 0.0, 0.0},
            {0.0, 1.0, 0.0},
            1.0,
            -2.0,
            nullptr,
            nullptr,
        };
        const auto candidate =
            execute_fun_00759210_surface_probe(
                {3.0, 1.0, 4.0},
                candidate_node);
        require_close(candidate.point[0], -2.0, 0.0, "FUN_00759210 candidate X", max_error);
        require_close(candidate.point[1], 0.0, 0.0, "FUN_00759210 candidate Y", max_error);
        require_close(candidate.point[2], 0.0, 0.0, "FUN_00759210 candidate Z", max_error);
        require_close(candidate.scalar, 2.0, 0.0, "FUN_00759210 candidate scalar", max_error);
        if (candidate.used_parent) {
            throw std::runtime_error("FUN_00759210 candidate unexpectedly used parent");
        }

        const SurfaceProbeNode parent = {
            {0.0, -1.0, 0.0},
            {0.0, 1.0, 0.0},
            1.0,
            2.0,
            nullptr,
            nullptr,
        };
        const SurfaceProbeNode recursive_child = {
            {0.0, 1.0, 0.0},
            {0.0, 1.0, 0.0},
            1.0,
            1.0,
            &parent,
            nullptr,
        };
        const auto recursed =
            execute_fun_00759210_surface_probe(
                {0.0, 0.0, 0.0},
                recursive_child);
        if (!recursed.used_parent) {
            throw std::runtime_error("FUN_00759210 parent recursion not reported");
        }
        require_close(recursed.scalar, 2.0, 0.0, "FUN_00759210 parent scalar", max_error);

        const SurfaceProbeNode blend_child = {
            {4.0, 0.0, 0.0},
            {0.0, 1.0, 0.0},
            1.0,
            2.0,
            nullptr,
            nullptr,
        };
        const SurfaceProbeNode blend_node = {
            {0.0, 0.0, 0.0},
            {0.0, 1.0, 0.0},
            1.0,
            2.0,
            nullptr,
            &blend_child,
        };
        const auto blended =
            execute_fun_00759210_surface_probe(
                {0.0, 1.0, 0.0},
                blend_node);
        require_close(blended.point[0], 6.0, 0.0, "FUN_00759210 blended X", max_error);
        require_close(blended.point[1], 0.0, 0.0, "FUN_00759210 blended Y", max_error);
        require_close(blended.point[2], 0.0, 0.0, "FUN_00759210 blended Z", max_error);
        require_close(blended.scalar, 2.0, 0.0, "FUN_00759210 blended scalar", max_error);

        bool zero_path_rejected = false;
        try {
            const SurfaceProbeNode bad = {
                {0.0, 0.0, 0.0},
                {0.0, 1.0, 0.0},
                0.0,
                1.0,
                nullptr,
                nullptr,
            };
            (void)execute_fun_00759210_surface_probe(
                {1.0, 1.0, 0.0},
                bad);
        } catch (const std::invalid_argument&) {
            zero_path_rejected = true;
        }
        if (!zero_path_rejected) {
            throw std::runtime_error("FUN_00759210 accepted zero distance path");
        }

        bool non_finite_rejected = false;
        try {
            auto bad = candidate_node;
            bad.normal[0] = std::numeric_limits<double>::infinity();
            (void)execute_fun_00759210_surface_probe(
                {1.0, 1.0, 1.0},
                bad);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error("FUN_00759210 accepted non-finite node state");
        }

        std::cout
            << "{\"format\":\"SHIFT.NativeSurfaceProbe/1\","
            << "\"ready\":true,"
            << "\"probe_function\":\"FUN_00759210\","
            << "\"direction_function\":\"FUN_007ade70\","
            << "\"direction_threshold_bits\":1008981770,"
            << "\"parent_recursion_proven\":true,"
            << "\"same_sign_child_blend_proven\":true,"
            << "\"zero_path_rejected\":true,"
            << "\"non_finite_rejected\":true,"
            << "\"max_absolute_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << "\n";
        return 1;
    }
}
