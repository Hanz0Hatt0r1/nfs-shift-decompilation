#include "shift_vulkan_d3d9_packet_capture.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <limits>
#include <set>
#include <sstream>
#include <stdexcept>
#include <tuple>
#include <type_traits>
#include <utility>

namespace shift::vulkan {
namespace {

using Field = std::pair<std::string, std::string>;
using Fields = std::vector<Field>;
using Packet = runtime::RecompiledGuestD3d9DrawIndexedPrimitivePacket;

constexpr uint32_t kA8R8G8B8 = 21;
constexpr uint32_t kA1R5G5B5 = 25;
constexpr uint32_t kDxt1 = 0x31545844;
constexpr uint32_t kDxt3 = 0x33545844;
constexpr uint32_t kDxt5 = 0x35545844;
constexpr uint32_t kD3dUsageDynamic = 0x200;

std::string json_string(const std::string& value) {
    std::ostringstream out;
    out << '"';
    for (unsigned char ch : value) {
        switch (ch) {
        case '"': out << "\\\""; break;
        case '\\': out << "\\\\"; break;
        case '\b': out << "\\b"; break;
        case '\f': out << "\\f"; break;
        case '\n': out << "\\n"; break;
        case '\r': out << "\\r"; break;
        case '\t': out << "\\t"; break;
        default:
            if (ch < 0x20) {
                out << "\\u" << std::hex << std::setw(4) << std::setfill('0')
                    << static_cast<unsigned>(ch) << std::dec;
            } else {
                out << static_cast<char>(ch);
            }
        }
    }
    out << '"';
    return out.str();
}

std::string json_u32(uint32_t value) {
    return std::to_string(value);
}

std::string json_i32(int32_t value) {
    return std::to_string(value);
}

std::string json_bool(bool value) {
    return value ? "true" : "false";
}

template <typename Range, typename Convert>
std::string json_array(const Range& values, Convert convert) {
    std::string out = "[";
    bool first = true;
    for (const auto& value : values) {
        if (!first) out += ',';
        first = false;
        out += convert(value);
    }
    out += ']';
    return out;
}

std::string json_u32_array(const std::vector<uint32_t>& values) {
    return json_array(values, [](uint32_t value) { return json_u32(value); });
}

template <size_t N>
std::string json_u32_array(const std::array<uint32_t, N>& values) {
    return json_array(values, [](uint32_t value) { return json_u32(value); });
}

std::string json_float(float value) {
    if (!std::isfinite(value)) {
        throw std::runtime_error("non-finite float cannot be serialized in capture JSON");
    }
    std::ostringstream out;
    out << std::setprecision(std::numeric_limits<float>::max_digits10) << value;
    return out.str();
}

float float_from_bits(uint32_t bits) {
    float value = 0.0f;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

std::string pointer_id(uint32_t value) {
    std::ostringstream out;
    out << "0x" << std::hex << std::setw(8) << std::setfill('0') << value;
    return out.str();
}

std::string resource_signature(const char* prefix, uint32_t value) {
    return std::string(prefix) + ":guest-" + pointer_id(value);
}

std::string bytes_hex(const std::vector<uint8_t>& bytes) {
    static constexpr char digits[] = "0123456789abcdef";
    std::string result;
    result.reserve(bytes.size() * 2);
    for (uint8_t byte : bytes) {
        result.push_back(digits[byte >> 4]);
        result.push_back(digits[byte & 0x0f]);
    }
    return result;
}

void append_u32_le(std::vector<uint8_t>& output, uint32_t value) {
    output.push_back(static_cast<uint8_t>(value));
    output.push_back(static_cast<uint8_t>(value >> 8));
    output.push_back(static_cast<uint8_t>(value >> 16));
    output.push_back(static_cast<uint8_t>(value >> 24));
}

std::vector<uint8_t> dword_bytes(const std::vector<uint32_t>& words) {
    std::vector<uint8_t> result;
    result.reserve(words.size() * 4);
    for (uint32_t word : words) append_u32_le(result, word);
    return result;
}

std::vector<uint8_t> declaration_bytes(const Packet& packet) {
    std::vector<uint8_t> result;
    result.reserve(packet.vertex_declaration_elements.size() * 8);
    for (const auto& element : packet.vertex_declaration_elements) {
        append_u32_le(result, element[0]);
        append_u32_le(result, element[1]);
    }
    return result;
}

void write_u32_le(std::array<uint8_t, 128>& header, size_t offset, uint32_t value) {
    header[offset] = static_cast<uint8_t>(value);
    header[offset + 1] = static_cast<uint8_t>(value >> 8);
    header[offset + 2] = static_cast<uint8_t>(value >> 16);
    header[offset + 3] = static_cast<uint8_t>(value >> 24);
}

std::vector<uint8_t> dds_bytes(const runtime::RecompiledGuestD3d9TextureBinding& texture) {
    if (texture.width == 0 || texture.height == 0 || texture.levels == 0 ||
        texture.levels != texture.mip_data.size()) {
        throw std::runtime_error("guest texture mip descriptors do not match the binding");
    }

    bool compressed = texture.format == kDxt1 || texture.format == kDxt3 || texture.format == kDxt5;
    uint32_t bytes_per_pixel = texture.format == kA8R8G8B8 ? 4 :
                               texture.format == kA1R5G5B5 ? 2 : 0;
    if (!compressed && bytes_per_pixel == 0) {
        throw std::runtime_error("unsupported guest texture format in Vulkan packet adapter");
    }
    uint32_t full_mip_count = 1;
    for (uint32_t dimension = std::max(texture.width, texture.height);
         dimension > 1; dimension >>= 1) {
        ++full_mip_count;
    }
    if (texture.levels > full_mip_count) {
        throw std::runtime_error("guest texture has more than a full mip chain");
    }

    std::vector<uint8_t> pixels;
    uint32_t expected_width = texture.width;
    uint32_t expected_height = texture.height;
    uint32_t top_size = 0;
    for (size_t level = 0; level < texture.mip_data.size(); ++level) {
        const auto& mip = texture.mip_data[level];
        if (mip.width != expected_width || mip.height != expected_height || mip.pitch == 0) {
            throw std::runtime_error("guest texture mip dimensions or pitch are invalid");
        }
        const uint64_t rows = compressed
            ? std::max<uint64_t>(1, (static_cast<uint64_t>(mip.height) + 3) / 4)
            : mip.height;
        const uint64_t minimum_pitch = compressed
            ? std::max<uint64_t>(1, (static_cast<uint64_t>(mip.width) + 3) / 4) *
                  (texture.format == kDxt1 ? 8u : 16u)
            : static_cast<uint64_t>(mip.width) * bytes_per_pixel;
        const uint64_t expected_size = static_cast<uint64_t>(mip.pitch) * rows;
        if (minimum_pitch > std::numeric_limits<uint32_t>::max() ||
            expected_size > std::numeric_limits<size_t>::max() ||
            mip.pitch != minimum_pitch || mip.bytes.size() != expected_size) {
            throw std::runtime_error("guest texture mip byte count does not match its pitch");
        }
        if (level == 0) {
            if (texture.pitch != mip.pitch) {
                throw std::runtime_error("guest texture top mip pitch differs from binding");
            }
            if (mip.bytes.size() > std::numeric_limits<uint32_t>::max()) {
                throw std::runtime_error("guest texture top mip exceeds DDS size fields");
            }
            top_size = static_cast<uint32_t>(mip.bytes.size());
        }
        constexpr size_t kMaxGuestTextureSnapshot = 64ull * 1024ull * 1024ull;
        if (mip.bytes.size() > kMaxGuestTextureSnapshot - pixels.size()) {
            throw std::runtime_error("guest managed texture exceeds P1 snapshot ceiling");
        }
        pixels.insert(pixels.end(), mip.bytes.begin(), mip.bytes.end());
        expected_width = std::max(1u, expected_width >> 1);
        expected_height = std::max(1u, expected_height >> 1);
    }

    std::array<uint8_t, 128> header{};
    header[0] = 'D'; header[1] = 'D'; header[2] = 'S'; header[3] = ' ';
    write_u32_le(header, 4, 124);
    uint32_t flags = 0x1u | 0x2u | 0x4u | 0x1000u |
                     (compressed ? 0x80000u : 0x8u);
    if (texture.levels > 1) flags |= 0x20000u;
    write_u32_le(header, 8, flags);
    write_u32_le(header, 12, texture.height);
    write_u32_le(header, 16, texture.width);
    write_u32_le(header, 20, compressed ? top_size : texture.mip_data[0].pitch);
    write_u32_le(header, 28, texture.levels);
    write_u32_le(header, 76, 32);
    if (compressed) {
        write_u32_le(header, 80, 0x4u);
        write_u32_le(header, 84, texture.format);
    } else {
        write_u32_le(header, 80, 0x40u | (texture.format == kA8R8G8B8 ? 0x1u : 0u));
        write_u32_le(header, 88, texture.format == kA8R8G8B8 ? 32u : 16u);
        if (texture.format == kA8R8G8B8) {
            write_u32_le(header, 92, 0x00ff0000u);
            write_u32_le(header, 96, 0x0000ff00u);
            write_u32_le(header, 100, 0x000000ffu);
            write_u32_le(header, 104, 0xff000000u);
        } else {
            write_u32_le(header, 92, 0x00007c00u);
            write_u32_le(header, 96, 0x000003e0u);
            write_u32_le(header, 100, 0x0000001fu);
            write_u32_le(header, 104, 0x00008000u);
        }
    }
    uint32_t caps = 0x1000u;
    if (texture.levels > 1) caps |= 0x8u | 0x400000u;
    write_u32_le(header, 108, caps);

    std::vector<uint8_t> result(header.begin(), header.end());
    result.insert(result.end(), pixels.begin(), pixels.end());
    return result;
}

void write_binary(const std::filesystem::path& path, const std::vector<uint8_t>& bytes) {
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    if (!out) throw std::runtime_error("cannot open capture payload: " + path.string());
    if (!bytes.empty()) {
        out.write(reinterpret_cast<const char*>(bytes.data()),
                  static_cast<std::streamsize>(bytes.size()));
    }
    if (!out) throw std::runtime_error("cannot write capture payload: " + path.string());
}

void append_field(std::string& row, const std::string& key, const std::string& json_value) {
    if (row.back() != '{') row += ',';
    row += json_string(key);
    row += ':';
    row += json_value;
}

class CaptureWriter {
public:
    CaptureWriter(const std::filesystem::path& path, std::string device)
        : output_(path, std::ios::trunc), device_(std::move(device)) {
        if (!output_) throw std::runtime_error("cannot open draw capture JSONL: " + path.string());
    }

    uint32_t event(
        const char* kind,
        const Fields& fields = {},
        bool include_device = true) {
        std::string row = "{";
        append_field(row, "event_index", json_u32(next_event_++));
        append_field(row, "frame", "0");
        append_field(row, "process_id", "1");
        if (include_device) append_field(row, "device_ptr", json_string(device_));
        append_field(row, "event", json_string(kind));
        for (const auto& [key, value] : fields) append_field(row, key, value);
        row += "}\n";
        output_ << row;
        if (!output_) throw std::runtime_error("failed writing draw capture JSONL");
        return next_event_ - 1;
    }

    void finish() {
        output_.flush();
        output_.close();
        if (!output_) throw std::runtime_error("failed closing draw capture JSONL");
    }

private:
    std::ofstream output_;
    std::string device_;
    uint32_t next_event_ = 0;
};

template <size_t N>
bool mask_bit(const std::array<uint32_t, N>& mask, size_t bit) {
    return bit < N * 32 && ((mask[bit / 32] >> (bit % 32)) & 1u) != 0;
}

template <size_t N>
void emit_float_constant_events(
    CaptureWriter& writer,
    const char* event_name,
    const std::array<uint32_t, N>& values,
    const std::array<uint32_t, 8>& set_mask,
    size_t register_limit) {
    size_t start = 0;
    while (start < register_limit) {
        if (!mask_bit(set_mask, start)) {
            ++start;
            continue;
        }
        size_t end = start + 1;
        while (end < register_limit && mask_bit(set_mask, end)) ++end;
        std::vector<uint32_t> bits;
        std::vector<float> floats;
        bits.reserve((end - start) * 4);
        floats.reserve((end - start) * 4);
        for (size_t reg = start; reg < end; ++reg) {
            for (size_t component = 0; component < 4; ++component) {
                const uint32_t word = values[reg * 4 + component];
                const float value = float_from_bits(word);
                if (!std::isfinite(value)) {
                    throw std::runtime_error(
                        "non-finite shader float constant cannot use the current JSONL capture schema");
                }
                bits.push_back(word);
                floats.push_back(value);
            }
        }
        writer.event(event_name, {
            {"start_register", json_u32(static_cast<uint32_t>(start))},
            {"vector4f_count", json_u32(static_cast<uint32_t>(end - start))},
            {"values", json_array(floats, [](float value) { return json_float(value); })},
            {"values_bits", json_u32_array(bits)},
        });
        start = end;
    }
}


template <typename T, typename = void> struct HasFloatConstantMasks : std::false_type {};
template <typename T>
struct HasFloatConstantMasks<T, std::void_t<
    decltype(std::declval<const T&>().vertex_float_constant_set_mask),
    decltype(std::declval<const T&>().pixel_float_constant_set_mask)>> : std::true_type {};

template <typename T, typename = void> struct HasBoolConstantMasks : std::false_type {};
template <typename T>
struct HasBoolConstantMasks<T, std::void_t<
    decltype(std::declval<const T&>().vertex_bool_constant_set_mask),
    decltype(std::declval<const T&>().pixel_bool_constant_set_mask)>> : std::true_type {};

template <typename T, typename = void> struct HasBoolQueryHresults : std::false_type {};
template <typename T>
struct HasBoolQueryHresults<T, std::void_t<
    decltype(std::declval<const T&>().vertex_bool_constants_hresult),
    decltype(std::declval<const T&>().pixel_bool_constants_hresult)>> : std::true_type {};

template <typename T>
void emit_proven_float_constant_events(CaptureWriter& writer, const T& packet) {
    if constexpr (HasFloatConstantMasks<T>::value) {
        emit_float_constant_events(writer, "set_vertex_shader_constant_f",
            packet.vertex_float_constants, packet.vertex_float_constant_set_mask, 256);
        emit_float_constant_events(writer, "set_pixel_shader_constant_f",
            packet.pixel_float_constants, packet.pixel_float_constant_set_mask, 224);
    }
    // Raw DWORD arrays still reach the draw event without validity masks;
    // never invent Set*ConstantF write history.
}

template <typename T>
void append_constant_provenance(Fields& draw, const T& packet) {
    if constexpr (HasFloatConstantMasks<T>::value) {
        draw.emplace_back("vertex_float_constant_set_mask",
                          json_u32_array(packet.vertex_float_constant_set_mask));
        draw.emplace_back("pixel_float_constant_set_mask",
                          json_u32_array(packet.pixel_float_constant_set_mask));
    }
    if constexpr (HasBoolConstantMasks<T>::value) {
        draw.emplace_back("vertex_bool_constant_set_mask",
                          json_u32(packet.vertex_bool_constant_set_mask));
        draw.emplace_back("pixel_bool_constant_set_mask",
                          json_u32(packet.pixel_bool_constant_set_mask));
    }
    if constexpr (HasBoolQueryHresults<T>::value) {
        draw.emplace_back("vertex_bool_constants_hresult",
                          json_i32(packet.vertex_bool_constants_hresult));
        draw.emplace_back("pixel_bool_constants_hresult",
                          json_i32(packet.pixel_bool_constants_hresult));
        draw.emplace_back("vertex_bool_constants_hr",
                          json_i32(packet.vertex_bool_constants_hresult));
        draw.emplace_back("pixel_bool_constants_hr",
                          json_i32(packet.pixel_bool_constants_hresult));
    }
}

std::string surface_signature(
    const runtime::RecompiledGuestD3d9SurfaceBinding& surface) {
    const auto& d = surface.description;
    return "surface:" + pointer_id(surface.guest_surface) + ":" +
           json_u32(d[6]) + "x" + json_u32(d[7]) + ":" + json_u32(d[0]);
}

Fields surface_fields(const runtime::RecompiledGuestD3d9SurfaceBinding& surface) {
    const auto& d = surface.description;
    return {
        {"surface_ptr",
         surface.guest_surface == 0 ? "null" : json_string(pointer_id(surface.guest_surface))},
        {"resource_signature", json_string(surface_signature(surface))},
        {"surface_descriptor_status", json_string(surface.guest_surface == 0 ? "null" : "observed")},
        {"surface_format", json_u32(d[0])},
        {"surface_type", json_u32(d[1])},
        {"surface_usage", json_u32(d[2])},
        {"surface_pool", json_u32(d[3])},
        {"surface_multisample_type", json_u32(d[4])},
        {"surface_multisample_quality", json_u32(d[5])},
        {"surface_width", json_u32(d[6])},
        {"surface_height", json_u32(d[7])},
    };
}

std::string safe_filename(uint32_t id, const char* suffix) {
    return pointer_id(id).substr(2) + suffix;
}

void require_write(const std::filesystem::path& path, const std::vector<uint8_t>& bytes) {
    write_binary(path, bytes);
}

}  // namespace

D3d9PacketCaptureAdapter::D3d9PacketCaptureAdapter(
    std::filesystem::path output_root,
    uint32_t draw_limit)
    : output_root_(std::move(output_root)), draw_limit_(draw_limit) {}

bool D3d9PacketCaptureAdapter::install(
    runtime::RecompiledGuestD3d9AdapterInfo& adapter,
    std::string& error) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (installed_) {
        error = "D3D9 packet capture adapter is already installed";
        return false;
    }
    if (output_root_.empty() || draw_limit_ == 0) {
        error = "D3D9 packet capture output root and positive draw limit are required";
        return false;
    }
    downstream_ = adapter;
    // This adapter captures managed DXT5 bytes from guest memory; it does not
    // advertise DXT5 support on the live Vulkan texture-upload path.
    adapter.supports_dxt5_texture = true;
    adapter.backend_context = this;
    adapter.create_device = &create_device_callback;
    adapter.create_texture = &create_texture_callback;
    adapter.release_texture = &release_texture_callback;
    adapter.create_vertex_buffer = &create_vertex_buffer_callback;
    adapter.update_vertex_buffer = &update_vertex_buffer_callback;
    adapter.release_vertex_buffer = &release_vertex_buffer_callback;
    adapter.create_index_buffer = &create_index_buffer_callback;
    adapter.update_index_buffer = &update_index_buffer_callback;
    adapter.release_index_buffer = &release_index_buffer_callback;
    adapter.clear = &clear_callback;
    adapter.present = &present_callback;
    adapter.draw_indexed_primitive = &draw_indexed_primitive_callback;
    installed_ = true;
    return true;
}

uint32_t D3d9PacketCaptureAdapter::captured_draw_count() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return captured_draw_count_;
}

