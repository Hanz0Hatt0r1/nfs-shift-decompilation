#include "shift_fun_007618f0_local_sample_producer.hpp"

#include <cmath>
#include <stdexcept>

namespace shift::runtime::physics {
namespace {

double retail_store_f64(long double value) {
    const double stored = static_cast<double>(value);
    if (!std::isfinite(stored)) {
        throw std::invalid_argument("FUN_007618f0 local-sample producer overflowed f64");
    }
    return stored;
}

void require_finite_vec(const CollisionQueryVector3d& value, const char* message) {
    for (double component : value) {
        if (!std::isfinite(component)) {
            throw std::invalid_argument(message);
        }
    }
}

double retail_add_f64(double lhs, double rhs) {
    return retail_store_f64(
        static_cast<long double>(lhs) + static_cast<long double>(rhs));
}

double retail_mul_f64(double lhs, double rhs) {
    return retail_store_f64(
        static_cast<long double>(lhs) * static_cast<long double>(rhs));
}

}  // namespace

Fun007618f0LocalSampleProducerResult
execute_fun_007618f0_local_sample_producer(
    const Fun007618f0LocalSampleProducerInput& input) {
    require_finite_vec(
        input.hdvehicle_pointer_vec_0820,
        "FUN_007618f0 HDVehicle+0x820 pointed vec3 must be finite");
    require_finite_vec(
        input.hdvehicle_pointer_vec_12a0,
        "FUN_007618f0 HDVehicle+0x12a0 pointed vec3 must be finite");
    require_finite_vec(
        input.source_vec_0918,
        "FUN_007618f0 source+0x918 vec3 must be finite");
    if (!std::isfinite(input.source_scalar_0338)) {
        throw std::invalid_argument(
            "FUN_007618f0 source+0x338 scalar must be finite");
    }

    Fun007618f0LocalSampleProducerResult result{};

    // FUN_00753590 first stores the component-wise f64 sum. FUN_007535f0 then
    // multiplies that stored vec3 by the exact f64 constant 0.5 and stores f64
    // again. Keep both round-trip boundaries explicit.
    CollisionQueryVector3d pointer_sum{};
    for (std::size_t index = 0u; index < pointer_sum.size(); ++index) {
        pointer_sum[index] = retail_add_f64(
            input.hdvehicle_pointer_vec_0820[index],
            input.hdvehicle_pointer_vec_12a0[index]);
        result.pointer_midpoint[index] =
            retail_mul_f64(pointer_sum[index], 0.5);
    }

    result.local_base = {
        result.pointer_midpoint[0],
        retail_store_f64(-static_cast<long double>(input.source_scalar_0338)),
        result.pointer_midpoint[2],
    };

    // The final FUN_00753590 call adds source+0x918 and stores the result at
    // HDVehicle+0x3938/+0x3940/+0x3948.
    for (std::size_t index = 0u; index < result.local_sample_3938.size(); ++index) {
        result.local_sample_3938[index] = retail_add_f64(
            result.local_base[index],
            input.source_vec_0918[index]);
    }

    return result;
}

}  // namespace shift::runtime::physics
