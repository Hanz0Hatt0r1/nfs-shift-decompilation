#pragma once

#include "shift_collision_query_contract.hpp"

namespace shift::runtime::physics {

inline constexpr const char* kFun007618f0LocalSampleProducerFormat =
    "SHIFT.Fun007618f0LocalSampleProducer/1";

// Exact-offset input contract recovered from the PC retail FUN_007618f0 writer.
// Names intentionally preserve storage provenance rather than assigning
// unsupported vehicle/suspension semantics to the source fields.
struct Fun007618f0LocalSampleProducerInput {
    CollisionQueryVector3d hdvehicle_pointer_vec_0820{};
    CollisionQueryVector3d hdvehicle_pointer_vec_12a0{};
    double source_scalar_0338 = 0.0;
    CollisionQueryVector3d source_vec_0918{};
};

struct Fun007618f0LocalSampleProducerResult {
    CollisionQueryVector3d pointer_midpoint{};
    CollisionQueryVector3d local_base{};
    CollisionQueryVector3d local_sample_3938{};
};

// PC retail FUN_007618f0 writes HDVehicle+0x3938/+0x3940/+0x3948 as:
//   midpoint = 0.5 * (vec(*HDVehicle+0x820) + vec(*HDVehicle+0x12a0));
//   local_base = {midpoint.x, -source[0x338], midpoint.z};
//   local_sample = local_base + source.vec3[0x918].
// Each vector add/multiply helper stores f64 before the next stage.
Fun007618f0LocalSampleProducerResult
execute_fun_007618f0_local_sample_producer(
    const Fun007618f0LocalSampleProducerInput& input);

}  // namespace shift::runtime::physics
