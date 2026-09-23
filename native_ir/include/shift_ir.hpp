#pragma once
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

namespace shift::ir {

struct Vec3 {
    float x{}, y{}, z{};
};

struct UVLayer {
    std::uint32_t width{};
    std::vector<float> values;
};

struct Mesh {
    std::uint16_t version{};
    std::uint16_t flags{};
    std::vector<Vec3> positions;
    std::vector<Vec3> normals;
    std::vector<Vec3> tangents;
    std::vector<UVLayer> uvLayers;
    std::vector<std::uint32_t> indices;
    std::vector<std::string> primitiveMaterials;
    std::string metadataJson;
};

struct CollisionMesh {
    std::uint16_t version{};
    std::vector<Vec3> positions;
    std::vector<std::uint32_t> indices;
    std::string metadataJson;
};

Mesh loadMgeo(const std::filesystem::path& path);
CollisionMesh loadCmesh(const std::filesystem::path& path);
void validateMesh(const Mesh& mesh);
void validateCollisionMesh(const CollisionMesh& mesh);

} // namespace shift::ir