bool D3d9PacketCaptureAdapter::create_device_callback(
    void* context, uint32_t focus_window, uint32_t behavior_flags,
    runtime::RecompiledGuestD3d9PresentationParameters& parameters,
    std::string& error) {
    auto* self = static_cast<D3d9PacketCaptureAdapter*>(context);
    if (!self) { error = "D3D9 packet capture adapter context is null"; return false; }
    return !self->downstream_.create_device || self->downstream_.create_device(
        self->downstream_.backend_context, focus_window, behavior_flags,
        parameters, error);
}

bool D3d9PacketCaptureAdapter::create_texture_callback(
    void* context, uint32_t guest_texture, uint32_t guest_device,
    uint32_t width, uint32_t height, uint32_t levels, uint32_t usage,
    uint32_t format, uint32_t pool, std::string& error) {
    auto* self = static_cast<D3d9PacketCaptureAdapter*>(context);
    if (!self) { error = "D3D9 packet capture adapter context is null"; return false; }
    return !self->downstream_.create_texture || self->downstream_.create_texture(
        self->downstream_.backend_context, guest_texture, guest_device, width,
        height, levels, usage, format, pool, error);
}

void D3d9PacketCaptureAdapter::release_texture_callback(void* context, uint32_t guest_texture) {
    auto* self = static_cast<D3d9PacketCaptureAdapter*>(context);
    if (self && self->downstream_.release_texture) {
        self->downstream_.release_texture(self->downstream_.backend_context, guest_texture);
    }
}

