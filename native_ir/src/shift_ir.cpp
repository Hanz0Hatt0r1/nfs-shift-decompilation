#include "shift_ir.hpp"
#include <fstream>
#include <stdexcept>
#include <cstring>

namespace shift::ir {
namespace {

class Reader {
public:
    explicit Reader(const std::filesystem::path& p) : in_(p, std::ios::binary) {
        if (!in_) throw std::runtime_error("cannot open IR file: " + p.string());
    }
    std::uint8_t u8() { return get<std::uint8_t>(); }
    std::uint16_t u16() { return get<std::uint16_t>(); }
    std::uint32_t u32() { return get<std::uint32_t>(); }
    float f32() { return get<float>(); }
    std::string bytes(std::size_t n) {
        std::string s(n, '\0');
        in_.read(s.data(), static_cast<std::streamsize>(n));
        if (!in_) throw std::runtime_error("truncated IR data");
        return s;
    }
    std::size_t tell() {
        return static_cast<std::size_t>(in_.tellg());
    }
private:
    template<class T>
    T get() {
        T v{};
        in_.read(reinterpret_cast<char*>(&v), sizeof(T));
        if (!in_) throw std::runtime_error("truncated IR header/data");
        return v;
    }
    std::ifstream in_;
};

void expectMagic(Reader& r, const char (&magic)[5]) {
    auto got = r.bytes(4);
    if (got != std::string(magic, 4)) throw std::runtime_error("invalid IR magic");
}

std::string readBlob(Reader& r, std::uint32_t n) { return r.bytes(n); }

} // namespace

Mesh loadMgeo(const std::filesystem::path& path) {
    Reader r(path);
    expectMagic(r, "MGEO");
    Mesh m;
    m.version = r.u16();
    m.flags = r.u16();
    const auto vertexCount = r.u32();
    const auto indexCount = r.u32();
    const auto primitiveCount = r.u32();
    const auto uvCount = r.u32();
    const auto normalCount = r.u32();
    const auto metaBytes = r.u32();

    m.positions.resize(vertexCount);
    for (auto& v : m.positions) v = {r.f32(), r.f32(), r.f32()};
    m.normals.resize(normalCount);
    for (auto& v : m.normals) v = {r.f32(), r.f32(), r.f32()};
    if (m.flags & 2u) {
        m.tangents.resize(vertexCount);
        for (auto& v : m.tangents) v = {r.f32(), r.f32(), r.f32()};
    }
    if (m.flags & 16u) {
        m.tangents.resize(vertexCount);
        // V1 API exposes only the primary tangent; secondary tangent is kept opaque below.
        for (std::uint32_t i = 0; i < vertexCount; ++i) { (void)r.f32(); (void)r.f32(); (void)r.f32(); }
    }
    m.uvLayers.resize(uvCount);
    for (auto& layer : m.uvLayers) {
        layer.width = r.u32();
        if (layer.width != 2 && layer.width != 3) throw std::runtime_error("unsupported MGEO UV width");
        layer.values.resize(static_cast<std::size_t>(vertexCount) * layer.width);
        for (auto& value : layer.values) value = r.f32();
    }
    if (m.flags & 4u) (void)r.bytes(static_cast<std::size_t>(vertexCount) * 4u);
    if (m.flags & 32u) (void)r.bytes(static_cast<std::size_t>(vertexCount) * 4u);
    if (m.flags & 64u) (void)r.bytes(static_cast<std::size_t>(vertexCount) * 4u);
    if (m.flags & 128u) (void)r.bytes(static_cast<std::size_t>(vertexCount) * 16u);
    m.indices.resize(indexCount);
    for (auto& i : m.indices) i = r.u32();
    m.primitiveMaterials.resize(primitiveCount);
    // Primitive material strings are stored in metadata JSON; the native core
    // intentionally treats metadata as opaque to keep this loader dependency-free.
    m.metadataJson = readBlob(r, metaBytes);
    validateMesh(m);
    return m;
}

CollisionMesh loadCmesh(const std::filesystem::path& path) {
    Reader r(path);
    expectMagic(r, "CMES");
    CollisionMesh m;
    m.version = r.u16();
    (void)r.u16();
    const auto vertexCount = r.u32();
    const auto indexCount = r.u32();
    const auto triangleCount = r.u32();
    const auto metaBytes = r.u32();
    if (indexCount != triangleCount * 3u) throw std::runtime_error("CMES index/triangle count mismatch");
    m.positions.resize(vertexCount);
    for (auto& v : m.positions) v = {r.f32(), r.f32(), r.f32()};
    m.indices.resize(indexCount);
    for (auto& i : m.indices) i = r.u32();
    m.metadataJson = readBlob(r, metaBytes);
    validateCollisionMesh(m);
    return m;
}

void validateMesh(const Mesh& mesh) {
    if (mesh.version != 1) throw std::runtime_error("unsupported MGEO version");
    if (!mesh.indices.empty()) {
        for (auto i : mesh.indices) if (i >= mesh.positions.size()) throw std::runtime_error("MGEO index out of range");
    }
    if (!mesh.normals.empty() && mesh.normals.size() != mesh.positions.size()) throw std::runtime_error("MGEO normal count mismatch");
    if (!mesh.tangents.empty() && mesh.tangents.size() != mesh.positions.size()) throw std::runtime_error("MGEO tangent count mismatch");
    for (const auto& uv : mesh.uvLayers) if (uv.width < 2 || uv.width > 3 || uv.values.size() != mesh.positions.size() * uv.width) throw std::runtime_error("MGEO UV count mismatch");
}

void validateCollisionMesh(const CollisionMesh& mesh) {
    if (mesh.version != 1) throw std::runtime_error("unsupported CMES version");
    if (mesh.indices.size() % 3u != 0) throw std::runtime_error("CMES index count is not divisible by 3");
    for (auto i : mesh.indices) if (i >= mesh.positions.size()) throw std::runtime_error("CMES index out of range");
}

} // namespace shift::ir
