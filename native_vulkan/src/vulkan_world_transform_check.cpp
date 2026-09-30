#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

#pragma pack(push, 1)
struct WorldTransformHeader {
    char magic[4];
    uint32_t version;
    uint32_t convention;
    uint32_t matrix_bytes;
};
#pragma pack(pop)

static_assert(sizeof(WorldTransformHeader) == 16);

namespace {

constexpr uint32_t kVersion = 1;
constexpr uint32_t kD3DRowToGLSLColumn = 1;

struct Packet {
    WorldTransformHeader header{};
    std::array<float, 16> matrix{};
};

Packet load_packet(const std::string& path) {
    std::ifstream input(path, std::ios::binary | std::ios::ate);
    if (!input) {
        throw std::runtime_error("cannot open world transform packet");
    }
    const std::streamsize size = input.tellg();
    const std::streamsize expected =
        static_cast<std::streamsize>(sizeof(WorldTransformHeader) + 16 * sizeof(float));
    if (size != expected) {
        throw std::runtime_error("world transform packet size mismatch");
    }
    input.seekg(0);

    Packet packet{};
    input.read(
        reinterpret_cast<char*>(&packet.header),
        sizeof(packet.header));
    input.read(
        reinterpret_cast<char*>(packet.matrix.data()),
        static_cast<std::streamsize>(packet.matrix.size() * sizeof(float)));
    if (!input) {
        throw std::runtime_error("failed to read world transform packet");
    }

    if (std::memcmp(packet.header.magic, "SVWT", 4) != 0 ||
        packet.header.version != kVersion ||
        packet.header.convention != kD3DRowToGLSLColumn ||
        packet.header.matrix_bytes != 16 * sizeof(float)) {
        throw std::runtime_error("unsupported world transform packet");
    }

    for (float value : packet.matrix) {
        if (!std::isfinite(value)) {
            throw std::runtime_error("world transform contains non-finite scalar");
        }
    }

    constexpr float epsilon = 1.0e-5f;
    if (std::fabs(packet.matrix[3]) > epsilon ||
        std::fabs(packet.matrix[7]) > epsilon ||
        std::fabs(packet.matrix[11]) > epsilon ||
        std::fabs(packet.matrix[15] - 1.0f) > epsilon) {
        throw std::runtime_error("world transform is not affine D3D row-vector form");
    }
    return packet;
}

std::array<float, 4> transform_row_vector(
    const std::array<float, 16>& matrix,
    const std::array<float, 4>& point) {

    std::array<float, 4> output{};
    for (size_t column = 0; column < 4; ++column) {
        for (size_t row = 0; row < 4; ++row) {
            output[column] += point[row] * matrix[row * 4 + column];
        }
    }
    return output;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr
            << "usage: shift_vulkan_world_transform_check <world_transform.svwt>\n";
        return 2;
    }

    try {
        const Packet packet = load_packet(argv[1]);
        const std::array<float, 4> input = {1.0f, 2.0f, 3.0f, 1.0f};
        const auto output = transform_row_vector(packet.matrix, input);

        std::cout << "{\n";
        std::cout << "  \"format\": \"SHIFT.VulkanWorldTransformCheck/1\",\n";
        std::cout << "  \"status\": \"ok\",\n";
        std::cout << "  \"convention\": \"D3D-row-vector / GLSL-column-mat4-bytes\",\n";
        std::cout << "  \"translation_xyz\": ["
                  << packet.matrix[12] << ", "
                  << packet.matrix[13] << ", "
                  << packet.matrix[14] << "],\n";
        std::cout << "  \"input_point\": [1, 2, 3, 1],\n";
        std::cout << "  \"transformed_point\": ["
                  << output[0] << ", "
                  << output[1] << ", "
                  << output[2] << ", "
                  << output[3] << "]\n";
        std::cout << "}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "shift_vulkan_world_transform_check: "
                  << error.what() << "\n";
        return 1;
    }
}
