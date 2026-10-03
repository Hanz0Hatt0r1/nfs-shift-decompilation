#include "shift_vehicle_world_transform_transport.hpp"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>

namespace shift::runtime::render {
namespace {

constexpr float kTolerance = 1.0e-5f;
constexpr float kSingularTolerance = 1.0e-8f;

float determinant3(const VehicleWorldMatrix& matrix) {
    const float a = matrix[0];
    const float b = matrix[1];
    const float c = matrix[2];
    const float d = matrix[4];
    const float e = matrix[5];
    const float f = matrix[6];
    const float g = matrix[8];
    const float h = matrix[9];
    const float i = matrix[10];
    return
        a * (e * i - f * h) -
        b * (d * i - f * g) +
        c * (d * h - e * g);
}

bool linear_identity(const VehicleWorldMatrix& matrix) {
    return
        std::fabs(matrix[0] - 1.0f) <= kTolerance &&
        std::fabs(matrix[1]) <= kTolerance &&
        std::fabs(matrix[2]) <= kTolerance &&
        std::fabs(matrix[4]) <= kTolerance &&
        std::fabs(matrix[5] - 1.0f) <= kTolerance &&
        std::fabs(matrix[6]) <= kTolerance &&
        std::fabs(matrix[8]) <= kTolerance &&
        std::fabs(matrix[9]) <= kTolerance &&
        std::fabs(matrix[10] - 1.0f) <= kTolerance;
}

std::string trim(std::string value) {
    const auto first = value.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) return {};
    const auto last = value.find_last_not_of(" \t\r\n");
    return value.substr(first, last - first + 1u);
}

void require_float3(
    const VehicleVertexAttribute& attribute,
    const char* semantic) {
    if (attribute.format != 2u) {
        throw std::runtime_error(
            std::string("vehicle transform ") + semantic +
            " must be FLOAT3");
    }
}

}  // namespace

void validate_vehicle_world_matrix(
    const VehicleWorldMatrix& matrix) {
    for (float value : matrix) {
        if (!std::isfinite(value)) {
            throw std::runtime_error(
                "vehicle world transform contains non-finite scalar");
        }
    }
    if (std::fabs(matrix[3]) > kTolerance ||
        std::fabs(matrix[7]) > kTolerance ||
        std::fabs(matrix[11]) > kTolerance ||
        std::fabs(matrix[15] - 1.0f) > kTolerance) {
        throw std::runtime_error(
            "vehicle world transform is not affine D3D row-vector form");
    }
    const float determinant = determinant3(matrix);
    if (!std::isfinite(determinant) ||
        std::fabs(determinant) <= kSingularTolerance) {
        throw std::runtime_error(
            "vehicle world transform affine linear block is singular");
    }
}

VehicleWorldTransformScript load_vehicle_world_transform_script(
    const std::string& path) {
    std::ifstream file(path);
    if (!file) {
        throw std::runtime_error(
            "cannot open vehicle world transform script: " + path);
    }

    VehicleWorldTransformScript script{};
    bool header_seen = false;
    std::string line;
    std::uint64_t line_number = 0;
    while (std::getline(file, line)) {
        ++line_number;
        const std::string value = trim(line);
        if (value.empty() || value.front() == '#') continue;
        if (!header_seen) {
            if (value != VehicleWorldTransformScript::format) {
                throw std::runtime_error(
                    "vehicle world transform script header is invalid");
            }
            header_seen = true;
            continue;
        }

        std::istringstream row(value);
        std::uint64_t step = 0;
        VehicleWorldMatrix matrix{};
        std::string extra;
        if (!(row >> step)) {
            throw std::runtime_error(
                "vehicle world transform step is missing at line " +
                std::to_string(line_number));
        }
        for (float& scalar : matrix) {
            if (!(row >> scalar)) {
                throw std::runtime_error(
                    "vehicle world transform row is incomplete at line " +
                    std::to_string(line_number));
            }
        }
        if (row >> extra) {
            throw std::runtime_error(
                "vehicle world transform row has extra fields at line " +
                std::to_string(line_number));
        }
        if (step != script.steps.size()) {
            throw std::runtime_error(
                "vehicle world transform steps must be contiguous from zero");
        }
        validate_vehicle_world_matrix(matrix);
        script.steps.push_back(matrix);
    }
    if (!header_seen) {
        throw std::runtime_error(
            "vehicle world transform script header is missing");
    }
    if (script.steps.empty()) {
        throw std::runtime_error(
            "vehicle world transform script contains no fixed-step rows");
    }
    return script;
}

