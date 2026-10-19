#include "shift_d3dx9_effect_binary.hpp"

#include <algorithm>
#include <limits>
#include <stdexcept>
#include <utility>

namespace shift::runtime {
namespace {

constexpr uint32_t kD3dx9EffectVersion = 0xfeff0901;
constexpr uint32_t kD3dxParameterClassScalar = 0;
constexpr uint32_t kD3dxParameterClassVector = 1;
constexpr uint32_t kD3dxParameterClassMatrixRows = 2;
constexpr uint32_t kD3dxParameterClassMatrixColumns = 3;
constexpr uint32_t kD3dxParameterClassObject = 4;
constexpr uint32_t kD3dxParameterClassStruct = 5;
constexpr uint32_t kD3dxParameterTypeString = 4;
constexpr uint32_t kD3dxParameterTypeTexture = 5;
constexpr uint32_t kD3dxParameterTypeTextureCube = 9;
constexpr uint32_t kD3dxParameterTypeSampler = 10;
constexpr uint32_t kD3dxParameterTypeSamplerCube = 14;
constexpr uint32_t kD3dxParameterTypePixelShader = 15;
constexpr uint32_t kD3dxParameterTypeVertexShader = 16;
constexpr uint32_t kMaxRecords = 65536;
constexpr unsigned int kMaxTypeDepth = 64;

[[noreturn]] void fail(const char* message) {
    throw std::runtime_error(message);
}

class Cursor {
public:
    Cursor(const uint8_t* data, size_t size, size_t position = 0)
        : data_(data), size_(size), position_(position) {
        if (position > size)
            throw std::runtime_error("effect offset " +
                                     std::to_string(position) +
                                     " exceeds input size " +
                                     std::to_string(size));
    }

    uint32_t u32() {
        require(4);
        const uint32_t value = static_cast<uint32_t>(data_[position_]) |
                               (static_cast<uint32_t>(data_[position_ + 1]) << 8) |
                               (static_cast<uint32_t>(data_[position_ + 2]) << 16) |
                               (static_cast<uint32_t>(data_[position_ + 3]) << 24);
        position_ += 4;
        return value;
    }

    void read(std::vector<uint8_t>& output, size_t size) {
        require(size);
        output.assign(data_ + position_, data_ + position_ + size);
        position_ += size;
    }

    void skip(size_t size) {
        require(size);
        position_ += size;
    }

    size_t position() const { return position_; }
    void set_position(size_t position) {
        if (position > size_) fail("type data extends beyond effect input");
        position_ = position;
    }
    size_t remaining() const { return size_ - position_; }

private:
    void require(size_t size) const {
        if (size > remaining()) fail("truncated D3DX effect data");
    }

    const uint8_t* data_;
    size_t size_;
    size_t position_;
};

bool is_object_id_type(uint32_t type) {
    return type == kD3dxParameterTypeString ||
           (type >= kD3dxParameterTypeTexture &&
            type <= kD3dxParameterTypeTextureCube) ||
           type == kD3dxParameterTypePixelShader ||
           type == kD3dxParameterTypeVertexShader;
}

bool is_sampler_type(uint32_t type) {
    return type >= kD3dxParameterTypeSampler &&
           type <= kD3dxParameterTypeSamplerCube;
}

size_t type_value_size(const D3dx9EffectType& type, unsigned int depth = 0) {
    if (depth > kMaxTypeDepth) fail("D3DX type nesting is too deep");
    if (!type.members.empty()) {
        size_t size = 0;
        for (const auto& member : type.members) {
            const size_t member_size = type_value_size(member, depth + 1);
            if (member_size > std::numeric_limits<size_t>::max() - size)
                fail("D3DX type size overflows");
            size += member_size;
        }
        return size;
    }

    if (type.element_count != 0)
        fail("D3DX array type is missing element records");

    if (type.parameter_class == kD3dxParameterClassObject)
        return is_object_id_type(type.type) ? sizeof(uint32_t) : 0;

    if (type.parameter_class == kD3dxParameterClassScalar ||
        type.parameter_class == kD3dxParameterClassVector ||
        type.parameter_class == kD3dxParameterClassMatrixRows ||
        type.parameter_class == kD3dxParameterClassMatrixColumns) {
        const uint64_t components = static_cast<uint64_t>(type.rows) * type.columns;
        if (components > std::numeric_limits<size_t>::max() / sizeof(uint32_t))
            fail("D3DX numeric type size overflows");
        return static_cast<size_t>(components) * sizeof(uint32_t);
    }
    return 0;
}

class EffectParser {
public:
    EffectParser(const uint8_t* data, size_t size)
        : data_(data), size_(size) {}