bool D3d9PacketCaptureAdapter::create_vertex_buffer_callback(
    void* context, uint32_t guest_buffer, uint32_t guest_device, uint32_t size,
    uint32_t usage, uint32_t fvf, uint32_t pool, std::string& error) {
    auto* self = static_cast<D3d9PacketCaptureAdapter*>(context);
    if (!self) { error = "D3D9 packet capture adapter context is null"; return false; }
    if (self->downstream_.create_vertex_buffer &&
        !self->downstream_.create_vertex_buffer(self->downstream_.backend_context,
            guest_buffer, guest_device, size, usage, fvf, pool, error)) return false;
    return self->create_buffer(guest_buffer, guest_device, size, usage, 0, fvf,
                               pool, false, error);
}

bool D3d9PacketCaptureAdapter::update_vertex_buffer_callback(
    void* context, uint32_t guest_buffer, uint32_t offset, const uint8_t* data,
    size_t size, std::string& error) {
    auto* self = static_cast<D3d9PacketCaptureAdapter*>(context);
    if (!self) { error = "D3D9 packet capture adapter context is null"; return false; }
    if (self->downstream_.update_vertex_buffer &&
        !self->downstream_.update_vertex_buffer(self->downstream_.backend_context,
            guest_buffer, offset, data, size, error)) return false;
    return self->update_buffer(guest_buffer, offset, data, size, false, error);
}