std::vector<std::string> load_native_scene_draw_groups(
    const std::string& path,
    std::size_t expected_draw_count) {
    if (expected_draw_count == 0u) {
        throw std::runtime_error(
            "native scene draw-group expected count is zero");
    }
    std::ifstream file(path);
    if (!file) {
        throw std::runtime_error(
            "native scene draw-group sidecar is missing: " + path);
    }
    std::vector<std::string> groups;
    std::string line;
    while (std::getline(file, line)) {
        const std::string value = trim(line);
        if (value.empty()) continue;
        if (value != "track" && value != "vehicle") {
            throw std::runtime_error(
                "native scene draw-group sidecar contains unsupported group: " +
                value);
        }
        groups.push_back(value);
    }
    if (groups.size() != expected_draw_count) {
        throw std::runtime_error(
            "native scene draw-group count does not match bundle_set.paths");
    }
    if (std::find(groups.begin(), groups.end(), "vehicle") == groups.end()) {
        throw std::runtime_error(
            "native scene draw-group sidecar contains no vehicle draw");
    }
    return groups;
}

std::vector<std::size_t> vehicle_draw_indices(
    const std::vector<std::string>& groups) {
    std::vector<std::size_t> result;
    for (std::size_t index = 0; index < groups.size(); ++index) {
        if (groups[index] == "vehicle") result.push_back(index);
        else if (groups[index] != "track") {
            throw std::runtime_error(
                "native scene draw group is neither track nor vehicle");
        }
    }
    if (result.empty()) {
        throw std::runtime_error("native scene has no vehicle draw indices");
    }
    return result;
}

