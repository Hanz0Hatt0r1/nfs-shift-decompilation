#include "shift_contact_outer_kernel.hpp"

#include <cmath>
#include <iostream>
#include <limits>
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

Fun00759c90RecordSet make_records() {
    WheelForceAggregateRecord record{};
    record.scalar_at_base = 2.0;
    record.vector_a = {1.0, 0.0, 2.0};
    record.scalar_at_minus_8 = 1.0;
    record.vector_b = {1.0, 0.0, -1.0};
    record.point = {0.0, 0.0, 0.0};
    return {record, record, record};
}

}  // namespace

int main() {
    try {
        const auto records = make_records();
        const auto total = execute_fun_00759c90_weighted_total(records);
        require_near(total[0], 9.0, 0.0,
                     "FUN_00759c90 weighted total X mismatch");
        require_near(total[1], 0.0, 0.0,
                     "FUN_00759c90 weighted total Y mismatch");
        require_near(total[2], 9.0, 0.0,
                     "FUN_00759c90 weighted total Z mismatch");

        const double projected = execute_fun_007675f0_projected_scalar(
            records,
            ContactOuterVector3d{3.0, 0.0, 4.0});
        require_near(projected, 12.6, 1e-5,
                     "FUN_007675f0 projected scalar mismatch");

        ContactOuterKernelInput production{};
        production.planar_delta = {3.0, 0.0, 4.0};
        production.previous_distance_state = 5.0;
        production.distance_filter_cap = 1.0;
        production.speed_x = 0.0;
        production.speed_z = 20.0;
        production.surface_scalar = 4.0;
        production.param_3 = 0.5;
        production.body_field_120 = 2.0;
        production.fun_00759c90_records = records;
        production.derive_projected_scalar = true;
        production.derive_body_owned_scalars = true;
        const auto native = execute_fun_007675f0_outer_arithmetic(production);
        require(native.projected_scalar_derived,
                "production kernel did not derive projected scalar");
        require_near(native.projected_scalar, projected, 0.0,
                     "production projected scalar drift");

        ContactOuterKernelInput compatibility = production;
        compatibility.derive_projected_scalar = false;
        compatibility.derive_body_owned_scalars = false;
        compatibility.projected_scalar = 7.0;
        compatibility.base_scalar = 4.0;
        compatibility.alignment_scalar = 0.25;
        const auto legacy = execute_fun_007675f0_outer_arithmetic(compatibility);
        require(!legacy.projected_scalar_derived,
                "compatibility projected scalar was overwritten");
        require_near(legacy.projected_scalar, 7.0, 0.0,
                     "compatibility projected scalar drift");

        bool non_finite_rejected = false;
        try {
            auto bad = records;
            bad[0].scalar_at_base = std::numeric_limits<double>::infinity();
            (void)execute_fun_007675f0_projected_scalar(
                bad,
                ContactOuterVector3d{3.0, 0.0, 4.0});
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        require(non_finite_rejected,
                "projected-scalar path accepted non-finite FUN_00759c90 record state");

        std::cout
            << "{\"format\":\"" << kFun007675f0ProjectedScalarOwnershipFormat << "\","
            << "\"ready\":true,"
            << "\"aggregate\":\"FUN_00759c90\","
            << "\"record_count\":3,"
            << "\"weighted_total\":[9,0,9],"
            << "\"projected_scalar_internal\":true,"
            << "\"production_record_boundary\":true,"
            << "\"top_level_provider_count_reduced\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