void D3d9PacketCaptureAdapter::release_vertex_buffer_callback(void* context, uint32_t guest_buffer) {
    auto* self = static_cast<D3d9PacketCaptureAdapter*>(context);
    if (!self) return;
    if (self->downstream_.release_vertex_buffer) {
        self->downstream_.release_vertex_buffer(self->downstream_.backend_context, guest_buffer);
    }
    self->release_buffer(guest_buffer, false);
}

bool D3d9PacketCaptureAdapter::create_index_buffer_callback(
    void* context, uint32_t guest_buffer, uint32_t guest_device, uint32_t size,
    uint32_t usage, uint32_t format, uint32_t pool, std::string& error) {
    auto* self = static_cast<D3d9PacketCaptureAdapter*>(context);
    if (!self) { error = "D3D9 packet capture adapter context is null"; return false; }
    if (self->downstream_.create_index_buffer &&
        !self->downstream_.create_index_buffer(self->downstream_.backend_context,
            guest_buffer, guest_device, size, usage, format, pool, error)) return false;
    return self->create_buffer(guest_buffer, guest_device, size, usage, format,
                               0, pool, true, error);
}

bool D3d9PacketCaptureAdapter::update_index_buffer_callback(
    void* context, uint32_t guest_buffer, uint32_t offset, const uint8_t* data,
    size_t size, std::string& error) {
    auto* self = static_cast<D3d9PacketCaptureAdapter*>(context);
    if (!self) { error = "D3D9 packet capture adapter context is null"; return false; }
    if (self->downstream_.update_index_buffer &&
        !self->downstream_.update_index_buffer(self->downstream_.backend_context,
            guest_buffer, offset, data, size, error)) return false;
    return self->update_buffer(guest_buffer, offset, data, size, true, error);
}