VehicleWorldTransformResult apply_vehicle_world_transform(
    const VehicleObjectGeometry& object_geometry,
    const VehicleWorldMatrix& matrix) {
    validate_vehicle_world_matrix(matrix);
    if (object_geometry.stride == 0u ||
        object_geometry.vertex_bytes.empty() ||
        object_geometry.vertex_bytes.size() % object_geometry.stride != 0u) {
        throw std::runtime_error(
            "vehicle object-space vertex buffer shape is invalid");
    }
    if (object_geometry.attributes.empty()) {
        throw std::runtime_error(
            "vehicle object-space geometry has no attributes");
    }

    const VehicleVertexAttribute* position = nullptr;
    std::vector<const VehicleVertexAttribute*> normals;
    std::vector<const VehicleVertexAttribute*> tangents;
    std::vector<const VehicleVertexAttribute*> tangents2;
    for (const auto& attribute : object_geometry.attributes) {
        if (attribute.stride != object_geometry.stride ||
            attribute.offset + 3u * sizeof(float) > object_geometry.stride) {
            throw std::runtime_error(
                "vehicle object-space attribute exceeds vertex stride");
        }
        switch (attribute.property_id) {
            case 200u:
                if (position != nullptr) {
                    throw std::runtime_error(
                        "vehicle geometry contains duplicate POSITION property 200");
                }
                require_float3(attribute, "POSITION");
                position = &attribute;
                break;
            case 220u:
                require_float3(attribute, "NORMAL");
                normals.push_back(&attribute);
                break;
            case 240u:
                require_float3(attribute, "TANGENT");
                tangents.push_back(&attribute);
                break;
            case 250u:
                require_float3(attribute, "TANGENT2");
                tangents2.push_back(&attribute);
                break;
            case 0u:
                if (!linear_identity(matrix) &&
                    object_geometry.attributes.size() > 1u) {
                    throw std::runtime_error(
                        "dynamic vehicle affine transform requires semantic-aware attributes");
                }
                break;
            default:
                break;
        }
    }
    if (position == nullptr) {
        throw std::runtime_error(
            "vehicle geometry is missing POSITION property 200");
    }

    const float determinant = determinant3(matrix);
    const float inverse_determinant = 1.0f / determinant;
    const float a = matrix[0];
    const float b = matrix[1];
    const float c = matrix[2];
    const float d = matrix[4];
    const float e = matrix[5];
    const float f = matrix[6];
    const float g = matrix[8];
    const float h = matrix[9];
    const float i = matrix[10];
    const float inverse[9] = {
        (e * i - f * h) * inverse_determinant,
        (c * h - b * i) * inverse_determinant,
        (b * f - c * e) * inverse_determinant,
        (f * g - d * i) * inverse_determinant,
        (a * i - c * g) * inverse_determinant,
        (c * d - a * f) * inverse_determinant,
        (d * h - e * g) * inverse_determinant,
        (b * g - a * h) * inverse_determinant,
        (a * e - b * d) * inverse_determinant,
    };

    VehicleWorldTransformResult result{};
    // Important: copy from immutable object-space bytes on every invocation.
    // Callers can therefore apply step N independently of steps 0..N-1.
    result.vertex_bytes = object_geometry.vertex_bytes;
    result.determinant = determinant;
    result.linear_identity = linear_identity(matrix);
    result.mode = result.linear_identity
        ? "translation"
        : object_geometry.attributes.size() > 1u
            ? "affine-semantic-v3"
            : "affine-position-only";

    const std::size_t vertex_count =
        result.vertex_bytes.size() / object_geometry.stride;
    auto load_float3 = [&](std::size_t vertex,
                           const VehicleVertexAttribute& attribute,
                           float value[3]) {
        const std::size_t offset =
            vertex * object_geometry.stride + attribute.offset;
        std::memcpy(
            value,
            result.vertex_bytes.data() + offset,
            3u * sizeof(float));
    };
    auto store_float3 = [&](std::size_t vertex,
                            const VehicleVertexAttribute& attribute,
                            const float value[3]) {
        const std::size_t offset =
            vertex * object_geometry.stride + attribute.offset;
        std::memcpy(
            result.vertex_bytes.data() + offset,
            value,
            3u * sizeof(float));
    };
    auto normalize = [&](float value[3], const char* semantic) {
        const float length_squared =
            value[0] * value[0] +
            value[1] * value[1] +
            value[2] * value[2];
        if (!std::isfinite(length_squared) ||
            length_squared <= kSingularTolerance * kSingularTolerance) {
            throw std::runtime_error(
                std::string("dynamic vehicle ") + semantic +
                " collapses under affine transform");
        }
        const float scale = 1.0f / std::sqrt(length_squared);
        value[0] *= scale;
        value[1] *= scale;
        value[2] *= scale;
    };
    auto transform_direction = [&](float value[3]) {
        const float x = value[0];
        const float y = value[1];
        const float z = value[2];
        value[0] = x * a + y * d + z * g;
        value[1] = x * b + y * e + z * h;
        value[2] = x * c + y * f + z * i;
    };
    auto transform_normal = [&](float value[3]) {
        const float x = value[0];
        const float y = value[1];
        const float z = value[2];
        value[0] = x * inverse[0] + y * inverse[1] + z * inverse[2];
        value[1] = x * inverse[3] + y * inverse[4] + z * inverse[5];
        value[2] = x * inverse[6] + y * inverse[7] + z * inverse[8];
    };

    result.positions.resize(vertex_count * 3u);
    for (std::size_t vertex = 0; vertex < vertex_count; ++vertex) {
        float value[3]{};
        load_float3(vertex, *position, value);
        const float x = value[0];
        const float y = value[1];
        const float z = value[2];
        value[0] = x * a + y * d + z * g + matrix[12];
        value[1] = x * b + y * e + z * h + matrix[13];
        value[2] = x * c + y * f + z * i + matrix[14];
        store_float3(vertex, *position, value);
        result.positions[vertex * 3u + 0u] = value[0];
        result.positions[vertex * 3u + 1u] = value[1];
        result.positions[vertex * 3u + 2u] = value[2];

        for (const auto* attribute : normals) {
            load_float3(vertex, *attribute, value);
            transform_normal(value);
            normalize(value, "NORMAL");
            store_float3(vertex, *attribute, value);
        }
        for (const auto* attribute : tangents) {
            load_float3(vertex, *attribute, value);
            transform_direction(value);
            normalize(value, "TANGENT");
            store_float3(vertex, *attribute, value);
        }
        for (const auto* attribute : tangents2) {
            load_float3(vertex, *attribute, value);
            transform_direction(value);
            normalize(value, "TANGENT2");
            store_float3(vertex, *attribute, value);
        }
    }
    return result;
}

}  // namespace shift::runtime::render
