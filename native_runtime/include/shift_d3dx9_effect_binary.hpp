#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace shift::runtime {

struct D3dx9EffectType {
    uint32_t type = 0;
    uint32_t parameter_class = 0;
    uint32_t element_count = 0;
    uint32_t member_count = 0;
    uint32_t rows = 0;
    uint32_t columns = 0;
    std::string name;
    std::string semantic;
    std::vector<D3dx9EffectType> members;
};

struct D3dx9EffectValue {
    std::vector<uint8_t> bytes;
    std::vector<uint32_t> object_ids;
};

struct D3dx9EffectAnnotation {
    D3dx9EffectType type;
    D3dx9EffectValue value;
};

struct D3dx9EffectParameter {
    D3dx9EffectType type;
    uint32_t flags = 0;
    D3dx9EffectValue value;
    std::vector<D3dx9EffectAnnotation> annotations;
};

struct D3dx9EffectState {
    uint32_t operation = 0;
    uint32_t index = 0;
    D3dx9EffectType type;
    D3dx9EffectValue value;
};

struct D3dx9EffectPass {
    std::string name;
    std::vector<D3dx9EffectAnnotation> annotations;
    std::vector<D3dx9EffectState> states;
};

struct D3dx9EffectTechnique {
    std::string name;
    std::vector<D3dx9EffectAnnotation> annotations;
    std::vector<D3dx9EffectPass> passes;
};

struct D3dx9EffectObject {
    std::vector<uint8_t> data;
};

struct D3dx9EffectResource {
    uint32_t technique_index = 0;
    uint32_t pass_index = 0;
    uint32_t element_index = 0;
    uint32_t state_index = 0;
    uint32_t usage = 0;
    std::vector<uint8_t> data;
};

struct D3dx9BinaryEffect {
    uint32_t shader_variable_count = 0;
    std::vector<D3dx9EffectParameter> parameters;
    std::vector<D3dx9EffectTechnique> techniques;
    std::vector<D3dx9EffectObject> objects;
    std::vector<D3dx9EffectResource> resources;
};

bool parse_d3dx9_binary_effect(const uint8_t* data, size_t size,
                               D3dx9BinaryEffect& effect,
                               std::string& error);

}  // namespace shift::runtime