void D3d9PacketCaptureAdapter::release_index_buffer_callback(void* context, uint32_t guest_buffer) {
    auto* self = static_cast<D3d9PacketCaptureAdapter*>(context);
    if (!self) return;
    if (self->downstream_.release_index_buffer) {
        self->downstream_.release_index_buffer(self->downstream_.backend_context, guest_buffer);
    }
    self->release_buffer(guest_buffer, true);
}

bool D3d9PacketCaptureAdapter::clear_callback(
    void* context, uint32_t flags, uint32_t color, uint32_t depth_bits,
    uint32_t stencil, uint32_t rect_count, std::string& error) {
    auto* self = static_cast<D3d9PacketCaptureAdapter*>(context);
    if (!self) { error = "D3D9 packet capture adapter context is null"; return false; }
    return !self->downstream_.clear || self->downstream_.clear(
        self->downstream_.backend_context, flags, color, depth_bits, stencil,
        rect_count, error);
}

bool D3d9PacketCaptureAdapter::present_callback(void* context, std::string& error) {
    auto* self = static_cast<D3d9PacketCaptureAdapter*>(context);
    if (!self) { error = "D3D9 packet capture adapter context is null"; return false; }
    return !self->downstream_.present || self->downstream_.present(
        self->downstream_.backend_context, error);
}

bool D3d9PacketCaptureAdapter::draw_indexed_primitive_callback(
    void* context, const Packet& packet, std::string& error) {
    auto* self = static_cast<D3d9PacketCaptureAdapter*>(context);
    if (!self) { error = "D3D9 packet capture adapter context is null"; return false; }
    if (self->captured_draw_count() < self->draw_limit_ &&
        !self->capture_draw(packet, error)) return false;
    return self->forward_draw(packet, error);
}

bool D3d9PacketCaptureAdapter::create_buffer(
    uint32_t guest_buffer, uint32_t guest_device, uint32_t size,
    uint32_t usage, uint32_t format, uint32_t fvf, uint32_t pool,
    bool index_buffer, std::string& error) {
    if (guest_buffer == 0 || guest_device == 0 || size == 0 ||
        size > (256u << 20)) {
        error = "guest D3D9 buffer descriptor is invalid";
        return false;
    }
    BufferSnapshot snapshot{};
    snapshot.guest_device = guest_device;
    snapshot.size = size;
    snapshot.usage = usage;
    snapshot.format = format;
    snapshot.fvf = fvf;
    snapshot.pool = pool;
    try {
        snapshot.bytes.resize(size);
        snapshot.initialized.resize(size);
    } catch (const std::exception&) {
        error = "cannot allocate guest D3D9 buffer snapshot";
        return false;
    }
    std::lock_guard<std::mutex> lock(mutex_);
    auto& buffers = index_buffer ? index_buffers_ : vertex_buffers_;
    if (buffers.find(guest_buffer) != buffers.end()) {
        error = "guest D3D9 buffer ID was created twice without release";
        return false;
    }
    buffers.emplace(guest_buffer, std::move(snapshot));
    return true;
}

bool D3d9PacketCaptureAdapter::update_buffer(
    uint32_t guest_buffer, uint32_t offset, const uint8_t* data, size_t size,
    bool index_buffer, std::string& error) {
    if (size > 0 && data == nullptr) {
        error = "guest D3D9 buffer update has null data";
        return false;
    }
    std::lock_guard<std::mutex> lock(mutex_);
    auto& buffers = index_buffer ? index_buffers_ : vertex_buffers_;
    auto it = buffers.find(guest_buffer);
    if (it == buffers.end() || offset > it->second.size ||
        size > static_cast<size_t>(it->second.size - offset)) {
        error = "guest D3D9 buffer update is outside its created resource";
        return false;
    }
    if (size) {
        std::copy(data, data + size, it->second.bytes.begin() + offset);
        std::fill(it->second.initialized.begin() + offset,
                  it->second.initialized.begin() + offset + size, uint8_t{1});
        if ((it->second.usage & kD3dUsageDynamic) != 0) {
            it->second.has_unproven_discard_semantics =
                offset != 0 || size != it->second.size;
        }
    }
    return true;
}

