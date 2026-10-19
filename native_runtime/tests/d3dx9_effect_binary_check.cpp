#include "shift_d3dx9_effect_binary.hpp"

#include <cstdint>
#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void append_u32(std::vector<uint8_t>& bytes, uint32_t value) {
    bytes.push_back(static_cast<uint8_t>(value));
    bytes.push_back(static_cast<uint8_t>(value >> 8));
    bytes.push_back(static_cast<uint8_t>(value >> 16));
    bytes.push_back(static_cast<uint8_t>(value >> 24));
}

void patch_u32(std::vector<uint8_t>& bytes, size_t offset, uint32_t value) {
    for (unsigned int i = 0; i < 4; ++i)
        bytes.at(offset + i) = static_cast<uint8_t>(value >> (i * 8));
}

uint32_t append_name(std::vector<uint8_t>& bytes, const std::string& name) {
    const uint32_t offset = static_cast<uint32_t>(bytes.size());
    append_u32(bytes, static_cast<uint32_t>(name.size() + 1));
    bytes.insert(bytes.end(), name.begin(), name.end());
    bytes.push_back(0);
    return offset;
}

std::vector<uint8_t> make_effect() {
    std::vector<uint8_t> bytes(8, 0);
    const uint32_t table_offset = static_cast<uint32_t>(bytes.size());
    append_u32(bytes, 0);  // Parameters.
    append_u32(bytes, 1);  // Techniques.
    append_u32(bytes, 1);  // Shader variables.
    append_u32(bytes, 1);  // Objects.

    const size_t technique_name_offset_field = bytes.size();
    append_u32(bytes, 0);
    append_u32(bytes, 0);  // Technique annotations.
    append_u32(bytes, 1);  // Passes.
    const size_t pass_name_offset_field = bytes.size();
    append_u32(bytes, 0);
    append_u32(bytes, 0);  // Pass annotations.
    append_u32(bytes, 1);  // States.
    append_u32(bytes, 0);  // State operation.
    append_u32(bytes, 0);  // State index.
    const size_t type_offset_field = bytes.size();
    append_u32(bytes, 0);
    const size_t value_offset_field = bytes.size();
    append_u32(bytes, 0);

    append_u32(bytes, 0);  // String objects.
    append_u32(bytes, 1);  // Resources.
    append_u32(bytes, 0);  // Technique index.
    append_u32(bytes, 0);  // Pass index.
    append_u32(bytes, std::numeric_limits<uint32_t>::max());
    append_u32(bytes, 0);  // State index.
    append_u32(bytes, 0);  // Constant resource.
    const std::vector<uint8_t> shader = {0, 3, 0, 0, 0xff, 0xff, 0, 0};
    append_u32(bytes, static_cast<uint32_t>(shader.size()));
    bytes.insert(bytes.end(), shader.begin(), shader.end());

    const uint32_t type_offset = static_cast<uint32_t>(bytes.size());
    append_u32(bytes, 16);  // D3DXPT_VERTEXSHADER.
    append_u32(bytes, 4);   // D3DXPC_OBJECT.
    const size_t type_name_offset_field = bytes.size();
    append_u32(bytes, 0);
    const size_t semantic_offset_field = bytes.size();
    append_u32(bytes, 0);
    append_u32(bytes, 0);  // Array elements.

    const uint32_t value_offset = static_cast<uint32_t>(bytes.size());
    append_u32(bytes, 0);  // Object id.
    const uint32_t technique_name = append_name(bytes, "ShadowGen");
    const uint32_t pass_name = append_name(bytes, "Pass0");
    const uint32_t type_name = append_name(bytes, "VertexShader");
    const uint32_t empty_name = append_name(bytes, "");

    patch_u32(bytes, 0, 0xfeff0901);
    patch_u32(bytes, 4, table_offset - 8);
    patch_u32(bytes, technique_name_offset_field, technique_name - 8);
    patch_u32(bytes, pass_name_offset_field, pass_name - 8);
    patch_u32(bytes, type_offset_field, type_offset - 8);
    patch_u32(bytes, value_offset_field, value_offset - 8);
    patch_u32(bytes, type_name_offset_field, type_name - 8);
    patch_u32(bytes, semantic_offset_field, empty_name - 8);
    return bytes;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        auto bytes = make_effect();
        shift::runtime::D3dx9BinaryEffect effect;
        std::string error;
        if (!shift::runtime::parse_d3dx9_binary_effect(
                bytes.data(), bytes.size(), effect, error))
            throw std::runtime_error("valid binary effect was rejected: " +
                                     error);
        require(effect.shader_variable_count == 1 &&
                    effect.techniques.size() == 1 &&
                    effect.techniques[0].name == "ShadowGen" &&
                    effect.techniques[0].passes.size() == 1 &&
                    effect.techniques[0].passes[0].name == "Pass0",
                "effect technique or pass metadata was not preserved");
        require(effect.resources.size() == 1 &&
                    effect.resources[0].data.size() == 8 &&
                    effect.objects[0].data == effect.resources[0].data,
                "shader resource was not attached to its effect object");

        bytes.pop_back();
        require(!shift::runtime::parse_d3dx9_binary_effect(
                    bytes.data(), bytes.size(), effect, error) &&
                    !error.empty(),
                "truncated binary effect was accepted");

        if (argc > 1) {
            std::ifstream input(argv[1], std::ios::binary);
            if (!input) throw std::runtime_error("could not open effect input");
            const std::vector<uint8_t> captured(
                std::istreambuf_iterator<char>(input), {});
            shift::runtime::D3dx9BinaryEffect parsed;
            if (!shift::runtime::parse_d3dx9_binary_effect(
                    captured.data(), captured.size(), parsed, error))
                throw std::runtime_error("captured effect was rejected: " + error);
            std::cout << "parameters=" << parsed.parameters.size()
                      << " techniques=" << parsed.techniques.size()
                      << " objects=" << parsed.objects.size()
                      << " resources=" << parsed.resources.size() << '\n';
            for (const auto& parameter : parsed.parameters)
                std::cout << "parameter=" << parameter.type.name
                          << " annotations=" << parameter.annotations.size()
                          << '\n';
            for (const auto& technique : parsed.techniques)
                std::cout << "technique=" << technique.name
                          << " annotations=" << technique.annotations.size()
                          << " passes=" << technique.passes.size() << '\n';
            for (const auto& technique : parsed.techniques) {
                for (const auto& pass : technique.passes)
                    std::cout << "pass=" << pass.name
                              << " annotations=" << pass.annotations.size()
                              << " states=" << pass.states.size() << '\n';
            }
            for (size_t i = 0; i < parsed.objects.size(); ++i)
                std::cout << "object[" << i << "]="
                          << parsed.objects[i].data.size() << " bytes\n";
            for (const auto& resource : parsed.resources)
                std::cout << "resource usage=" << resource.usage
                          << " bytes=" << resource.data.size() << '\n';
        }
        return 0;
    } catch (const std::exception& exception) {
        std::cerr << exception.what() << '\n';
        return 1;
    }
}