    D3dx9BinaryEffect parse() {
        if (data_ == nullptr || size_ < 8)
            fail("D3DX effect input is empty or truncated");
        Cursor header(data_, size_);
        if (header.u32() != kD3dx9EffectVersion)
            fail("unsupported D3DX effect binary version");
        const uint32_t table_offset = header.u32();
        data_ += 8;
        size_ -= 8;
        Cursor table(data_, size_, table_offset);

        const uint32_t parameter_count = count(table.u32(), "parameter");
        const uint32_t technique_count = count(table.u32(), "technique");
        effect_.shader_variable_count = table.u32();
        const uint32_t object_count = count(table.u32(), "object");
        effect_.objects.resize(object_count);

        effect_.parameters.reserve(parameter_count);
        for (uint32_t i = 0; i < parameter_count; ++i)
            effect_.parameters.push_back(parse_parameter(table));

        effect_.techniques.reserve(technique_count);
        for (uint32_t i = 0; i < technique_count; ++i)
            effect_.techniques.push_back(parse_technique(table));

        const uint32_t string_count = count(table.u32(), "string object");
        const uint32_t resource_count = count(table.u32(), "resource");
        for (uint32_t i = 0; i < string_count; ++i) {
            const uint32_t object_id = table.u32();
            auto bytes = read_blob(table);
            set_object_data(object_id, bytes);
        }
        effect_.resources.reserve(resource_count);
        for (uint32_t i = 0; i < resource_count; ++i)
            effect_.resources.push_back(parse_resource(table));
        return std::move(effect_);
    }

private:
    uint32_t count(uint32_t value, const char* what) const {
        if (value > kMaxRecords || value > size_ / sizeof(uint32_t))
            throw std::runtime_error(std::string("invalid D3DX ") + what + " count");
        return value;
    }

    std::string name_at(uint32_t offset) const {
        if (offset > size_)
            throw std::runtime_error("D3DX name offset " +
                                     std::to_string(offset) + " is invalid");
        Cursor cursor(data_, size_, offset);
        const uint32_t size = cursor.u32();
        std::vector<uint8_t> bytes;
        cursor.read(bytes, size);
        const auto terminator = std::find(bytes.begin(), bytes.end(), 0);
        return std::string(bytes.begin(), terminator);
    }

    D3dx9EffectType parse_type(uint32_t offset, unsigned int depth = 0) const {
        if (depth > kMaxTypeDepth) fail("D3DX type nesting is too deep");
        if (offset > size_)
            throw std::runtime_error("D3DX type offset " +
                                     std::to_string(offset) + " is invalid");
        Cursor cursor(data_, size_, offset);
        return parse_type_record(cursor, nullptr, depth);
    }