void D3d9PacketCaptureAdapter::release_buffer(uint32_t guest_buffer, bool index_buffer) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto& buffers = index_buffer ? index_buffers_ : vertex_buffers_;
    buffers.erase(guest_buffer);
}

bool D3d9PacketCaptureAdapter::capture_draw(const Packet& packet, std::string& error) {
    std::filesystem::path temp;
    try {
        std::lock_guard<std::mutex> lock(mutex_);
        if (captured_draw_count_ >= draw_limit_) return true;
        if (packet.version != 1) throw std::runtime_error("unsupported guest draw packet version");
        if (packet.guest_device == 0 || packet.guest_index_buffer == 0 ||
            packet.guest_vertex_declaration == 0 || packet.guest_vertex_shader == 0 ||
            packet.guest_pixel_shader == 0 || packet.vertex_shader_tokens.empty() ||
            packet.pixel_shader_tokens.empty()) {
            throw std::runtime_error("guest draw packet is missing a required bound resource");
        }
        if (packet.vertex_declaration_elements.empty()) {
            throw std::runtime_error("guest draw packet has no vertex declaration bytes");
        }

        const std::string device = pointer_id(packet.guest_device);
        const std::string draw_name = "draw_" + pointer_id(packet.guest_device).substr(2) +
                                      "_" + std::to_string(packet.sequence);
        temp = output_root_ / (draw_name + ".tmp");
        const auto final = output_root_ / draw_name;
        std::filesystem::remove_all(temp);
        std::filesystem::create_directories(temp / "buffers");
        std::filesystem::create_directories(temp / "textures");
        CaptureWriter writer(temp / "capture.jsonl", device);

        writer.event("device_hooks", {
            {"stream_source_freq_capture", "true"},
            {"buffer_payload_capture_enabled", "true"},
            {"partial_buffer_payload_capture_enabled", "true"},
            {"partial_buffer_payload_length_filter", "0"},
            {"capture_source", json_string("guest-d3d9-packet-v1")},
        });

        const auto index_it = index_buffers_.find(packet.guest_index_buffer);
        if (index_it == index_buffers_.end() ||
            index_it->second.guest_device != packet.guest_device ||
            index_it->second.size != packet.index_buffer_size ||
            index_it->second.usage != packet.index_buffer_usage ||
            index_it->second.format != packet.index_buffer_format ||
            index_it->second.pool != packet.index_buffer_pool) {
            throw std::runtime_error("draw packet index resource does not match prior adapter callbacks");
        }
        if (index_it->second.has_unproven_discard_semantics) {
            throw std::runtime_error("dynamic index buffer had partial updates without lock flags; discard state is unknown");
        }
        if (std::find(index_it->second.initialized.begin(), index_it->second.initialized.end(), uint8_t{0}) !=
            index_it->second.initialized.end()) {
            throw std::runtime_error("index buffer has bytes that were not supplied through update callbacks");
        }
        const std::string ib_id = pointer_id(packet.guest_index_buffer);
        const std::string ib_sig = resource_signature("ib", packet.guest_index_buffer);
        writer.event("create_index_buffer", {
            {"index_buffer_ptr", json_string(ib_id)},
            {"resource_signature", json_string(ib_sig)},
            {"length", json_u32(index_it->second.size)},
            {"usage", json_u32(packet.index_buffer_usage)},
            {"format", json_u32(packet.index_buffer_format)},
            {"pool", json_u32(packet.index_buffer_pool)},
        });
        const std::string ib_file = safe_filename(packet.guest_index_buffer, "_ib.bin");
        require_write(temp / "buffers" / ib_file, index_it->second.bytes);
        writer.event("buffer_payload", {
            {"buffer_ptr", json_string(ib_id)},
            {"resource_type_name", json_string("index_buffer")},
            {"offset", "0"},
            {"requested_size", json_u32(index_it->second.size)},
            {"buffer_length", json_u32(index_it->second.size)},
            {"captured_byte_size", json_u32(index_it->second.size)},
            {"flags", "0"},
            {"snapshot_status", json_string("captured")},
            {"capture_scope", json_string("full-buffer")},
            {"payload_capture_frame", "0"},
            {"payload_path", json_string("buffers/" + ib_file)},
        });
        writer.event("set_indices", {
            {"index_buffer_ptr", json_string(ib_id)},
            {"resource_signature", json_string(ib_sig)},
        });

        std::set<uint32_t> emitted_stream_buffers;
        for (size_t stream_index = 0; stream_index < packet.streams.size(); ++stream_index) {
            const auto& stream = packet.streams[stream_index];
            if (stream.guest_buffer == 0) continue;
            if (stream.stride == 0) throw std::runtime_error("bound guest vertex stream has zero stride");
            const auto vb_it = vertex_buffers_.find(stream.guest_buffer);
            if (vb_it == vertex_buffers_.end() ||
                vb_it->second.guest_device != packet.guest_device ||
                vb_it->second.size != stream.size ||
                vb_it->second.usage != stream.usage ||
                vb_it->second.fvf != stream.fvf ||
                vb_it->second.pool != stream.pool) {
                throw std::runtime_error("draw packet vertex resource does not match prior adapter callbacks");
            }
            if (vb_it->second.has_unproven_discard_semantics) {
                throw std::runtime_error("dynamic vertex buffer had partial updates without lock flags; discard state is unknown");
            }
            if (std::find(vb_it->second.initialized.begin(), vb_it->second.initialized.end(), uint8_t{0}) !=
                vb_it->second.initialized.end()) {
                throw std::runtime_error("vertex buffer has bytes that were not supplied through update callbacks");
            }
            const std::string id = pointer_id(stream.guest_buffer);
            const std::string signature = resource_signature("vb", stream.guest_buffer);
            if (emitted_stream_buffers.insert(stream.guest_buffer).second) {
                writer.event("create_vertex_buffer", {
                    {"vertex_buffer_ptr", json_string(id)},
                    {"resource_signature", json_string(signature)},
                    {"length", json_u32(vb_it->second.size)},
                    {"usage", json_u32(stream.usage)},
                    {"fvf", json_u32(stream.fvf)},
                    {"pool", json_u32(stream.pool)},
                });
                const std::string file = safe_filename(stream.guest_buffer, "_vb.bin");
                require_write(temp / "buffers" / file, vb_it->second.bytes);
                writer.event("buffer_payload", {
                    {"buffer_ptr", json_string(id)},
                    {"resource_type_name", json_string("vertex_buffer")},
                    {"offset", "0"},
                    {"requested_size", json_u32(vb_it->second.size)},
                    {"buffer_length", json_u32(vb_it->second.size)},
                    {"captured_byte_size", json_u32(vb_it->second.size)},
                    {"flags", "0"},
                    {"snapshot_status", json_string("captured")},
                    {"capture_scope", json_string("full-buffer")},
                    {"payload_capture_frame", "0"},
                    {"payload_path", json_string("buffers/" + file)},
                });
            }
            writer.event("set_stream_source", {
                {"vertex_buffer_ptr", json_string(id)},
                {"resource_signature", json_string(signature)},
                {"stream", json_u32(static_cast<uint32_t>(stream_index))},
                {"offset_in_bytes", json_u32(stream.offset)},
                {"stride", json_u32(stream.stride)},
            });
        }

        const auto decl = declaration_bytes(packet);
        const std::string decl_id = pointer_id(packet.guest_vertex_declaration);
        const std::string decl_sig = resource_signature("decl", packet.guest_vertex_declaration);
        writer.event("create_vertex_declaration", {
            {"declaration_ptr", json_string(decl_id)},
            {"resource_signature", json_string(decl_sig)},
            {"byte_length", json_u32(static_cast<uint32_t>(decl.size()))},
            {"bytes_hex", json_string(bytes_hex(decl))},
        });
        writer.event("set_vertex_declaration", {
            {"declaration_ptr", json_string(decl_id)},
            {"resource_signature", json_string(decl_sig)},
        });

        const auto vs_bytes = dword_bytes(packet.vertex_shader_tokens);
        const auto ps_bytes = dword_bytes(packet.pixel_shader_tokens);
        const std::string vs_id = pointer_id(packet.guest_vertex_shader);
        const std::string ps_id = pointer_id(packet.guest_pixel_shader);
        const std::string vs_sig = resource_signature("vs", packet.guest_vertex_shader);
        const std::string ps_sig = resource_signature("ps", packet.guest_pixel_shader);
        writer.event("create_vertex_shader", {
            {"shader_ptr", json_string(vs_id)},
            {"resource_signature", json_string(vs_sig)},
            {"byte_length", json_u32(static_cast<uint32_t>(vs_bytes.size()))},
            {"bytes_hex", json_string(bytes_hex(vs_bytes))},
        });
        writer.event("create_pixel_shader", {
            {"shader_ptr", json_string(ps_id)},
            {"resource_signature", json_string(ps_sig)},
            {"byte_length", json_u32(static_cast<uint32_t>(ps_bytes.size()))},
            {"bytes_hex", json_string(bytes_hex(ps_bytes))},
        });
        writer.event("set_vertex_shader", {
            {"shader_ptr", json_string(vs_id)}, {"resource_signature", json_string(vs_sig)},
        });
        writer.event("set_pixel_shader", {
            {"shader_ptr", json_string(ps_id)}, {"resource_signature", json_string(ps_sig)},
        });

        for (const auto& texture : packet.textures) {
            if (texture.stage > 259) throw std::runtime_error("guest texture stage exceeds P1 SetTexture range");
            const std::string texture_id = texture.guest_texture == 0
                ? "null" : json_string(pointer_id(texture.guest_texture));
            const std::string signature = resource_signature("tex", texture.guest_texture);
            std::string snapshot_status = "backend-owned";
            std::string snapshot_paths = "[]";
            if (!texture.backend_owned) {
                const auto dds = dds_bytes(texture);
                const std::string file = safe_filename(texture.guest_texture,
                    ("_s" + std::to_string(texture.stage) + ".dds").c_str());
                require_write(temp / "textures" / file, dds);
                snapshot_status = "captured";
                snapshot_paths = "[" + json_string("textures/" + file) + "]";
            } else if (!texture.mip_data.empty()) {
                throw std::runtime_error("backend-owned render target unexpectedly carries guest mip bytes");
            }
            writer.event("create_texture", {
                {"texture_ptr", texture_id},
                {"resource_signature", json_string(signature)},
                {"width", json_u32(texture.width)},
                {"height", json_u32(texture.height)},
                {"levels", json_u32(texture.levels)},
                {"usage", json_u32(texture.usage)},
                {"format", json_u32(texture.format)},
                {"pool", json_u32(texture.pool)},
                {"pitch", json_u32(texture.pitch)},
                {"resource_type", "3"},
                {"resource_type_name", json_string("texture2d")},
                {"resource_descriptor_status", json_string("observed")},
                {"level_count", json_u32(texture.levels)},
                {"backend_owned", json_bool(texture.backend_owned)},
            });
            writer.event("set_texture", {
                {"texture_ptr", texture_id},
                {"resource_signature", json_string(signature)},
                {"stage", json_u32(texture.stage)},
                {"resource_type", "3"},
                {"resource_type_name", json_string("texture2d")},
                {"resource_descriptor_status", json_string("observed")},
                {"width", json_u32(texture.width)},
                {"height", json_u32(texture.height)},
                {"format", json_u32(texture.format)},
                {"pool", json_u32(texture.pool)},
                {"usage", json_u32(texture.usage)},
                {"pitch", json_u32(texture.pitch)},
                {"level_count", json_u32(texture.levels)},
                {"snapshot_status", json_string(snapshot_status)},
                {"snapshot_paths", snapshot_paths},
                {"backend_owned", json_bool(texture.backend_owned)},
            });
        }

        for (const auto& state : packet.render_states) {
            writer.event("set_render_state", {
                {"object", json_u32(state.object)},
                {"state", json_u32(state.state)},
                {"value", json_u32(state.value)},
            });
        }
        for (const auto& state : packet.sampler_states) {
            writer.event("set_sampler_state", {
                {"object", json_u32(state.object)},
                {"sampler", json_u32(state.object)},
                {"state", json_u32(state.state)},
                {"value", json_u32(state.value)},
            });
        }

        emit_proven_float_constant_events(writer, packet);

        Fields viewport = {
            {"x", json_u32(packet.viewport[0])},
            {"y", json_u32(packet.viewport[1])},
            {"width", json_u32(packet.viewport[2])},
            {"height", json_u32(packet.viewport[3])},
            {"min_z", json_float(float_from_bits(packet.viewport[4]))},
            {"max_z", json_float(float_from_bits(packet.viewport[5]))},
        };
        writer.event("set_viewport", viewport);

        const auto& targets = packet.render_targets;
        for (const auto& target : targets) {
            auto fields = surface_fields(target);
            fields.emplace_back("render_target_index", json_u32(target.index));
            writer.event("set_render_target", fields);
        }
        if (packet.has_depth_surface) {
            writer.event("set_depth_stencil_surface", surface_fields(packet.depth_surface));
        }

        const auto primary_target = std::find_if(targets.begin(), targets.end(),
            [](const auto& target) { return target.index == 0; });
        const std::string clear_signature = primary_target == targets.end()
            ? "" : surface_signature(*primary_target);
        writer.event("clear", {
            {"rect_count", json_u32(packet.last_clear_rect_count)},
            {"clear_flags", json_u32(packet.last_clear_flags)},
            {"color", json_u32(packet.last_clear_color)},
            {"depth", json_float(float_from_bits(packet.last_clear_depth_bits))},
            {"stencil", json_u32(packet.last_clear_stencil)},
            {"resource_signature", json_string(clear_signature)},
            {"guest_packet_last_clear_unproven_target", "true"},
        });

        Fields draw = {
            {"guest_draw_sequence", json_u32(packet.sequence)},
            {"primitive_type", json_u32(packet.primitive_type)},
            {"base_vertex_index", json_i32(packet.base_vertex_index)},
            {"min_vertex_index", json_u32(packet.min_vertex_index)},
            {"num_vertices", json_u32(packet.num_vertices)},
            {"start_index", json_u32(packet.start_index)},
            {"primitive_count", json_u32(packet.primitive_count)},
            {"stream_source_frequencies", "[]"},
            {"vertex_float_constants_bits", json_u32_array(packet.vertex_float_constants)},
            {"pixel_float_constants_bits", json_u32_array(packet.pixel_float_constants)},
            {"vertex_bool_constants", json_u32_array(packet.vertex_bool_constants)},
            {"pixel_bool_constants", json_u32_array(packet.pixel_bool_constants)},
            {"last_clear_flags", json_u32(packet.last_clear_flags)},
            {"last_clear_color", json_u32(packet.last_clear_color)},
            {"last_clear_depth_bits", json_u32(packet.last_clear_depth_bits)},
            {"last_clear_stencil", json_u32(packet.last_clear_stencil)},
            {"last_clear_rect_count", json_u32(packet.last_clear_rect_count)},
            {"last_clear_target_proven", "false"},
            {"viewport_dwords", json_u32_array(packet.viewport)},
            {"vertex_shader_ptr", json_string(vs_id)},
            {"pixel_shader_ptr", json_string(ps_id)},
            {"index_buffer_ptr", json_string(ib_id)},
        };
        std::string frequencies = "[";
        for (size_t i = 0; i < packet.streams.size(); ++i) {
            if (i) frequencies += ',';
            frequencies += "{\"stream\":" + json_u32(static_cast<uint32_t>(i)) +
                           ",\"setting\":" + json_u32(packet.streams[i].frequency) + "}";
        }
        frequencies += ']';
        append_constant_provenance(draw, packet);
        for (auto& field : draw) if (field.first == "stream_source_frequencies") field.second = frequencies;
        writer.event("draw_indexed_primitive", draw);

        writer.finish();
        std::filesystem::remove_all(final);
        std::filesystem::rename(temp, final);
        ++captured_draw_count_;
        return true;
    } catch (const std::exception& exception) {
        if (!temp.empty()) {
            std::error_code ignored;
            std::filesystem::remove_all(temp, ignored);
        }
        error = exception.what();
        return false;
    }
}

bool D3d9PacketCaptureAdapter::forward_draw(const Packet& packet, std::string& error) {
    if (!downstream_.draw_indexed_primitive) return true;
    return downstream_.draw_indexed_primitive(
        downstream_.backend_context, packet, error);
}

}  // namespace shift::vulkan
