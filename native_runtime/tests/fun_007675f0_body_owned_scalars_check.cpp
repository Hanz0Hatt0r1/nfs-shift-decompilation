#include "shift_contact_outer_kernel.hpp"
#include "shift_fun_007675f0_body_owned_scalars.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>

namespace {

using namespace shift::runtime::physics;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void require_near(double actual, double expected, double tolerance, const char* message) {
    if (!std::isfinite(actual) || std::abs(actual - expected) > tolerance) {
        throw std::runtime_error(message);
    }
}

}  // namespace

int main() {
    try {
        const auto positive = execute_fun_007675f0_body_owned_scalars(
            ContactOuterVector3d{3.0, 0.0, 4.0},
            Fun007675f0BodyMotion{10.0, 0.0},
            10.0,
            2.0);
        require_near(positive.planar_direction[0], 0.6, 1e-6,
                     "planar direction X mismatch");
        require_near(positive.planar_direction[2], 0.8, 1e-6,
                     "planar direction Z mismatch");
        require_near(positive.normalized_planar_motion[0], 1.0, 0.0,
                     "normalized BODY0 X mismatch");
        require_near(positive.normalized_planar_motion[2], 0.0, 0.0,
                     "normalized BODY0 Z mismatch");
        require_near(positive.aligned_perpendicular[0], 0.0, 1e-7,
                     "aligned perpendicular X mismatch");
        require_near(positive.aligned_perpendicular[2], 1.0, 1e-7,
                     "aligned perpendicular Z mismatch");
        require_near(positive.alignment_scalar, 0.8, 1e-6,
                     "alignment scalar mismatch");
        require_near(positive.perpendicular_motion, 8.0, 1e-6,
                     "perpendicular BODY0 motion mismatch");
        require_near(positive.base_scalar, 12.8, 1e-5,
                     "body-owned base scalar mismatch");

        // The source flips the normalized perpendicular when its dot with the
        // probe-derived planar direction is negative. The final alignment is
        // therefore positive for this mirrored witness while the transverse
        // projection changes sign before its square.
        const auto mirrored = execute_fun_007675f0_body_owned_scalars(
            ContactOuterVector3d{3.0, 0.0, -4.0},
            Fun007675f0BodyMotion{10.0, 0.0},
            10.0,
            2.0);
        require_near(mirrored.aligned_perpendicular[2], -1.0, 1e-7,
                     "source sign flip was not reproduced");
        require_near(mirrored.alignment_scalar, 0.8, 1e-6,
                     "mirrored alignment scalar mismatch");
        require_near(mirrored.perpendicular_motion, -8.0, 1e-6,
                     "mirrored transverse projection mismatch");
        require_near(mirrored.base_scalar, 12.8, 1e-5,
                     "mirrored base scalar square mismatch");

        ContactOuterKernelInput production{};
        production.planar_delta = {6.0, 0.0, 8.0};
        production.previous_distance_state = 8.0;
        production.distance_filter_cap = 1.0;
        production.speed_x = 20.0;
        production.speed_z = 0.0;
        production.surface_scalar = 10.0;
        production.projected_scalar = 1.0;
        production.param_3 = 0.5;
        production.body_field_120 = 2.0;
        production.derive_body_owned_scalars = true;
        const auto native = execute_fun_007675f0_outer_arithmetic(production);
        require(native.gate_open,
                "production witness did not enter the recovered outer gate");
        require(native.body_owned_scalars_derived,
                "production kernel did not derive body-owned scalars");
        const auto expected = execute_fun_007675f0_body_owned_scalars(
            production.planar_delta,
            Fun007675f0BodyMotion{production.speed_x, production.speed_z},
            native.filtered_distance_state,
            production.body_field_120);
        require_near(native.base_scalar, expected.base_scalar, 0.0,
                     "kernel base scalar diverged from source-backed derivation");
        require_near(native.alignment_scalar, expected.alignment_scalar, 0.0,
                     "kernel alignment scalar diverged from source-backed derivation");
        require_near(native.projected_scalar, 1.0, 0.0,
                     "still-external projected scalar changed during derivation");

        ContactOuterKernelInput closed = production;
        closed.speed_x = 0.5;
        const auto closed_result = execute_fun_007675f0_outer_arithmetic(closed);
        require(!closed_result.gate_open && !closed_result.body_owned_scalars_derived,
                "body-owned scalars were manufactured outside the source gate");

        ContactOuterKernelInput compatibility = production;
        compatibility.derive_body_owned_scalars = false;
        compatibility.base_scalar = 4.0;
        compatibility.alignment_scalar = 0.25;
        const auto compatibility_result =
            execute_fun_007675f0_outer_arithmetic(compatibility);
        require(!compatibility_result.body_owned_scalars_derived,
                "compatibility scalar inputs were overwritten");
        require_near(compatibility_result.base_scalar, 4.0, 0.0,
                     "compatibility base scalar drift");
        require_near(compatibility_result.alignment_scalar, 0.25, 0.0,
                     "compatibility alignment scalar drift");

        std::cout
            << "{\"format\":\"" << kFun007675f0BodyOwnedScalarsFormat << "\","
            << "\"ready\":true,"
            << "\"pc_function\":\"FUN_007675f0\","
            << "\"xbox_counterpart\":\"sub_825939F0\","
            << "\"body_offsets\":[\"+0x78\",\"+0x88\",\"+0x120\"],"
            << "\"persistent_distance_offset\":\"HDVehicle+0x4080\","
            << "\"sign_alignment_locked\":true,"
            << "\"base_scalar_internal\":true,"
            << "\"alignment_scalar_internal\":true,"
            << "\"projected_scalar_external\":true,"
            << "\"top_level_provider_count_reduced\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