    D3dx9EffectType parse_type_record(Cursor& cursor,
                                      const D3dx9EffectType* parent,
                                      unsigned int depth) const {
        if (depth > kMaxTypeDepth) fail("D3DX type nesting is too deep");
        D3dx9EffectType type;
        if (parent == nullptr) {
            type.type = cursor.u32();
            type.parameter_class = cursor.u32();
            type.name = name_at(cursor.u32());
            type.semantic = name_at(cursor.u32());
            type.element_count = count(cursor.u32(), "array element");
            if (type.parameter_class == kD3dxParameterClassVector) {
                type.columns = cursor.u32();
                type.rows = cursor.u32();
            } else if (type.parameter_class == kD3dxParameterClassScalar ||
                       type.parameter_class == kD3dxParameterClassMatrixRows ||
                       type.parameter_class == kD3dxParameterClassMatrixColumns) {
                type.rows = cursor.u32();
                type.columns = cursor.u32();
            } else if (type.parameter_class == kD3dxParameterClassStruct) {
                type.member_count = count(cursor.u32(), "struct member");
            }
        } else {
            type = *parent;
            type.element_count = 0;
            type.members.clear();
        }

        if (type.element_count != 0) {
            const size_t element_offset = cursor.position();
            type.members.reserve(type.element_count);
            for (uint32_t i = 0; i < type.element_count; ++i) {
                Cursor element_cursor(data_, size_, element_offset);
                type.members.push_back(
                    parse_type_record(element_cursor, &type, depth + 1));
                cursor.set_position(element_cursor.position());
            }
        } else if (type.member_count != 0) {
            type.members.reserve(type.member_count);
            for (uint32_t i = 0; i < type.member_count; ++i)
                type.members.push_back(parse_type_record(cursor, nullptr,
                                                        depth + 1));
        }
        return type;
    }

    D3dx9EffectValue parse_value(const D3dx9EffectType& type,
                                 uint32_t value_offset) const {
        if (value_offset > size_)
            throw std::runtime_error("D3DX value offset " +
                                     std::to_string(value_offset) +
                                     " is invalid");
        D3dx9EffectValue value;
        Cursor byte_cursor(data_, size_, value_offset);
        const size_t byte_size = type_value_size(type);
        byte_cursor.read(value.bytes, byte_size);
        Cursor cursor(data_, size_, value_offset);
        parse_value_records(type, cursor, value, 0);
        return value;
    }

    void parse_value_records(const D3dx9EffectType& type, Cursor& cursor,
                             D3dx9EffectValue& value,
                             unsigned int depth) const {
        if (depth > kMaxTypeDepth) fail("D3DX value nesting is too deep");
        if (!type.members.empty()) {
            for (const auto& member : type.members)
                parse_value_records(member, cursor, value, depth + 1);
            return;
        }
        if (type.parameter_class != kD3dxParameterClassObject) return;
        if (is_object_id_type(type.type)) {
            const uint32_t object_id = cursor.u32();
            if (object_id >= effect_.objects.size())
                throw std::runtime_error(
                    "D3DX object reference " + std::to_string(object_id) +
                    " is out of range for " +
                    std::to_string(effect_.objects.size()) + " objects");
            value.object_ids.push_back(object_id);
        } else if (is_sampler_type(type.type)) {
            const uint32_t state_count = count(cursor.u32(), "sampler state");
            for (uint32_t i = 0; i < state_count; ++i)
                (void)parse_state(cursor);
        }
    }

    D3dx9EffectAnnotation parse_annotation(Cursor& table) const {
        D3dx9EffectAnnotation annotation;
        annotation.type = parse_type(table.u32());
        annotation.value = parse_value(annotation.type, table.u32());
        return annotation;
    }

    std::vector<D3dx9EffectAnnotation> parse_annotations(
        Cursor& table, uint32_t annotation_count) const {
        std::vector<D3dx9EffectAnnotation> annotations;
        annotations.reserve(annotation_count);
        for (uint32_t i = 0; i < annotation_count; ++i)
            annotations.push_back(parse_annotation(table));
        return annotations;
    }

    D3dx9EffectParameter parse_parameter(Cursor& table) const {
        D3dx9EffectParameter parameter;
        const uint32_t type_offset = table.u32();
        const uint32_t value_offset = table.u32();
        parameter.flags = table.u32();
        const uint32_t annotation_count = count(table.u32(), "annotation");
        parameter.type = parse_type(type_offset);
        parameter.value = parse_value(parameter.type, value_offset);
        parameter.annotations = parse_annotations(table, annotation_count);
        return parameter;
    }

