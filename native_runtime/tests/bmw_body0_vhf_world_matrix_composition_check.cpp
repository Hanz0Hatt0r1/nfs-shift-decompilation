#include "shift_bmw_body0_vhf_world_matrix_composition.hpp"
#include "shift_vehicle_world_transform_transport.hpp"

#include <cmath>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using namespace shift::runtime::physics;
using namespace shift::runtime::render;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void require_close(float actual, float expected, const char* label) {
    if (std::fabs(actual - expected) > 1.0e-5f) {
        throw std::runtime_error(
            std::string(label) + " mismatch: " +
            std::to_string(actual) + " vs " + std::to_string(expected));
    }
}

VehicleWorldMatrix vhf_bind_fixture() {
    return {
        0.0f, 2.0f, 0.0f, 0.0f,
        -1.0f, 0.0f, 0.0f, 0.0f,
        0.0f, 0.0f, 0.5f, 0.0f,
        5.0f, 6.0f, 7.0f, 1.0f,
    };
}

VehicleWorldMatrix body0_bind_fixture() {
    return {
        1.0f, 0.0f, 0.0f, 0.0f,
        0.0f, 2.0f, 0.0f, 0.0f,
        0.0f, 0.0f, 1.0f, 0.0f,
        1.0f, 2.0f, 3.0f, 1.0f,
    };
}

SelectedVehicleBodyPose body0_pose_fixture() {
    SelectedVehicleBodyPose pose{};
    pose.body_index = 0u;
    pose.snapshot_generation = 7u;
    pose.origin = {10.0, 20.0, 30.0};
    pose.basis = {
        1.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f,
        0.0f, 0.0f, 1.0f,
    };
    return pose;
}

void append_float3(std::vector<std::uint8_t>& bytes,
                   float x, float y, float z) {
    const float values[3] = {x, y, z};
    const auto* raw = reinterpret_cast<const std::uint8_t*>(values);
    bytes.insert(bytes.end(), raw, raw + sizeof(values));
}

}  // namespace

int main() {
    try {
        const auto pose = body0_pose_fixture();
        const ProvenBmwVhfBindFrame vhf{true, vhf_bind_fixture()};
        const ProvenBmwBody0BindFrame bind{
            true,
            true,
            0u,
            false,
            body0_bind_fixture(),
        };

        const auto composed = compose_bmw_body0_pose_to_vehicle_world_matrix(
            pose, vhf, bind);
        const auto& matrix = composed.vehicle_world_matrix;

        require_close(matrix[0], 0.0f, "m00");
        require_close(matrix[1], 1.0f, "m01");
        require_close(matrix[4], -1.0f, "m10");
        require_close(matrix[5], 0.0f, "m11");
        require_close(matrix[10], 0.5f, "m22");
        require_close(matrix[12], 14.0f, "tx");
        require_close(matrix[13], 22.0f, "ty");
        require_close(matrix[14], 34.0f, "tz");
        require_close(matrix[15], 1.0f, "homogeneous");

        // Phase 646 is the immediate native consumer.  Validate the produced
        // float32 ABI and execute one object-space point through the existing
        // non-cumulative transform core.
        validate_vehicle_world_matrix(matrix);
        VehicleObjectGeometry geometry{};
        geometry.stride = 12u;
        geometry.attributes = {{0u, 2u, 0u, 12u, 200u}};
        append_float3(geometry.vertex_bytes, 1.0f, 2.0f, 3.0f);
        const auto transformed = apply_vehicle_world_transform(geometry, matrix);
        require(transformed.positions.size() == 3u,
                "Phase 646 did not emit one transformed position");
        require_close(transformed.positions[0], 12.0f, "Phase 646 point x");
        require_close(transformed.positions[1], 23.0f, "Phase 646 point y");
        require_close(transformed.positions[2], 35.5f, "Phase 646 point z");

        bool bind_proof_rejected = false;
        try {
            auto blocked = bind;
            blocked.ready = false;
            (void)compose_bmw_body0_pose_to_vehicle_world_matrix(pose, vhf, blocked);
        } catch (const std::invalid_argument& exc) {
            bind_proof_rejected =
                std::string(exc.what()).find("proven-static") != std::string::npos;
        }
        require(bind_proof_rejected,
                "Phase 704 accepted missing BODY0 bind-frame proof");

        bool identity_assumption_rejected = false;
        try {
            auto assumed = bind;
            assumed.identity_matrix_assumed = true;
            (void)compose_bmw_body0_pose_to_vehicle_world_matrix(pose, vhf, assumed);
        } catch (const std::invalid_argument& exc) {
            identity_assumption_rejected =
                std::string(exc.what()).find("identity-matrix assumption") != std::string::npos;
        }
        require(identity_assumption_rejected,
                "Phase 704 accepted assumed identity BODY0 bind frame");

        bool wrong_body_rejected = false;
        try {
            auto wrong_pose = pose;
            wrong_pose.body_index = 9u;
            (void)compose_bmw_body0_pose_to_vehicle_world_matrix(wrong_pose, vhf, bind);
        } catch (const std::invalid_argument& exc) {
            wrong_body_rejected =
                std::string(exc.what()).find("BODY 0") != std::string::npos;
        }
        require(wrong_body_rejected,
                "Phase 704 accepted non-chassis persistent BODY pose");

        bool singular_rejected = false;
        try {
            auto singular = bind;
            singular.body0_local_to_vhf_vehicle_root[0] = 0.0f;
            (void)compose_bmw_body0_pose_to_vehicle_world_matrix(pose, vhf, singular);
        } catch (const std::invalid_argument& exc) {
            singular_rejected =
                std::string(exc.what()).find("singular") != std::string::npos;
        }
        require(singular_rejected,
                "Phase 704 accepted singular BODY0 bind matrix");

        bool nonfinite_rejected = false;
        try {
            auto bad_pose = pose;
            bad_pose.origin[0] = std::numeric_limits<double>::quiet_NaN();
            (void)compose_bmw_body0_pose_to_vehicle_world_matrix(bad_pose, vhf, bind);
        } catch (const std::invalid_argument& exc) {
            nonfinite_rejected =
                std::string(exc.what()).find("non-finite") != std::string::npos;
        }
        require(nonfinite_rejected,
                "Phase 704 accepted non-finite BODY0 runtime pose");

        std::cout
            << "{\"format\":\""
            << kNativeBmwBody0VhfWorldMatrixCompositionFormat << "\","
            << "\"phase\":704,"
            << "\"process1_contract\":\"SHIFT.BMWBody0VHFBindFrameFrontier/1\","
            << "\"formula_order\":\"vhf_bind*inverse(body0_bind)*body0_runtime\","
            << "\"selected_body_index\":0,"
            << "\"phase646_matrix_compatible\":true,"
            << "\"phase646_transport_executed\":true,"
            << "\"current_retail_body0_bind_proven\":false,"
            << "\"synthetic_bind_is_retail_proof\":false,"
            << "\"live_vulkan_buffer_mutation_enabled\":false,"
            << "\"fixed_step_auto_schedule\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << "bmw_body0_vhf_world_matrix_composition_check: "
                  << exc.what() << '\n';
        return 1;
    }
}