    D3dx9EffectState parse_state(Cursor& table) const {
        D3dx9EffectState state;
        state.operation = table.u32();
        state.index = table.u32();
        state.type = parse_type(table.u32());
        state.value = parse_value(state.type, table.u32());
        return state;
    }

    D3dx9EffectPass parse_pass(Cursor& table) const {
        D3dx9EffectPass pass;
        pass.name = name_at(table.u32());
        const uint32_t annotation_count = count(table.u32(), "annotation");
        const uint32_t state_count = count(table.u32(), "pass state");
        pass.annotations = parse_annotations(table, annotation_count);
        pass.states.reserve(state_count);
        for (uint32_t i = 0; i < state_count; ++i)
            pass.states.push_back(parse_state(table));
        return pass;
    }

    D3dx9EffectTechnique parse_technique(Cursor& table) const {
        D3dx9EffectTechnique technique;
        technique.name = name_at(table.u32());
        const uint32_t annotation_count = count(table.u32(), "annotation");
        const uint32_t pass_count = count(table.u32(), "pass");
        technique.annotations = parse_annotations(table, annotation_count);
        technique.passes.reserve(pass_count);
        for (uint32_t i = 0; i < pass_count; ++i)
            technique.passes.push_back(parse_pass(table));
        return technique;
    }

    std::vector<uint8_t> read_blob(Cursor& cursor) const {
        const uint32_t byte_count = cursor.u32();
        std::vector<uint8_t> bytes;
        cursor.read(bytes, byte_count);
        const size_t padding = (4 - (byte_count & 3)) & 3;
        cursor.skip(padding);
        return bytes;
    }

    void set_object_data(uint32_t object_id,
                         const std::vector<uint8_t>& bytes) {
        if (object_id >= effect_.objects.size())
            fail("D3DX object data id is out of range");
        effect_.objects[object_id].data = bytes;
    }

    D3dx9EffectResource parse_resource(Cursor& table) {
        D3dx9EffectResource resource;
        resource.technique_index = table.u32();
        resource.pass_index = table.u32();
        resource.element_index = table.u32();
        resource.state_index = table.u32();
        resource.usage = table.u32();
        if (resource.usage > 2) fail("unsupported D3DX effect resource usage");
        resource.data = read_blob(table);
        attach_resource_object(resource);
        return resource;
    }

    void attach_resource_object(const D3dx9EffectResource& resource) {
        if (resource.technique_index == UINT32_MAX) return;
        if (resource.technique_index >= effect_.techniques.size())
            fail("D3DX resource technique index is out of range");
        const auto& technique = effect_.techniques[resource.technique_index];
        if (resource.pass_index >= technique.passes.size())
            fail("D3DX resource pass index is out of range");
        const auto& pass = technique.passes[resource.pass_index];
        if (resource.state_index >= pass.states.size())
            fail("D3DX resource state index is out of range");
        const auto& state = pass.states[resource.state_index];
        if (resource.element_index != UINT32_MAX) {
            if (resource.element_index >= state.value.object_ids.size())
                fail("D3DX resource element index is out of range");
            set_object_data(state.value.object_ids[resource.element_index],
                            resource.data);
        } else {
            for (const uint32_t object_id : state.value.object_ids)
                set_object_data(object_id, resource.data);
        }
    }

    const uint8_t* data_;
    size_t size_;
    D3dx9BinaryEffect effect_;
};

}  // namespace

bool parse_d3dx9_binary_effect(const uint8_t* data, size_t size,
                               D3dx9BinaryEffect& effect,
                               std::string& error) {
    effect = {};
    try {
        effect = EffectParser(data, size).parse();
        error.clear();
        return true;
    } catch (const std::exception& exception) {
        error = exception.what();
        return false;
    }
}

}  // namespace shift::runtime
