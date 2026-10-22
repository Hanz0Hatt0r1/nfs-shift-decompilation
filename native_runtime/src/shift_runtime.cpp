#include <vulkan/vulkan.h>
#include <xcb/xcb.h>

#include "shift_ir.hpp"
#include "runtime_state.hpp"
#include "runtime_loop_policy.hpp"
#include "shift_builtin_solver_frame.hpp"
#include "shift_body_export_solver_join.hpp"
#include "shift_body_solver_export_frame.hpp"
#include "shift_generated_body_constraint_frame.hpp"
#include "shift_constraint_sample_relation_frame.hpp"
#include "shift_constraint_relation_reset_frame.hpp"
#include "shift_post_solve_projection.hpp"
#include "shift_vulkan_validation.hpp"
#include "shift_vulkan_d3d9_packet_capture.hpp"
#include "shift_recompiled_pcode_module.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
#include <map>
#include <cctype>
#include <iomanip>
#include <memory>
#include <stdexcept>
#include <string>
#include <sstream>
#include <vector>

namespace {

constexpr uint32_t kWindowWidth = 1280;
constexpr uint32_t kWindowHeight = 720;
constexpr uint32_t kD3dDisplayFormatX8R8G8B8 = 22;
constexpr int kDefaultFrames = 120;
constexpr size_t kFramesInFlight = 2;
constexpr double kFixedDt = 1.0 / 60.0;
constexpr uint64_t kFrozenRetailPcodeFunctionCount = 41538;

uint32_t parse_guest_address(const std::string& text) {
    size_t parsed = 0;
    const auto value = std::stoull(text, &parsed, 0);
    if (parsed != text.size() || value > UINT32_MAX) {
        throw std::runtime_error("invalid x86-32 guest address: " + text);
    }
    return static_cast<uint32_t>(value);
}

std::string format_guest_address(uint32_t address) {
    std::ostringstream text;
    text << "0x" << std::hex << std::setw(8) << std::setfill('0') << address;
    return text.str();
}

std::string format_guest_call_stack(const std::vector<uint32_t>& functions) {
    std::ostringstream text;
    text << '[';
    for (size_t index = 0; index < functions.size(); ++index) {
        if (index != 0) text << ',';
        text << '"' << format_guest_address(functions[index]) << '"';
    }
    text << ']';
    return text.str();
}

std::string format_json_string(const std::string& value) {
    static constexpr char hex[] = "0123456789abcdef";
    std::string escaped;
    escaped.reserve(value.size() + 2);
    escaped.push_back('"');
    for (unsigned char character : value) {
        switch (character) {
            case '"': escaped += "\\\""; break;
            case '\\': escaped += "\\\\"; break;
            case '\b': escaped += "\\b"; break;
            case '\f': escaped += "\\f"; break;
            case '\n': escaped += "\\n"; break;
            case '\r': escaped += "\\r"; break;
            case '\t': escaped += "\\t"; break;
            default:
                if (character < 0x20) {
                    escaped += "\\u00";
                    escaped.push_back(hex[character >> 4]);
                    escaped.push_back(hex[character & 0x0f]);
                } else {
                    escaped.push_back(static_cast<char>(character));
                }
        }
    }
    escaped.push_back('"');
    return escaped;
}

std::string format_ui_state_gate_trace(
    const std::vector<shift::runtime::RecompiledUiStateGateTraceEvent>& events) {
    std::ostringstream text;
    text << '[';
    for (size_t index = 0; index < events.size(); ++index) {
        const auto& event = events[index];
        if (index != 0) text << ',';
        text << "{\"dispatch_count\":" << event.dispatch_count
             << ",\"thread_id\":\""
             << format_guest_address(event.thread_id)
             << "\",\"function\":\""
             << format_guest_address(event.function)
             << "\",\"caller\":\""
             << format_guest_address(event.caller)
             << "\",\"ecx_entry\":\""
             << format_guest_address(event.ecx_entry)
             << "\",\"eax_entry\":\""
             << format_guest_address(event.eax_entry)
             << "\",\"esp_entry\":\""
             << format_guest_address(event.esp_entry)
             << "\",\"gate_state_word\":";
        if (event.has_gate_state_word) {
            text << '"' << format_guest_address(event.gate_state_word) << '"';
        } else {
            text << "null";
        }
        text << ",\"gate_callback_object\":";
        if (event.has_gate_callback_object) {
            text << '"' << format_guest_address(event.gate_callback_object)
                 << '"';
        } else {
            text << "null";
        }
        text << ",\"gate_state_last_writer\":";
        if (event.has_gate_state_last_writer) {
            text << "{\"sequence\":"
                 << event.gate_state_last_writer_sequence
                 << ",\"dispatch_count\":"
                 << event.gate_state_last_writer_dispatch_count
                 << ",\"function\":\""
                 << format_guest_address(
                        event.gate_state_last_writer_function)
                 << "\",\"ecx_entry\":";
            if (event.has_gate_state_last_writer_ecx) {
                text << '"' << format_guest_address(
                                    event.gate_state_last_writer_ecx)
                     << '"';
            } else {
                text << "null";
            }
            text << ",\"caller_function\":";
            if (event.has_gate_state_last_writer_caller_function) {
                text << '"' << format_guest_address(
                                    event.gate_state_last_writer_caller_function)
                     << '"';
            } else {
                text << "null";
            }
            text << ",\"call_return_address\":";
            if (event.has_gate_state_last_writer_call_return_address) {
                text << '"' << format_guest_address(
                                    event.gate_state_last_writer_call_return_address)
                     << '"';
            } else {
                text << "null";
            }
            text << ",\"caller_return_address\":";
            if (event.has_gate_state_last_writer_caller_return_address) {
                text << '"' << format_guest_address(
                                    event.gate_state_last_writer_caller_return_address)
                     << '"';
            } else {
                text << "null";
            }
            text << ",\"ancestor_function\":";
            if (event.has_gate_state_last_writer_ancestor_function) {
                text << '"' << format_guest_address(
                                    event.gate_state_last_writer_ancestor_function)
                     << '"';
            } else {
                text << "null";
            }
            text << ",\"ancestor_caller_function\":";
            if (event.has_gate_state_last_writer_ancestor_caller_function) {
                text << '"' << format_guest_address(
                                    event.gate_state_last_writer_ancestor_caller_function)
                     << '"';
            } else {
                text << "null";
            }
            text << ",\"ancestor_return_address\":";
            if (event.has_gate_state_last_writer_ancestor_return_address) {
                text << '"' << format_guest_address(
                                    event.gate_state_last_writer_ancestor_return_address)
                     << '"';
            } else {
                text << "null";
            }
            text << ",\"thread_id\":\""
                 << format_guest_address(
                        event.gate_state_last_writer_thread_id)
                 << "\",\"write_address\":\""
                 << format_guest_address(
                        event.gate_state_last_writer_address)
                 << "\",\"write_size\":"
                 << event.gate_state_last_writer_size
                 << ",\"word_value\":\""
                 << format_guest_address(
                        event.gate_state_last_writer_word_value)
                 << "\"}";
        } else {
            text << "null";
        }
        text << ",\"helper_flag_last_writer\":";
        if (event.has_helper_flag_last_writer) {
            const auto& writer = event.helper_flag_last_writer;
            text << "{\"sequence\":" << writer.sequence
                 << ",\"dispatch_count\":" << writer.dispatch_count
                 << ",\"function\":\""
                 << format_guest_address(writer.function)
                 << "\",\"ecx_entry\":";
            if (writer.has_ecx_entry) {
                text << '\"' << format_guest_address(writer.ecx_entry)
                     << '\"';
            } else {
                text << "null";
            }
            text << ",\"caller_function\":";
            if (writer.has_caller_function) {
                text << '\"' << format_guest_address(writer.caller_function)
                     << '\"';
            } else {
                text << "null";
            }
            text << ",\"call_return_address\":";
            if (writer.has_call_return_address) {
                text << '\"'
                     << format_guest_address(writer.call_return_address)
                     << '\"';
            } else {
                text << "null";
            }
            text << ",\"caller_return_address\":";
            if (writer.has_caller_return_address) {
                text << '\"'
                     << format_guest_address(writer.caller_return_address)
                     << '\"';
            } else {
                text << "null";
            }
            text << ",\"thread_id\":\""
                 << format_guest_address(writer.thread_id)
                 << "\",\"write_address\":\""
                 << format_guest_address(writer.write_address)
                 << "\",\"write_size\":" << writer.write_size
                 << ",\"word_value\":\""
                 << format_guest_address(writer.word_value) << "\"}";
        } else {
            text << "null";
        }
        text << ",\"helper_flag_byte\":";
        if (event.has_helper_flag_byte) {
            text << '"' << "0x" << std::hex << std::setw(2)
                 << std::setfill('0')
                 << static_cast<unsigned>(event.helper_flag_byte) << std::dec
                 << '"';
        } else {
            text << "null";
        }
        text << ",\"callback_target\":";
        if (event.has_callback_target) {
            text << '"' << format_guest_address(event.callback_target) << '"';
        } else {
            text << "null";
        }
        text << ",\"eax_return\":";
        if (event.completed) {
            text << '"' << format_guest_address(event.eax_return) << '"';
        } else {
            text << "null";
        }
        text << ",\"completed\":"
             << (event.completed ? "true" : "false") << '}';
    }
    text << ']';
    return text.str();
}

std::string format_guest_call_trace_memory_slot(
    const shift::runtime::RecompiledGuestCallTraceMemorySlot& slot) {
    std::ostringstream text;
    text << "{\"offset\":\""
         << format_guest_address(slot.offset)
         << "\",\"value\":";
    if (slot.has_value) {
        text << '"' << format_guest_address(slot.value) << '"';
    } else {
        text << "null";
    }
    text << ",\"last_writer\":";
    if (slot.has_last_writer) {
        const auto& writer = slot.last_writer;
        text << "{\"sequence\":" << writer.sequence
             << ",\"dispatch_count\":" << writer.dispatch_count
             << ",\"function\":\""
             << format_guest_address(writer.function)
             << "\",\"ecx_entry\":";
        if (writer.has_ecx_entry) {
            text << '"' << format_guest_address(writer.ecx_entry) << '"';
        } else {
            text << "null";
        }
        text << ",\"caller_function\":";
        if (writer.has_caller_function) {
            text << '"' << format_guest_address(writer.caller_function)
                 << '"';
        } else {
            text << "null";
        }
        text << ",\"call_return_address\":";
        if (writer.has_call_return_address) {
            text << '"' << format_guest_address(writer.call_return_address)
                 << '"';
        } else {
            text << "null";
        }
        text << ",\"caller_return_address\":";
        if (writer.has_caller_return_address) {
            text << '"' << format_guest_address(writer.caller_return_address)
                 << '"';
        } else {
            text << "null";
        }
        text << ",\"thread_id\":\""
             << format_guest_address(writer.thread_id)
             << "\",\"write_address\":\""
             << format_guest_address(writer.write_address)
             << "\",\"write_size\":" << writer.write_size
             << ",\"word_value\":\""
             << format_guest_address(writer.word_value) << "\"}";
    } else {
        text << "null";
    }
    text << '}';
    return text.str();
}

std::string format_guest_call_trace_memory_slots(
    const std::vector<shift::runtime::RecompiledGuestCallTraceMemorySlot>&
        slots) {
    std::ostringstream text;
    text << '[';
    for (size_t index = 0; index < slots.size(); ++index) {
        if (index != 0) text << ',';
        text << format_guest_call_trace_memory_slot(slots[index]);
    }
    text << ']';
    return text.str();
}

std::string format_guest_call_trace_indexed_source(
    const shift::runtime::RecompiledGuestCallTraceIndexedSource& source) {
    std::ostringstream text;
    text << "{\"pointer_offset\":\""
         << format_guest_address(source.pointer_offset)
         << "\",\"list_pointer\":"
         << format_guest_call_trace_memory_slot(source.list_pointer)
         << ",\"base_offset\":\""
         << format_guest_address(source.base_offset)
         << "\",\"source_base\":"
         << format_guest_call_trace_memory_slot(source.source_base)
         << ",\"count_offset\":\""
         << format_guest_address(source.count_offset)
         << "\",\"source_count\":"
         << format_guest_call_trace_memory_slot(source.source_count)
         << ",\"stride_offset\":\""
         << format_guest_address(source.stride_offset)
         << "\",\"element_stride\":"
         << format_guest_call_trace_memory_slot(source.element_stride)
         << ",\"source_address\":";
    if (source.has_source_address) {
        text << '"' << format_guest_address(source.source_address) << '"';
    } else {
        text << "null";
    }
    text << ",\"source_value\":"
         << format_guest_call_trace_memory_slot(source.source_value) << '}';
    return text.str();
}

std::string format_guest_call_trace_string_slots(
    const std::vector<shift::runtime::RecompiledGuestCallTraceStringSlot>&
        slots) {
    std::ostringstream text;
    text << '[';
    for (size_t index = 0; index < slots.size(); ++index) {
        const auto& slot = slots[index];
        if (index != 0) text << ',';
        text << "{\"offset\":\"" << format_guest_address(slot.offset)
             << "\",\"address\":";
        if (slot.has_address) {
            text << '"' << format_guest_address(slot.address) << '"';
        } else {
            text << "null";
        }
        text << ",\"value\":";
        if (slot.has_value) {
            text << format_json_string(slot.value);
        } else {
            text << "null";
        }
        text << ",\"terminated\":" << (slot.terminated ? "true" : "false")
             << ",\"truncated\":" << (slot.truncated ? "true" : "false")
             << '}';
    }
    text << ']';
    return text.str();
}

std::string format_guest_call_trace(
    const std::vector<shift::runtime::RecompiledGuestCallTraceEvent>& events) {
    std::ostringstream text;
    text << '[';
    for (size_t index = 0; index < events.size(); ++index) {
        const auto& event = events[index];
        if (index != 0) text << ',';
        text << "{\"dispatch_count\":" << event.dispatch_count
             << ",\"thread_id\":\""
             << format_guest_address(event.thread_id)
             << "\",\"function\":\""
             << format_guest_address(event.function)
             << "\",\"caller\":\""
             << format_guest_address(event.caller)
             << "\",\"return_address\":";
        if (event.has_return_address) {
            text << '"' << format_guest_address(event.return_address) << '"';
        } else {
            text << "null";
        }
        text << ",\"ecx_entry\":\""
             << format_guest_address(event.ecx_entry)
             << "\",\"caller_ecx\":\""
             << format_guest_address(event.caller_ecx)
             << "\",\"eax_entry\":\""
             << format_guest_address(event.eax_entry)
             << "\",\"eax_return\":";
        if (event.has_eax_return) {
            text << '"' << format_guest_address(event.eax_return) << '"';
        } else {
            text << "null";
        }
        text << ",\"completion_dispatch_count\":";
        if (event.completed) {
            text << event.completion_dispatch_count;
        } else {
            text << "null";
        }
        text << ",\"completed\":"
             << (event.completed ? "true" : "false")
             << ",\"edx_entry\":\""
             << format_guest_address(event.edx_entry)
             << "\",\"esi_entry\":\""
             << format_guest_address(event.esi_entry)
             << "\",\"esi_return\":";
        if (event.has_esi_return) {
            text << '"' << format_guest_address(event.esi_return) << '"';
        } else {
            text << "null";
        }
        text << ",\"ebp_entry\":\""
             << format_guest_address(event.ebp_entry)
             << "\",\"ebp_return\":";
        if (event.has_ebp_return) {
            text << '"' << format_guest_address(event.ebp_return) << '"';
        } else {
            text << "null";
        }
        text << ",\"esp_entry\":\""
             << format_guest_address(event.esp_entry)
             << "\",\"esp_return\":";
        if (event.has_esp_return) {
            text << '"' << format_guest_address(event.esp_return) << '"';
        } else {
            text << "null";
        }
        text << ",\"is_import\":"
             << (event.is_import ? "true" : "false")
             << ",\"target_resolved\":"
             << (event.target_resolved ? "true" : "false")
             << ",\"import_name\":";
        if (event.is_import) {
            text << format_json_string(event.import_name);
        } else {
            text << "null";
        }
        text << ",\"caller_slots\":"
             << format_guest_call_trace_memory_slots(event.caller_slots)
             << ",\"target_slots\":"
             << format_guest_call_trace_memory_slots(event.target_slots)
             << ",\"stack_slots\":"
             << format_guest_call_trace_memory_slots(event.stack_slots)
             << ",\"indexed_source\":";
        if (event.has_indexed_source) {
            text << format_guest_call_trace_indexed_source(
                event.indexed_source);
        } else {
            text << "null";
        }
        text << ",\"edx_return_slot\":"
             << format_guest_call_trace_memory_slot(event.edx_return_slot)
             << ",\"edx_entry_slot\":"
             << format_guest_call_trace_memory_slot(event.edx_entry_slot)
             << ",\"string_slots\":"
             << format_guest_call_trace_string_slots(event.string_slots)
             << '}';
    }
    text << ']';
    return text.str();
}

std::string format_guest_call_trace_addresses(
    const std::vector<uint32_t>& addresses) {
    std::ostringstream text;
    text << '[';
    for (size_t index = 0; index < addresses.size(); ++index) {
        if (index != 0) text << ',';
        text << '"' << format_guest_address(addresses[index]) << '"';
    }
    text << ']';
    return text.str();
}

std::string format_guest_call_trace_imports(
    const std::vector<std::string>& imports) {
    std::ostringstream text;
    text << '[';
    for (size_t index = 0; index < imports.size(); ++index) {
        if (index != 0) text << ',';
        text << format_json_string(imports[index]);
    }
    text << ']';
    return text.str();
}

#pragma pack(push, 1)
struct GeometryHeader {
    char magic[4];
    uint32_t version;
    uint32_t vertex_count;
    uint32_t index_count;
    uint32_t stride;
    uint32_t attribute_count;
    uint32_t first_index;
    float center_x;
    float center_y;
    float center_z;
    float scale;
};
struct LegacyGeometryAttribute {
    uint32_t location;
    uint32_t format;
    uint32_t offset;
    uint32_t stride;
};
struct GeometryAttribute {
    uint32_t location;
    uint32_t format;
    uint32_t offset;
    uint32_t stride;
    uint32_t property_id;
};
struct WorldTransformHeader {
    char magic[4];
    uint32_t version;
    uint32_t convention;
    uint32_t matrix_bytes;
};
#pragma pack(pop)

static_assert(sizeof(GeometryHeader) == 44);
static_assert(sizeof(LegacyGeometryAttribute) == 16);
static_assert(sizeof(GeometryAttribute) == 20);
static_assert(sizeof(WorldTransformHeader) == 16);

struct PacketGeometry {
    std::vector<float> positions;
    std::vector<uint8_t> vertex_bytes;
    std::vector<GeometryAttribute> attributes;
    std::vector<uint32_t> indices;
    uint32_t stride = sizeof(float) * 3u;
    uint32_t first_index = 0;
    std::string source = "MGEO";
    bool world_transform_applied = false;
    std::string world_transform_mode = "none";
};

constexpr size_t kBundleConstantBytes = 4096;

struct BundleTexture {
    uint32_t register_index = 0;
    uint32_t width = 0;
    uint32_t height = 0;
    uint32_t sampler_mode = 1;
    std::vector<uint8_t> pixels;
};

struct BundleCube {
    uint32_t register_index = 3;
    uint32_t width = 0;
    uint32_t height = 0;
    std::vector<uint8_t> pixels;
};

struct BundlePipelineState {
    VkCullModeFlags cull_mode = VK_CULL_MODE_NONE;
    VkBool32 depth_test_enable = VK_TRUE;
    VkBool32 depth_write_enable = VK_TRUE;
    VkCompareOp depth_compare_op = VK_COMPARE_OP_LESS_OR_EQUAL;
    VkBool32 blend_enable = VK_FALSE;
    VkBlendFactor src_color_blend_factor = VK_BLEND_FACTOR_ONE;
    VkBlendFactor dst_color_blend_factor = VK_BLEND_FACTOR_ZERO;
    VkBlendOp color_blend_op = VK_BLEND_OP_ADD;
    VkBlendFactor src_alpha_blend_factor = VK_BLEND_FACTOR_ONE;
    VkBlendFactor dst_alpha_blend_factor = VK_BLEND_FACTOR_ZERO;
    VkBlendOp alpha_blend_op = VK_BLEND_OP_ADD;
};

struct BundleAssets {
    std::string vertex_shader_path;
    std::string fragment_shader_path;
    BundlePipelineState pipeline_state{};
    std::vector<uint8_t> vertex_constants;
    std::vector<uint8_t> pixel_constants;
    std::vector<BundleTexture> textures;
    BundleCube cube{};
    bool has_cube = false;
};


void vk_check(VkResult result, const char* message) {
    if (result != VK_SUCCESS) {
        throw std::runtime_error(
            std::string(message) + " (VkResult=" +
            std::to_string(static_cast<int>(result)) + ")");
    }
}

uint32_t find_memory_type(
    VkPhysicalDevice physical,
    uint32_t type_bits,
    VkMemoryPropertyFlags required) {

    VkPhysicalDeviceMemoryProperties props{};
    vkGetPhysicalDeviceMemoryProperties(physical, &props);
    for (uint32_t i = 0; i < props.memoryTypeCount; ++i) {
        if ((type_bits & (1u << i)) != 0u &&
            (props.memoryTypes[i].propertyFlags & required) == required) {
            return i;
        }
    }
    throw std::runtime_error("no compatible Vulkan memory type");
}

std::vector<uint32_t> read_spirv(const std::string& path) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file) throw std::runtime_error("cannot open SPIR-V: " + path);
    const std::streamsize size = file.tellg();
    if (size <= 0 || size % static_cast<std::streamsize>(sizeof(uint32_t)) != 0) {
        throw std::runtime_error("invalid SPIR-V size: " + path);
    }
    file.seekg(0);
    std::vector<uint32_t> code(static_cast<size_t>(size) / sizeof(uint32_t));
    if (!file.read(reinterpret_cast<char*>(code.data()), size)) {
        throw std::runtime_error("cannot read SPIR-V: " + path);
    }
    return code;
}


std::vector<uint8_t> read_file_bytes(const std::string& path) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file) throw std::runtime_error("cannot open file: " + path);
    const std::streamsize size = file.tellg();
    if (size <= 0) throw std::runtime_error("empty file: " + path);
    file.seekg(0);
    std::vector<uint8_t> data(static_cast<size_t>(size));
    if (!file.read(reinterpret_cast<char*>(data.data()), size)) {
        throw std::runtime_error("cannot read file: " + path);
    }
    return data;
}

uint32_t read_u32(const std::vector<uint8_t>& data, size_t offset) {
    if (offset > data.size() || data.size() - offset < sizeof(uint32_t)) {
        throw std::runtime_error("bundle packet integer is out of bounds");
    }
    uint32_t value = 0;
    std::memcpy(&value, data.data() + offset, sizeof(value));
    return value;
}

bool file_contains(const std::string& path, const std::string& needle) { 
    std::ifstream file(path, std::ios::binary);
    if (!file) return false;
    const std::string contents(
        (std::istreambuf_iterator<char>(file)),
        std::istreambuf_iterator<char>());
    return contents.find(needle) != std::string::npos;
}

uint32_t json_u32_field(
    const std::string& path,
    const std::string& field) {
    std::ifstream file(path, std::ios::binary);
    if (!file) {
        throw std::runtime_error("cannot open JSON manifest: " + path);
    }
    const std::string text(
        (std::istreambuf_iterator<char>(file)),
        std::istreambuf_iterator<char>());
    const std::string key = "\""+field+"\"";
    const size_t key_pos = text.find(key);
    if (key_pos == std::string::npos) {
        throw std::runtime_error("manifest field is missing: " + field);
    }
    const size_t colon = text.find(':', key_pos + key.size());
    if (colon == std::string::npos) {
        throw std::runtime_error("manifest field has no value: " + field);
    }
    size_t cursor = colon + 1;
    while (cursor < text.size() &&
           std::isspace(static_cast<unsigned char>(text[cursor]))) {
        ++cursor;
    }
    if (cursor == text.size() || !std::isdigit(static_cast<unsigned char>(text[cursor]))) {
        throw std::runtime_error("manifest field is not a non-negative integer: " + field);
    }
    uint64_t value = 0;
    while (cursor < text.size() &&
           std::isdigit(static_cast<unsigned char>(text[cursor]))) {
        value = value * 10u + static_cast<unsigned>(text[cursor] - '0');
        if (value > UINT32_MAX) {
            throw std::runtime_error("manifest field exceeds uint32: " + field);
        }
        ++cursor;
    }
    return static_cast<uint32_t>(value);
}

int32_t json_i32_field(
    const std::string& path,
    const std::string& field) {
    std::ifstream file(path, std::ios::binary);
    if (!file) {
        throw std::runtime_error("cannot open JSON manifest: " + path);
    }
    const std::string text(
        (std::istreambuf_iterator<char>(file)),
        std::istreambuf_iterator<char>());
    const std::string key = "\"" + field + "\"";
    const size_t key_pos = text.find(key);
    if (key_pos == std::string::npos) {
        throw std::runtime_error("manifest field is missing: " + field);
    }
    const size_t colon = text.find(':', key_pos + key.size());
    if (colon == std::string::npos) {
        throw std::runtime_error("manifest field has no value: " + field);
    }
    size_t cursor = colon + 1;
    while (cursor < text.size() &&
           std::isspace(static_cast<unsigned char>(text[cursor]))) {
        ++cursor;
    }
    bool negative = false;
    if (cursor < text.size() && text[cursor] == '-') {
        negative = true;
        ++cursor;
    }
    if (cursor == text.size() ||
        !std::isdigit(static_cast<unsigned char>(text[cursor]))) {
        throw std::runtime_error(
            "manifest field is not an integer: " + field);
    }
    int64_t magnitude = 0;
    while (cursor < text.size() &&
           std::isdigit(static_cast<unsigned char>(text[cursor]))) {
        magnitude =
            magnitude * 10 +
            static_cast<int64_t>(text[cursor] - '0');
        if (magnitude >
            static_cast<int64_t>(
                std::numeric_limits<int32_t>::max()) + 1) {
            throw std::runtime_error(
                "manifest field exceeds int32: " + field);
        }
        ++cursor;
    }
    const int64_t value = negative ? -magnitude : magnitude;
    if (value < std::numeric_limits<int32_t>::min() ||
        value > std::numeric_limits<int32_t>::max()) {
        throw std::runtime_error(
            "manifest field exceeds int32: " + field);
    }
    return static_cast<int32_t>(value);
}

bool json_bool_field(
    const std::string& path,
    const std::string& field) {
    std::ifstream file(path, std::ios::binary);
    if (!file) {
        throw std::runtime_error("cannot open JSON manifest: " + path);
    }
    const std::string text(
        (std::istreambuf_iterator<char>(file)),
        std::istreambuf_iterator<char>());
    const std::string key = "\"" + field + "\"";
    const size_t key_pos = text.find(key);
    if (key_pos == std::string::npos) {
        throw std::runtime_error("manifest field is missing: " + field);
    }
    const size_t colon = text.find(':', key_pos + key.size());
    if (colon == std::string::npos) {
        throw std::runtime_error("manifest field has no value: " + field);
    }
    size_t cursor = colon + 1;
    while (cursor < text.size() &&
           std::isspace(static_cast<unsigned char>(text[cursor]))) {
        ++cursor;
    }
    if (text.compare(cursor, 4, "true") == 0) {
        return true;
    }
    if (text.compare(cursor, 5, "false") == 0) {
        return false;
    }
    throw std::runtime_error(
        "manifest field is not boolean: " + field);
}

void load_camera_state_bridge(
    const std::string& path,
    shift::runtime::CameraBufferRuntime& camera) {
    if (!file_contains(
            path,
            "\"format\": \"SHIFT.NativeCameraStateBridge/1\"") ||
        !file_contains(path, "\"ready\": true")) {
        throw std::runtime_error(
            "native camera state bridge is invalid or blocked");
    }

    const uint32_t active_index =
        json_u32_field(path, "native_active_index");
    const uint32_t sub_flag =
        json_u32_field(path, "native_active_buffer_sub_flag");
    if (active_index >=
            shift::runtime::CameraBufferRuntime::buffer_count ||
        sub_flag > 0xFFu) {
        throw std::runtime_error(
            "native camera state bridge field is out of range");
    }

    const bool applied = camera.apply_evidence_snapshot(
        active_index,
        json_bool_field(
            path,
            "native_update_in_progress"),
        json_i32_field(path, "native_manager_mode"),
        json_i32_field(path, "native_buffer_sub_index"),
        json_i32_field(path, "native_camera_id"),
        json_i32_field(path, "native_active_group"),
        json_i32_field(path, "native_group_restore_value"),
        static_cast<uint8_t>(sub_flag));
    if (!applied) {
        throw std::runtime_error(
            "native camera state bridge could not be applied");
    }
}

VkCullModeFlags load_bundle_cull_mode(const std::string& root) {
    const std::string path = root + "/pipeline_state.json";
    if (!std::filesystem::is_regular_file(path)) {
        return VK_CULL_MODE_NONE;
    }
    const bool legacy =
        file_contains(path, "\"format\": \"SHIFT.MaterialCullState/1\"");
    const bool pipeline =
        file_contains(path, "\"format\": \"SHIFT.MaterialPipelineState/1\"");
    if ((!legacy && !pipeline) ||
        !file_contains(path, "\"ready\": true")) {
        throw std::runtime_error(
            "bundle pipeline-state sidecar is invalid or blocked");
    }
    if (file_contains(
            path,
            "\"vulkan_cull_mode\": \"VK_CULL_MODE_NONE\"")) {
        return VK_CULL_MODE_NONE;
    }
    if (file_contains(
            path,
            "\"vulkan_cull_mode\": \"VK_CULL_MODE_BACK_BIT\"")) {
        return VK_CULL_MODE_BACK_BIT;
    }
    if (file_contains(
            path,
            "\"vulkan_cull_mode\": \"VK_CULL_MODE_FRONT_BIT\"")) {
        return VK_CULL_MODE_FRONT_BIT;
    }
    throw std::runtime_error(
        "bundle pipeline-state cull mode is unsupported");
}

BundlePipelineState load_bundle_pipeline_state(
    const std::string& root) {
    BundlePipelineState out{};
    out.cull_mode = load_bundle_cull_mode(root);

    const std::string path = root + "/pipeline_state.json";
    if (!std::filesystem::is_regular_file(path) ||
        file_contains(
            path,
            "\"format\": \"SHIFT.MaterialCullState/1\"")) {
        return out;
    }
    if (!file_contains(
            path,
            "\"format\": \"SHIFT.MaterialPipelineState/1\"") ||
        !file_contains(path, "\"ready\": true")) {
        throw std::runtime_error(
            "bundle material pipeline state is invalid or blocked");
    }

    auto required_bool = [&](const char* field) -> VkBool32 {
        const std::string prefix = "\"" + std::string(field) + "\": ";
        if (file_contains(path, prefix + "true")) return VK_TRUE;
        if (file_contains(path, prefix + "false")) return VK_FALSE;
        throw std::runtime_error(
            "bundle material pipeline boolean is missing: " +
            std::string(field));
    };
    auto require_token = [&](const char* field,
                             const std::vector<std::pair<std::string, int>>& values)
        -> int {
        for (const auto& row : values) {
            const std::string needle =
                "\"" + std::string(field) + "\": \"" +
                row.first + "\"";
            if (file_contains(path, needle)) return row.second;
        }
        throw std::runtime_error(
            "bundle material pipeline enum is missing/unsupported: " +
            std::string(field));
    };

    out.depth_test_enable = required_bool("depth_test_enable");
    out.depth_write_enable = required_bool("depth_write_enable");
    out.blend_enable = required_bool("blend_enable");
    out.depth_compare_op = static_cast<VkCompareOp>(require_token(
        "depth_compare_op",
        {
            {"VK_COMPARE_OP_NEVER", VK_COMPARE_OP_NEVER},
            {"VK_COMPARE_OP_LESS", VK_COMPARE_OP_LESS},
            {"VK_COMPARE_OP_EQUAL", VK_COMPARE_OP_EQUAL},
            {"VK_COMPARE_OP_LESS_OR_EQUAL", VK_COMPARE_OP_LESS_OR_EQUAL},
            {"VK_COMPARE_OP_GREATER", VK_COMPARE_OP_GREATER},
            {"VK_COMPARE_OP_NOT_EQUAL", VK_COMPARE_OP_NOT_EQUAL},
            {"VK_COMPARE_OP_GREATER_OR_EQUAL", VK_COMPARE_OP_GREATER_OR_EQUAL},
            {"VK_COMPARE_OP_ALWAYS", VK_COMPARE_OP_ALWAYS},
        }));
    const std::vector<std::pair<std::string, int>> blend_factors = {
        {"VK_BLEND_FACTOR_ZERO", VK_BLEND_FACTOR_ZERO},
        {"VK_BLEND_FACTOR_ONE", VK_BLEND_FACTOR_ONE},
        {"VK_BLEND_FACTOR_SRC_COLOR", VK_BLEND_FACTOR_SRC_COLOR},
        {"VK_BLEND_FACTOR_ONE_MINUS_SRC_COLOR", VK_BLEND_FACTOR_ONE_MINUS_SRC_COLOR},
        {"VK_BLEND_FACTOR_SRC_ALPHA", VK_BLEND_FACTOR_SRC_ALPHA},
        {"VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA", VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA},
        {"VK_BLEND_FACTOR_DST_ALPHA", VK_BLEND_FACTOR_DST_ALPHA},
        {"VK_BLEND_FACTOR_ONE_MINUS_DST_ALPHA", VK_BLEND_FACTOR_ONE_MINUS_DST_ALPHA},
        {"VK_BLEND_FACTOR_DST_COLOR", VK_BLEND_FACTOR_DST_COLOR},
        {"VK_BLEND_FACTOR_ONE_MINUS_DST_COLOR", VK_BLEND_FACTOR_ONE_MINUS_DST_COLOR},
        {"VK_BLEND_FACTOR_SRC_ALPHA_SATURATE", VK_BLEND_FACTOR_SRC_ALPHA_SATURATE},
    };
    const std::vector<std::pair<std::string, int>> blend_ops = {
        {"VK_BLEND_OP_ADD", VK_BLEND_OP_ADD},
        {"VK_BLEND_OP_SUBTRACT", VK_BLEND_OP_SUBTRACT},
        {"VK_BLEND_OP_REVERSE_SUBTRACT", VK_BLEND_OP_REVERSE_SUBTRACT},
        {"VK_BLEND_OP_MIN", VK_BLEND_OP_MIN},
        {"VK_BLEND_OP_MAX", VK_BLEND_OP_MAX},
    };
    out.src_color_blend_factor = static_cast<VkBlendFactor>(
        require_token("src_color_blend_factor", blend_factors));
    out.dst_color_blend_factor = static_cast<VkBlendFactor>(
        require_token("dst_color_blend_factor", blend_factors));
    out.color_blend_op = static_cast<VkBlendOp>(
        require_token("color_blend_op", blend_ops));
    out.src_alpha_blend_factor = static_cast<VkBlendFactor>(
        require_token("src_alpha_blend_factor", blend_factors));
    out.dst_alpha_blend_factor = static_cast<VkBlendFactor>(
        require_token("dst_alpha_blend_factor", blend_factors));
    out.alpha_blend_op = static_cast<VkBlendOp>(
        require_token("alpha_blend_op", blend_ops));
    return out;
}

void load_participant_boundary(
    const std::string& path,
    shift::runtime::PhysicsTickBoundary& physics) {

    const bool structural_boundary = file_contains(
        path,
        "\"format\": \"SHIFT.NativePhysicsParticipantBoundary/1\"");
    const bool runtime_evidence = file_contains(
        path,
        "\"format\": \"SHIFT.NativePhysicsParticipantRuntimeEvidence/1\"");
    if ((!structural_boundary && !runtime_evidence) ||
        !file_contains(path, "\"ready\": true")) {
        throw std::runtime_error(
            "native physics participant boundary/evidence is missing or not ready");
    }
    if (!file_contains(path, "\"registry_contract_ready\": true") ||
        !file_contains(path, "\"participant_gate_ready\": true") ||
        !file_contains(path, "\"participant_process_ready\": true") ||
        !file_contains(path, "\"selector_context_ready\": true")) {
        throw std::runtime_error(
            "native physics participant source contracts are not all ready");
    }
    if (!file_contains(
            path,
            "\"registry_manager_global\": \"DAT_00c109e0\"") ||
        !file_contains(
            path,
            "\"selector_global\": \"DAT_00bbc600\"") ||
        !file_contains(path, "\"selector_context_separate\": true")) {
        throw std::runtime_error(
            "native physics participant manager/selector identity mismatch");
    }

    const uint32_t slot_stride =
        json_u32_field(path, "registry_slot_stride");
    const uint32_t descriptor_type =
        json_u32_field(path, "participant_descriptor_type");
    const uint32_t registry_index_source_offset =
        json_u32_field(path, "registry_index_source_offset");
    const uint32_t candidate_ready_offset =
        json_u32_field(path, "selector_candidate_ready_offset");
    if (slot_stride != 0x1fa0u ||
        descriptor_type != 3u ||
        registry_index_source_offset != 0x3cu ||
        candidate_ready_offset != 0x74u) {
        throw std::runtime_error(
            "native physics participant structural ABI mismatch");
    }

    const bool identity_join_proven =
        json_bool_field(
            path,
            "registry_selector_identity_join_proven");
    const int32_t registry_index =
        json_i32_field(path, "participant_registry_index");
    const int32_t selector_ordinal =
        json_i32_field(path, "selector_ordinal");
    const int32_t process_state =
        json_i32_field(path, "participant_process_state");
    const bool participant_instance_ready =
        json_bool_field(path, "participant_instance_ready");

    if (structural_boundary) {
        if (participant_instance_ready ||
            identity_join_proven ||
            registry_index != -1 ||
            selector_ordinal != -1 ||
            process_state != -1 ||
            !file_contains(path, "\"participant_index\": -1") ||
            !file_contains(path, "\"participant_mode\": -1")) {
            throw std::runtime_error(
                "native physics structural participant boundary overclaims runtime instance/identity");
        }
    } else {
        if (!participant_instance_ready ||
            !identity_join_proven ||
            registry_index < 0 ||
            selector_ordinal < 0 ||
            process_state == -1 ||
            !file_contains(
                path,
                "\"same_participant_pointer_proven\": true") ||
            !file_contains(
                path,
                "\"manager_registry_identity_observed\": true") ||
            !file_contains(
                path,
                "\"igphasevehicle_selection_observed\": true") ||
            !file_contains(
                path,
                "\"registry_index_equals_selector_ordinal\": false") ||
            !file_contains(path, "\"participant_index\": -1") ||
            !file_contains(path, "\"participant_mode\": -1")) {
            throw std::runtime_error(
                "native physics runtime participant evidence is incomplete");
        }
    }

    physics.participant_contract_ready = true;
    physics.participant_registry_ready = true;
    physics.selector_context_separate = true;
    physics.registry_slot_stride = slot_stride;
    physics.participant_descriptor_type = descriptor_type;
    physics.participant_identity_join_proven =
        identity_join_proven;

    // Registry index and selector ordinal remain separate observed domains
    // even after the participant pointer join is proven.
    physics.participant_ready =
        runtime_evidence && participant_instance_ready;
    physics.participant_registry_index = registry_index;
    physics.selector_ordinal = selector_ordinal;
    physics.participant_process_state = process_state;
    physics.participant_index = -1;
    physics.participant_mode = -1;
}


shift::runtime::PhysicsWorkspaceBoundary load_physics_manifest(
    const std::string& path) {
    if (!file_contains(
            path,
            "\"format\": \"SHIFT.BMWM3VehiclePhysicsResourceManifest/1\"")) {
        throw std::runtime_error("unsupported native physics manifest");
    }
    shift::runtime::PhysicsWorkspaceBoundary workspace{};
    workspace.configure(
        json_u32_field(path, "body_count"),
        json_u32_field(path, "joint_hinge_count"),
        json_u32_field(path, "bar_count"));
    if (!workspace.ready || workspace.scalar_count != 40u) {
        throw std::runtime_error("BMW SDF manifest does not resolve to 40 solver scalars");
    }
    return workspace;
}

BundleAssets load_bundle_assets(const std::string& root) {
    const std::string interface_path =
        root + "/vulkan_interface.json";
    const bool bmw_interface = file_contains(
        interface_path,
        "\"format\": \"SHIFT.BMWVulkanInterfaceGate/1\"");
    const bool neutral_interface = file_contains(
        interface_path,
        "\"format\": \"SHIFT.VulkanInterfaceGate/1\"");
    if ((!bmw_interface && !neutral_interface) ||
        !file_contains(interface_path, "\"ready\": true") ||
        !file_contains(root + "/spirv_report.json", "\"format\": \"SHIFT.VulkanBundleSPIRV/1\"") ||
        !file_contains(root + "/spirv_report.json", "\"ready\": true")) {
        throw std::runtime_error(
            "bundle shader/interface gate is missing or not ready");
    }

    BundleAssets out;
    out.pipeline_state = load_bundle_pipeline_state(root);
    out.vertex_shader_path = root + "/spirv/submesh_0.vertex.glsl.spv";
    out.fragment_shader_path = root + "/spirv/submesh_0.pixel.glsl.spv";
    if (!std::filesystem::is_regular_file(out.vertex_shader_path) ||
        !std::filesystem::is_regular_file(out.fragment_shader_path)) {
        throw std::runtime_error("bundle submesh-0 SPIR-V shader is missing");
    }

    const auto constants = read_file_bytes(root + "/constants.svcp");
    if (constants.size() != 28u + 2u * kBundleConstantBytes ||
        std::memcmp(constants.data(), "SVCP", 4) != 0 ||
        read_u32(constants, 4) != 1u ||
        read_u32(constants, 8) != 256u ||
        read_u32(constants, 12) != 16u) {
        throw std::runtime_error("unsupported bundle constant packet");
    }
    out.vertex_constants.assign(
        constants.begin() + 28,
        constants.begin() + 28 + kBundleConstantBytes);
    out.pixel_constants.assign(
        constants.begin() + 28 + kBundleConstantBytes,
        constants.end());

    const std::string textures_path = root + "/textures.svtp";
    if (std::filesystem::is_regular_file(textures_path)) {
        const auto data = read_file_bytes(textures_path);
        if (data.size() < 20u || std::memcmp(data.data(), "SVTP", 4) != 0 ||
            read_u32(data, 4) != 1u ||
            read_u32(data, 12) != 1u) {
            throw std::runtime_error("unsupported bundle texture packet");
        }
        const uint32_t count = read_u32(data, 8);
        if (count == 0 || count > 16) {
            throw std::runtime_error("invalid bundle texture count");
        }
        const size_t table_end = 20u + static_cast<size_t>(count) * 24u;
        if (table_end > data.size()) {
            throw std::runtime_error("bundle texture table truncated");
        }
        out.textures.resize(count);
        for (uint32_t i = 0; i < count; ++i) {
            const size_t offset = 20u + static_cast<size_t>(i) * 24u;
            const uint32_t reg = read_u32(data, offset);
            const uint32_t width = read_u32(data, offset + 4);
            const uint32_t height = read_u32(data, offset + 8);
            const uint32_t pixel_offset = read_u32(data, offset + 12);
            const uint32_t pixel_bytes = read_u32(data, offset + 16);
            const uint32_t sampler_mode = read_u32(data, offset + 20);
            const uint64_t expected = static_cast<uint64_t>(width) * height * 4u;
            if (reg > 15 || width == 0 || height == 0 ||
                expected != pixel_bytes || pixel_offset < table_end ||
                static_cast<uint64_t>(pixel_offset) + pixel_bytes > data.size() ||
                sampler_mode < 1 || sampler_mode > 4) {
                throw std::runtime_error("invalid bundle texture record");
            }
            BundleTexture& texture = out.textures[i];
            texture.register_index = reg;
            texture.width = width;
            texture.height = height;
            texture.sampler_mode = sampler_mode;
            texture.pixels.assign(
                data.begin() + static_cast<std::ptrdiff_t>(pixel_offset),
                data.begin() + static_cast<std::ptrdiff_t>(pixel_offset + pixel_bytes));
        }
    }

    const std::string cube_path = root + "/environment_cube.svcp";
    if (std::filesystem::is_regular_file(cube_path)) {
        const auto data = read_file_bytes(cube_path);
        if (data.size() < 28u || std::memcmp(data.data(), "SVCP", 4) != 0 ||
            read_u32(data, 4) != 1u ||
            read_u32(data, 8) != 3u ||
            read_u32(data, 20) != 6u) {
            throw std::runtime_error("unsupported bundle cube packet");
        }
        const uint32_t width = read_u32(data, 12);
        const uint32_t height = read_u32(data, 16);
        const uint32_t face_bytes = read_u32(data, 24);
        const uint64_t expected_face = static_cast<uint64_t>(width) * height * 4u;
        const uint64_t expected_total = expected_face * 6u;
        if (width == 0 || height == 0 || expected_face != face_bytes ||
            data.size() != 28u + expected_total) {
            throw std::runtime_error("bundle cube packet size mismatch");
        }
        out.has_cube = true;
        out.cube.width = width;
        out.cube.height = height;
        out.cube.pixels.assign(data.begin() + 28, data.end());
    }
    return out;
}


void apply_bundle_world_transform(
    const std::string& root,
    PacketGeometry& geometry) {

    const std::filesystem::path path =
        std::filesystem::path(root) / "world_transform.svwt";
    if (!std::filesystem::is_regular_file(path)) {
        return;
    }

    const auto data = read_file_bytes(path.string());
    if (data.size() !=
        sizeof(WorldTransformHeader) + 16u * sizeof(float)) {
        throw std::runtime_error("SVWT packet size mismatch");
    }

    WorldTransformHeader header{};
    std::memcpy(&header, data.data(), sizeof(header));
    if (std::memcmp(header.magic, "SVWT", 4) != 0 ||
        header.version != 1u ||
        header.convention != 1u ||
        header.matrix_bytes != 16u * sizeof(float)) {
        throw std::runtime_error("unsupported SVWT packet");
    }

    float matrix[16]{};
    std::memcpy(
        matrix,
        data.data() + sizeof(header),
        sizeof(matrix));
    for (float value : matrix) {
        if (!std::isfinite(value)) {
            throw std::runtime_error(
                "SVWT matrix contains non-finite scalar");
        }
    }

    constexpr float kTolerance = 1.0e-5f;
    constexpr float kSingularTolerance = 1.0e-8f;
    if (std::fabs(matrix[3]) > kTolerance ||
        std::fabs(matrix[7]) > kTolerance ||
        std::fabs(matrix[11]) > kTolerance ||
        std::fabs(matrix[15] - 1.0f) > kTolerance) {
        throw std::runtime_error(
            "SVWT matrix is not affine D3D row-vector form");
    }

    const float a = matrix[0];
    const float b = matrix[1];
    const float c0 = matrix[2];
    const float d = matrix[4];
    const float e = matrix[5];
    const float f0 = matrix[6];
    const float g = matrix[8];
    const float h = matrix[9];
    const float i = matrix[10];

    const float determinant =
        a * (e * i - f0 * h) -
        b * (d * i - f0 * g) +
        c0 * (d * h - e * g);
    if (!std::isfinite(determinant) ||
        std::fabs(determinant) <= kSingularTolerance) {
        throw std::runtime_error(
            "SVWT affine linear transform is singular");
    }

    const bool linear_identity =
        std::fabs(a - 1.0f) <= kTolerance &&
        std::fabs(b) <= kTolerance &&
        std::fabs(c0) <= kTolerance &&
        std::fabs(d) <= kTolerance &&
        std::fabs(e - 1.0f) <= kTolerance &&
        std::fabs(f0) <= kTolerance &&
        std::fabs(g) <= kTolerance &&
        std::fabs(h) <= kTolerance &&
        std::fabs(i - 1.0f) <= kTolerance;

    if (!linear_identity &&
        geometry.attributes.size() > 1u &&
        std::any_of(
            geometry.attributes.begin(),
            geometry.attributes.end(),
            [](const GeometryAttribute& attribute) {
                return attribute.property_id == 0u;
            })) {
        throw std::runtime_error(
            "SVWT affine execution requires semantic-aware SVGP");
    }

    const float inv_det = 1.0f / determinant;
    const float inverse[9] = {
        (e * i - f0 * h) * inv_det,
        (c0 * h - b * i) * inv_det,
        (b * f0 - c0 * e) * inv_det,
        (f0 * g - d * i) * inv_det,
        (a * i - c0 * g) * inv_det,
        (c0 * d - a * f0) * inv_det,
        (d * h - e * g) * inv_det,
        (b * g - a * h) * inv_det,
        (a * e - b * d) * inv_det,
    };

    const GeometryAttribute* position = nullptr;
    std::vector<const GeometryAttribute*> normals;
    std::vector<const GeometryAttribute*> tangents;
    std::vector<const GeometryAttribute*> tangents2;
    for (const auto& attribute : geometry.attributes) {
        switch (attribute.property_id) {
            case 200u:
                if (position != nullptr || attribute.format != 2u) {
                    throw std::runtime_error(
                        "SVWT execution requires one FLOAT3 POSITION property 200");
                }
                position = &attribute;
                break;
            case 220u:
                if (attribute.format != 2u) {
                    throw std::runtime_error(
                        "SVWT NORMAL property 220 must be FLOAT3");
                }
                normals.push_back(&attribute);
                break;
            case 240u:
                if (attribute.format != 2u) {
                    throw std::runtime_error(
                        "SVWT TANGENT property 240 must be FLOAT3");
                }
                tangents.push_back(&attribute);
                break;
            case 250u:
                if (attribute.format != 2u) {
                    throw std::runtime_error(
                        "SVWT TANGENT2 property 250 must be FLOAT3");
                }
                tangents2.push_back(&attribute);
                break;
            default:
                break;
        }
    }
    if (position == nullptr) {
        throw std::runtime_error(
            "SVWT execution requires POSITION property 200");
    }
    if (geometry.stride == 0 ||
        geometry.vertex_bytes.size() % geometry.stride != 0) {
        throw std::runtime_error(
            "SVWT runtime vertex buffer shape is invalid");
    }

    const uint32_t vertex_count = static_cast<uint32_t>(
        geometry.vertex_bytes.size() / geometry.stride);

    auto load_float3 = [&](uint32_t vertex,
                           const GeometryAttribute& attribute,
                           float out[3]) {
        const size_t offset =
            static_cast<size_t>(vertex) * geometry.stride +
            attribute.offset;
        if (offset + 3u * sizeof(float) >
            geometry.vertex_bytes.size()) {
            throw std::runtime_error(
                "SVWT semantic write exceeds vertex buffer");
        }
        std::memcpy(
            out,
            geometry.vertex_bytes.data() + offset,
            3u * sizeof(float));
    };
    auto store_float3 = [&](uint32_t vertex,
                            const GeometryAttribute& attribute,
                            const float value[3]) {
        const size_t offset =
            static_cast<size_t>(vertex) * geometry.stride +
            attribute.offset;
        std::memcpy(
            geometry.vertex_bytes.data() + offset,
            value,
            3u * sizeof(float));
    };
    auto normalize = [&](float value[3], const char* semantic) {
        const float length_sq =
            value[0] * value[0] +
            value[1] * value[1] +
            value[2] * value[2];
        if (!std::isfinite(length_sq) ||
            length_sq <=
                kSingularTolerance * kSingularTolerance) {
            throw std::runtime_error(
                std::string("SVWT ") + semantic +
                " collapses under affine transform");
        }
        const float inv_length =
            1.0f / std::sqrt(length_sq);
        value[0] *= inv_length;
        value[1] *= inv_length;
        value[2] *= inv_length;
    };
    auto transform_direction = [&](float value[3]) {
        const float x = value[0];
        const float y = value[1];
        const float z = value[2];
        value[0] = x * a + y * d + z * g;
        value[1] = x * b + y * e + z * h;
        value[2] = x * c0 + y * f0 + z * i;
    };
    auto transform_normal = [&](float value[3]) {
        const float x = value[0];
        const float y = value[1];
        const float z = value[2];
        value[0] =
            x * inverse[0] + y * inverse[1] + z * inverse[2];
        value[1] =
            x * inverse[3] + y * inverse[4] + z * inverse[5];
        value[2] =
            x * inverse[6] + y * inverse[7] + z * inverse[8];
    };

    const float translation[3] = {
        matrix[12], matrix[13], matrix[14]
    };
    for (uint32_t vertex = 0; vertex < vertex_count; ++vertex) {
        float value[3]{};
        load_float3(vertex, *position, value);
        const float x = value[0];
        const float y = value[1];
        const float z = value[2];
        value[0] =
            x * a + y * d + z * g + translation[0];
        value[1] =
            x * b + y * e + z * h + translation[1];
        value[2] =
            x * c0 + y * f0 + z * i + translation[2];
        store_float3(vertex, *position, value);

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

    geometry.positions.resize(
        static_cast<size_t>(vertex_count) * 3u);
    for (uint32_t vertex = 0; vertex < vertex_count; ++vertex) {
        float value[3]{};
        load_float3(vertex, *position, value);
        std::memcpy(
            geometry.positions.data() +
                static_cast<size_t>(vertex) * 3u,
            value,
            3u * sizeof(float));
    }
    geometry.world_transform_applied = true;
    geometry.world_transform_mode =
        linear_identity
            ? "translation"
            : geometry.attributes.size() > 1u
                ? "affine-semantic-v3"
                : "affine-position-only-legacy";
}

PacketGeometry load_bundle_geometry(const std::string& root) {
    const std::string manifest = root + "/bundle_manifest.json";
    const std::string gate = root + "/native_submission_gate.json";
    const bool bmw_bundle = file_contains(
        manifest, "\"format\": \"SHIFT.BMWVulkanBundle/1\"");
    const bool neutral_bundle = file_contains(
        manifest, "\"format\": \"SHIFT.VulkanDrawBundle/1\"");
    if (!bmw_bundle && !neutral_bundle) {
        throw std::runtime_error(
            "bundle manifest is not a supported SHIFT Vulkan draw bundle");
    }
    if (neutral_bundle) {
        const std::string prepare =
            root + "/vulkan_draw_prepare.json";
        if (!file_contains(
                prepare,
                "\"format\": \"SHIFT.VulkanDrawBundlePrepare/1\"") ||
            !file_contains(prepare, "\"ready\": true")) {
            throw std::runtime_error(
                "neutral Vulkan draw prepare gate is missing or not ready");
        }
    }
    if (!file_contains(gate, "\"format\": \"SHIFT.NativeSubmissionGate/1\"") ||
        !file_contains(gate, "\"ready\": true") ||
        !file_contains(gate, "\"blocking_reasons\": []")) {
        throw std::runtime_error("native submission gate is missing or not ready");
    }

    const auto data = read_file_bytes(root + "/geometry.svpk");
    if (data.size() < sizeof(GeometryHeader)) {
        throw std::runtime_error("geometry packet truncated");
    }

    GeometryHeader header{};
    std::memcpy(&header, data.data(), sizeof(header));
    if (std::memcmp(header.magic, "SVGP", 4) != 0 ||
        (header.version != 1 &&
         header.version != 2 &&
         header.version != 3)) {
        throw std::runtime_error("unsupported SVGP geometry packet");
    }
    if (header.vertex_count == 0 || header.index_count == 0 ||
        header.stride == 0 || header.attribute_count == 0 ||
        header.attribute_count > 16 || header.index_count % 3 != 0) {
        throw std::runtime_error("invalid SVGP geometry header");
    }

    const size_t attribute_record_bytes =
        header.version >= 3
            ? sizeof(GeometryAttribute)
            : sizeof(LegacyGeometryAttribute);
    const size_t attributes_bytes =
        static_cast<size_t>(header.attribute_count) * attribute_record_bytes;
    const size_t vertices_bytes =
        static_cast<size_t>(header.vertex_count) * header.stride;
    const size_t indices_bytes =
        static_cast<size_t>(header.index_count) * sizeof(uint32_t);
    const size_t expected =
        sizeof(GeometryHeader) + attributes_bytes +
        vertices_bytes + indices_bytes;
    if (expected != data.size()) {
        throw std::runtime_error("SVGP geometry packet size mismatch");
    }

    std::vector<GeometryAttribute> attributes(header.attribute_count);
    if (header.version >= 3) {
        std::memcpy(
            attributes.data(),
            data.data() + sizeof(GeometryHeader),
            attributes_bytes);
    } else {
        for (uint32_t index = 0; index < header.attribute_count; ++index) {
            LegacyGeometryAttribute legacy{};
            std::memcpy(
                &legacy,
                data.data() + sizeof(GeometryHeader) +
                    static_cast<size_t>(index) * sizeof(LegacyGeometryAttribute),
                sizeof(legacy));
            attributes[index] = {
                legacy.location,
                legacy.format,
                legacy.offset,
                legacy.stride,
                legacy.location == 0u ? 200u : 0u,
            };
        }
    }

    if (header.version == 1) {
        if (header.attribute_count != 1 ||
            attributes[0].format != 1u) {
            throw std::runtime_error(
                "invalid version-1 SVGP geometry attribute");
        }
        // SVGP v1 used format code 1 for FLOAT3; v2/v3 reserve 1 for FLOAT2.
        attributes[0].format = 2u;
    }

    const GeometryAttribute* position = nullptr;
    for (const auto& attribute : attributes) {
        if (attribute.location == 0) {
            position = &attribute;
            break;
        }
    }
    if (!position || position->format != 2 ||
        position->property_id != 200u ||
        position->stride != header.stride ||
        position->offset + sizeof(float) * 3 > header.stride) {
        throw std::runtime_error(
            "SVGP POSITION0 is not FLOAT3 property 200");
    }
    if (header.version >= 3) {
        for (const auto& attribute : attributes) {
            if (attribute.property_id == 0u) {
                throw std::runtime_error(
                    "SVGP v3 attribute is missing SHIFT property identity");
            }
        }
    }

    const size_t vertex_base = sizeof(GeometryHeader) + attributes_bytes;
    const size_t index_base = vertex_base + vertices_bytes;

    PacketGeometry out;
    out.source = neutral_bundle
        ? "SHIFT.VulkanDrawBundle/1"
        : "SHIFT.BMWVulkanBundle/1";
    out.first_index = header.first_index;
    out.stride = header.stride;
    out.attributes = attributes;
    out.vertex_bytes.assign(
        data.begin() + static_cast<std::ptrdiff_t>(vertex_base),
        data.begin() + static_cast<std::ptrdiff_t>(index_base));
    out.positions.resize(static_cast<size_t>(header.vertex_count) * 3u);
    for (uint32_t vertex = 0; vertex < header.vertex_count; ++vertex) {
        const uint8_t* src =
            data.data() + vertex_base +
            static_cast<size_t>(vertex) * header.stride +
            position->offset;
        std::memcpy(
            out.positions.data() + static_cast<size_t>(vertex) * 3u,
            src, sizeof(float) * 3u);
    }

    out.indices.resize(header.index_count);
    std::memcpy(
        out.indices.data(), data.data() + index_base, indices_bytes);
    for (uint32_t index : out.indices) {
        if (index >= header.vertex_count) {
            throw std::runtime_error("SVGP index out of range");
        }
    }
    apply_bundle_world_transform(root, out);
    return out;
}


std::vector<std::string> load_bundle_set_paths(
    const std::string& root,
    bool native_scene_set) {
    const std::filesystem::path base(root);
    const std::string manifest =
        (base / "bundle_set_manifest.json").string();
    const std::string prepare =
        (base / "bundle_set_prepare.json").string();
    const std::filesystem::path order_path =
        base / "bundle_set.paths";

    const std::string set_format =
        native_scene_set
            ? "\"format\": \"SHIFT.NativeSceneVulkanSet/1\""
            : "\"format\": \"SHIFT.BMWVulkanBundleSet/1\"";
    const std::string prepare_format =
        native_scene_set
            ? "\"format\": \"SHIFT.NativeSceneVulkanSetPrepare/1\""
            : "\"format\": \"SHIFT.BMWVulkanBundleSetPrepare/1\"";
    if (!file_contains(manifest, set_format) ||
        !file_contains(manifest, "\"ready\": true")) {
        throw std::runtime_error(
            "bundle set manifest is missing or not ready");
    }
    if (!file_contains(prepare, prepare_format) ||
        !file_contains(prepare, "\"ready\": true")) {
        throw std::runtime_error(
            "bundle set prepare gate is missing or not ready");
    }

    const uint32_t expected =
        json_u32_field(manifest, "draw_count");
    const uint32_t prepared =
        json_u32_field(prepare, "draw_count");
    if (expected == 0 || prepared != expected) {
        throw std::runtime_error(
            "bundle set draw count is empty or inconsistent");
    }

    std::ifstream order(order_path);
    if (!order) {
        throw std::runtime_error(
            "bundle set draw-order sidecar is missing");
    }

    std::vector<std::string> result;
    std::string line;
    while (std::getline(order, line)) {
        while (!line.empty() &&
               (line.back() == '\r' ||
                std::isspace(static_cast<unsigned char>(line.back())))) {
            line.pop_back();
        }
        size_t begin = 0;
        while (begin < line.size() &&
               std::isspace(static_cast<unsigned char>(line[begin]))) {
            ++begin;
        }
        line = line.substr(begin);
        if (line.empty()) continue;

        const std::filesystem::path relative(line);
        if (relative.is_absolute()) {
            throw std::runtime_error(
                "bundle set contains an absolute child path");
        }
        for (const auto& part : relative) {
            if (part == "..") {
                throw std::runtime_error(
                    "bundle set child path escapes its root");
            }
        }

        const std::filesystem::path child =
            (base / relative).lexically_normal();
        if (!std::filesystem::is_regular_file(
                child / "bundle_manifest.json")) {
            throw std::runtime_error(
                "bundle set child manifest is missing: " +
                relative.string());
        }
        result.push_back(child.string());
    }

    if (result.size() != expected) {
        throw std::runtime_error(
            "bundle set draw-order count does not match manifest");
    }
    return result;
}

struct InputState {
    bool throttle = false;
    bool brake = false;
    bool steer_left = false;
    bool steer_right = false;
};

struct InputScript {
    static constexpr const char* format =
        "SHIFT.NativeRuntimeInputScript/1";
    std::vector<InputState> steps;
};

InputScript load_input_script(const std::string& path) {
    std::ifstream file(path);
    if (!file) {
        throw std::runtime_error(
            "cannot open native input script: " + path);
    }

    InputScript script{};
    bool header_seen = false;
    std::string line;
    uint64_t line_number = 0;
    while (std::getline(file, line)) {
        ++line_number;
        const size_t first =
            line.find_first_not_of(" \t\r\n");
        if (first == std::string::npos ||
            line[first] == '#') {
            continue;
        }
        const size_t last =
            line.find_last_not_of(" \t\r\n");
        const std::string trimmed =
            line.substr(first, last - first + 1);

        if (!header_seen) {
            if (trimmed != InputScript::format) {
                throw std::runtime_error(
                    "native input script header is not "
                    "SHIFT.NativeRuntimeInputScript/1");
            }
            header_seen = true;
            continue;
        }

        std::istringstream row(trimmed);
        uint64_t step = 0;
        int throttle = 0;
        int brake = 0;
        int steer_left = 0;
        int steer_right = 0;
        std::string extra;
        if (!(row >> step >> throttle >> brake >>
              steer_left >> steer_right) ||
            (row >> extra)) {
            throw std::runtime_error(
                "native input script row is malformed at line " +
                std::to_string(line_number));
        }
        if (step != script.steps.size()) {
            throw std::runtime_error(
                "native input script steps must be contiguous from zero");
        }
        auto valid_bit = [](int value) {
            return value == 0 || value == 1;
        };
        if (!valid_bit(throttle) ||
            !valid_bit(brake) ||
            !valid_bit(steer_left) ||
            !valid_bit(steer_right)) {
            throw std::runtime_error(
                "native input script controls must be 0 or 1");
        }

        InputState state{};
        state.throttle = throttle != 0;
        state.brake = brake != 0;
        state.steer_left = steer_left != 0;
        state.steer_right = steer_right != 0;
        script.steps.push_back(state);
    }

    if (!header_seen) {
        throw std::runtime_error(
            "native input script header is missing");
    }
    if (script.steps.empty()) {
        throw std::runtime_error(
            "native input script contains no fixed-step rows");
    }
    return script;
}


struct Window {
    xcb_connection_t* connection = nullptr;
    xcb_window_t window = XCB_WINDOW_NONE;
    uint32_t width = kWindowWidth;
    uint32_t height = kWindowHeight;

    void create() {
        int screen_index = 0;
        connection = xcb_connect(nullptr, &screen_index);
        if (!connection || xcb_connection_has_error(connection)) {
            throw std::runtime_error("cannot connect to X11");
        }

        const xcb_setup_t* setup = xcb_get_setup(connection);
        auto screen_it = xcb_setup_roots_iterator(setup);
        for (int i = 0; i < screen_index && screen_it.rem; ++i) {
            xcb_screen_next(&screen_it);
        }
        if (!screen_it.rem) {
            throw std::runtime_error("cannot find X11 screen");
        }

        const xcb_screen_t* screen = screen_it.data;
        window = xcb_generate_id(connection);

        const uint32_t event_mask =
            XCB_EVENT_MASK_EXPOSURE |
            XCB_EVENT_MASK_STRUCTURE_NOTIFY |
            XCB_EVENT_MASK_KEY_PRESS |
            XCB_EVENT_MASK_KEY_RELEASE;

        const uint32_t values[] = {
            screen->black_pixel,
            event_mask
        };

        xcb_create_window(
            connection,
            XCB_COPY_FROM_PARENT,
            window,
            screen->root,
            0, 0,
            kWindowWidth, kWindowHeight,
            0,
            XCB_WINDOW_CLASS_INPUT_OUTPUT,
            screen->root_visual,
            XCB_CW_BACK_PIXEL | XCB_CW_EVENT_MASK,
            values);

        const char title[] = "SHIFT Linux Test Runtime";
        xcb_change_property(
            connection,
            XCB_PROP_MODE_REPLACE,
            window,
            XCB_ATOM_WM_NAME,
            XCB_ATOM_STRING,
            8,
            static_cast<uint32_t>(sizeof(title) - 1),
            title);

        xcb_map_window(connection, window);
        xcb_flush(connection);
    }

    void resize(uint32_t requested_width, uint32_t requested_height) {
        if (!connection || window == XCB_WINDOW_NONE ||
            requested_width == 0 || requested_height == 0 ||
            requested_width > UINT16_MAX || requested_height > UINT16_MAX) {
            throw std::runtime_error("invalid guest D3D9 window size");
        }
        const uint32_t values[] = {requested_width, requested_height};
        xcb_configure_window(
            connection, window,
            XCB_CONFIG_WINDOW_WIDTH | XCB_CONFIG_WINDOW_HEIGHT, values);
        xcb_flush(connection);
        width = requested_width;
        height = requested_height;
    }

    void poll(bool& quit, InputState& input, std::string& quit_reason,
              shift::runtime::RecompiledPcodeModule* guest_module = nullptr) {
        while (xcb_generic_event_t* raw = xcb_poll_for_event(connection)) {
            const uint8_t type = raw->response_type & 0x7f;
            if (type == XCB_KEY_PRESS || type == XCB_KEY_RELEASE) {
                const auto* event =
                    reinterpret_cast<const xcb_key_press_event_t*>(raw);
                const bool pressed = type == XCB_KEY_PRESS;
                uint32_t virtual_key = 0;
                uint32_t scan_code = 0;
                bool extended = false;
                switch (event->detail) {
                    case 9: virtual_key = 0x1b; scan_code = 0x01; break;
                    case 24: virtual_key = 'Q'; scan_code = 0x10; break;
                    case 111:
                        virtual_key = 0x26;
                        scan_code = 0x48;
                        extended = true;
                        break;
                    case 25: virtual_key = 'W'; scan_code = 0x11; break;
                    case 116:
                        virtual_key = 0x28;
                        scan_code = 0x50;
                        extended = true;
                        break;
                    case 39: virtual_key = 'S'; scan_code = 0x1f; break;
                    case 113:
                        virtual_key = 0x25;
                        scan_code = 0x4b;
                        extended = true;
                        break;
                    case 38: virtual_key = 'A'; scan_code = 0x1e; break;
                    case 114:
                        virtual_key = 0x27;
                        scan_code = 0x4d;
                        extended = true;
                        break;
                    case 40: virtual_key = 'D'; scan_code = 0x20; break;
                    case 36: virtual_key = 0x0d; scan_code = 0x1c; break;
                    case 65: virtual_key = 0x20; scan_code = 0x39; break;
                    case 22: virtual_key = 0x08; scan_code = 0x0e; break;
                    case 23: virtual_key = 0x09; scan_code = 0x0f; break;
                    default: break;
                }
                if (guest_module && virtual_key != 0) {
                    uint32_t message = pressed ? 0x0100 : 0x0101;
                    uint32_t key_data = 1 | (scan_code << 16);
                    if (extended) key_data |= 1u << 24;
                    if (!pressed) key_data |= (1u << 30) | (1u << 31);
                    guest_module->post_guest_window_message(
                        message, virtual_key, key_data);
                }
                switch (event->detail) {
                    case 9:
                        if (pressed && !guest_module) {
                            quit = true;
                            quit_reason = "escape_key";
                        }
                        break;
                    case 24:
                        if (pressed && !guest_module) {
                            quit = true;
                            quit_reason = "q_key";
                        }
                        break;
                    case 111:
                    case 25:
                        input.throttle = pressed;
                        break;
                    case 116:
                    case 39:
                        input.brake = pressed;
                        break;
                    case 113:
                    case 38:
                        input.steer_left = pressed;
                        break;
                    case 114:
                    case 40:
                        input.steer_right = pressed;
                        break;
                    default:
                        break;
                }
            } else if (type == XCB_DESTROY_NOTIFY) {
                quit = true;
                quit_reason = "window_destroyed";
            }
            std::free(raw);
        }
    }

    void destroy() {
        if (!connection) return;
        if (window != XCB_WINDOW_NONE) {
            xcb_destroy_window(connection, window);
        }
        xcb_disconnect(connection);
        connection = nullptr;
        window = XCB_WINDOW_NONE;
    }
};

struct Buffer {
    VkDevice device = VK_NULL_HANDLE;
    VkBuffer handle = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;

    void destroy() {
        if (device != VK_NULL_HANDLE) {
            if (handle) vkDestroyBuffer(device, handle, nullptr);
            if (memory) vkFreeMemory(device, memory, nullptr);
        }
        device = VK_NULL_HANDLE;
        handle = VK_NULL_HANDLE;
        memory = VK_NULL_HANDLE;
    }
};

struct Image {
    VkDevice device = VK_NULL_HANDLE;
    VkImage handle = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
    VkImageView view = VK_NULL_HANDLE;
    uint32_t layers = 1;

    void destroy() {
        if (device != VK_NULL_HANDLE) {
            if (view) vkDestroyImageView(device, view, nullptr);
            if (handle) vkDestroyImage(device, handle, nullptr);
            if (memory) vkFreeMemory(device, memory, nullptr);
        }
        device = VK_NULL_HANDLE;
        handle = VK_NULL_HANDLE;
        memory = VK_NULL_HANDLE;
        view = VK_NULL_HANDLE;
        layers = 1;
    }
};


struct MaterialDraw {
    Buffer vertex_buffer;
    Buffer index_buffer;
    uint32_t index_count = 0;
    uint32_t first_index = 0;

    Buffer vertex_constants;
    Buffer pixel_constants;
    std::vector<Buffer> texture_staging;
    std::vector<Image> texture_images;
    std::vector<VkSampler> texture_samplers;
    Image cube_image;
    Buffer cube_staging;
    VkSampler cube_sampler = VK_NULL_HANDLE;

    VkDescriptorSetLayout set0_layout = VK_NULL_HANDLE;
    VkDescriptorSetLayout set1_layout = VK_NULL_HANDLE;
    VkDescriptorPool descriptor_pool = VK_NULL_HANDLE;
    VkDescriptorSet set0 = VK_NULL_HANDLE;
    VkDescriptorSet set1 = VK_NULL_HANDLE;

    VkPipelineLayout pipeline_layout = VK_NULL_HANDLE;
    VkPipeline pipeline = VK_NULL_HANDLE;
    VkShaderModule vertex_shader = VK_NULL_HANDLE;
    VkShaderModule fragment_shader = VK_NULL_HANDLE;

    void destroy(VkDevice device) {
        if (pipeline) vkDestroyPipeline(device, pipeline, nullptr);
        if (pipeline_layout) vkDestroyPipelineLayout(device, pipeline_layout, nullptr);
        if (descriptor_pool) vkDestroyDescriptorPool(device, descriptor_pool, nullptr);
        if (set1_layout) vkDestroyDescriptorSetLayout(device, set1_layout, nullptr);
        if (set0_layout) vkDestroyDescriptorSetLayout(device, set0_layout, nullptr);
        if (vertex_shader) vkDestroyShaderModule(device, vertex_shader, nullptr);
        if (fragment_shader) vkDestroyShaderModule(device, fragment_shader, nullptr);

        for (VkSampler sampler : texture_samplers) {
            if (sampler) vkDestroySampler(device, sampler, nullptr);
        }
        texture_samplers.clear();
        if (cube_sampler) vkDestroySampler(device, cube_sampler, nullptr);
        cube_sampler = VK_NULL_HANDLE;

        for (auto& image : texture_images) image.destroy();
        texture_images.clear();
        cube_image.destroy();

        for (auto& staging : texture_staging) staging.destroy();
        texture_staging.clear();
        cube_staging.destroy();
        vertex_constants.destroy();
        pixel_constants.destroy();
        vertex_buffer.destroy();
        index_buffer.destroy();

        set0_layout = VK_NULL_HANDLE;
        set1_layout = VK_NULL_HANDLE;
        descriptor_pool = VK_NULL_HANDLE;
        set0 = VK_NULL_HANDLE;
        set1 = VK_NULL_HANDLE;
        pipeline_layout = VK_NULL_HANDLE;
        pipeline = VK_NULL_HANDLE;
        vertex_shader = VK_NULL_HANDLE;
        fragment_shader = VK_NULL_HANDLE;
        first_index = 0;
        index_count = 0;
    }
};

struct Runtime {
    Window* window = nullptr;
    shift::vulkan::Validation validation;

    VkInstance instance = VK_NULL_HANDLE;
    VkSurfaceKHR surface = VK_NULL_HANDLE;
    VkPhysicalDevice physical = VK_NULL_HANDLE;
    VkPhysicalDeviceProperties physical_properties{};
    VkPhysicalDeviceFeatures physical_features{};
    VkDevice device = VK_NULL_HANDLE;
    VkQueue graphics_queue = VK_NULL_HANDLE;
    VkQueue present_queue = VK_NULL_HANDLE;
    uint32_t graphics_family = 0;
    uint32_t present_family = 0;

    VkSwapchainKHR swapchain = VK_NULL_HANDLE;
    VkFormat swapchain_format = VK_FORMAT_UNDEFINED;
    VkFormat depth_format = VK_FORMAT_D32_SFLOAT;
    VkSampleCountFlagBits guest_sample_count = VK_SAMPLE_COUNT_1_BIT;
    VkExtent2D swapchain_extent{};
    std::vector<VkImage> swapchain_images;
    std::vector<VkImageView> swapchain_views;
    std::vector<Image> multisample_color_images;
    std::vector<Image> depth_images;
    std::unordered_map<uint32_t, Image> guest_texture_images;
    std::unordered_map<uint32_t, Buffer> guest_vertex_buffers;
    std::unordered_map<uint32_t, uint32_t> guest_vertex_buffer_sizes;
    std::unordered_map<uint32_t, Buffer> guest_index_buffers;
    std::unordered_map<uint32_t, uint32_t> guest_index_buffer_sizes;
    bool guest_d3d9_device_bound = false;
    uint32_t guest_d3d9_focus_window = 0;
    uint32_t guest_d3d9_behavior_flags = 0;
    shift::runtime::RecompiledGuestD3d9PresentationParameters
        guest_d3d9_presentation{};
    uint64_t guest_d3d9_clear_request_count = 0;
    uint64_t guest_d3d9_present_request_count = 0;
    uint64_t guest_d3d9_vulkan_clear_submission_count = 0;
    uint64_t guest_d3d9_vulkan_present_submission_count = 0;
    uint32_t guest_d3d9_clear_color = 0;
    uint32_t guest_d3d9_clear_depth_bits = 0;
    uint32_t guest_d3d9_clear_stencil = 0;
    std::unique_ptr<shift::vulkan::D3d9PacketCaptureAdapter>
        guest_d3d9_packet_capture;

    VkRenderPass render_pass = VK_NULL_HANDLE;
    VkPipelineLayout pipeline_layout = VK_NULL_HANDLE;
    VkPipeline pipeline = VK_NULL_HANDLE;
    VkShaderModule vertex_shader = VK_NULL_HANDLE;
    VkShaderModule fragment_shader = VK_NULL_HANDLE;
    std::vector<VkFramebuffer> framebuffers;

    VkCommandPool command_pool = VK_NULL_HANDLE;
    std::vector<VkCommandBuffer> command_buffers;

    std::array<VkSemaphore, kFramesInFlight> image_available{};
    // Presentation completion follows the acquired image, not the frame fence.
    std::vector<VkSemaphore> render_finished;
    std::array<VkFence, kFramesInFlight> fences{};
    size_t frame_slot = 0;
    std::string frame_stop_reason;

    Buffer vertex_buffer;
    Buffer index_buffer;
    uint32_t index_count = 0;
    uint32_t first_index = 0;

    bool material_mode = false;
    std::vector<MaterialDraw> material_draws;

    shift::runtime::RecompiledGuestD3d9AdapterInfo
    recompiled_d3d9_adapter_info() {
        shift::runtime::RecompiledGuestD3d9AdapterInfo adapter_info{};
        auto& caps = adapter_info.caps;
        caps[0] = 1;  // D3DDEVTYPE_HAL: this Vulkan physical device.
        caps[22] = physical_properties.limits.maxImageDimension2D;
        caps[23] = physical_properties.limits.maxImageDimension2D;
        caps[24] = physical_properties.limits.maxImageDimension3D;
        caps[27] = physical_features.samplerAnisotropy
                       ? static_cast<uint32_t>(std::floor(
                             physical_properties.limits.maxSamplerAnisotropy))
                       : 1;
        const float max_point_size = physical_features.largePoints
                                         ? physical_properties.limits
                                               .pointSizeRange[1]
                                         : 1.0f;
        std::memcpy(&caps[44], &max_point_size, sizeof(max_point_size));
        caps[47] = physical_properties.limits.maxVertexInputBindings;
        caps[48] = physical_properties.limits.maxVertexInputBindingStride;
        caps[60] = physical_properties.limits.maxColorAttachments;
        adapter_info.vendor_id = physical_properties.vendorID;
        adapter_info.device_id = physical_properties.deviceID;
        adapter_info.description = physical_properties.deviceName;
        adapter_info.bgra8_sample_count_mask = image_sample_count_mask(
            VK_FORMAT_B8G8R8A8_UNORM,
            VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT);
        adapter_info.d24s8_sample_count_mask = image_sample_count_mask(
            VK_FORMAT_D24_UNORM_S8_UINT,
            VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT);
        adapter_info.backend_context = const_cast<Runtime*>(this);
        adapter_info.create_device =
            &Runtime::create_guest_d3d9_device_callback;
        adapter_info.create_texture =
            &Runtime::create_guest_d3d9_texture_callback;
        adapter_info.release_texture =
            &Runtime::release_guest_d3d9_texture_callback;
        adapter_info.create_vertex_buffer =
            &Runtime::create_guest_d3d9_vertex_buffer_callback;
        adapter_info.update_vertex_buffer =
            &Runtime::update_guest_d3d9_vertex_buffer_callback;
        adapter_info.release_vertex_buffer =
            &Runtime::release_guest_d3d9_vertex_buffer_callback;
        adapter_info.create_index_buffer =
            &Runtime::create_guest_d3d9_index_buffer_callback;
        adapter_info.update_index_buffer =
            &Runtime::update_guest_d3d9_index_buffer_callback;
        adapter_info.release_index_buffer =
            &Runtime::release_guest_d3d9_index_buffer_callback;
        adapter_info.clear = &Runtime::clear_guest_d3d9_callback;
        adapter_info.present = &Runtime::present_guest_d3d9_callback;
        uint32_t surface_format_count = 0;
        vk_check(vkGetPhysicalDeviceSurfaceFormatsKHR(
                     physical, surface, &surface_format_count, nullptr),
                 "surface formats failed while building D3D9 capabilities");
        std::vector<VkSurfaceFormatKHR> surface_formats(surface_format_count);
        if (!surface_formats.empty()) {
            vk_check(vkGetPhysicalDeviceSurfaceFormatsKHR(
                         physical, surface, &surface_format_count,
                         surface_formats.data()),
                     "surface formats failed while building D3D9 capabilities");
        }
        const bool bgra8_presentable = std::any_of(
            surface_formats.begin(), surface_formats.end(),
            [](const VkSurfaceFormatKHR& format) {
                return format.format == VK_FORMAT_B8G8R8A8_UNORM &&
                       format.colorSpace ==
                           VK_COLOR_SPACE_SRGB_NONLINEAR_KHR;
            });
        VkFormatProperties bgra8_properties{};
        vkGetPhysicalDeviceFormatProperties(
            physical, VK_FORMAT_B8G8R8A8_UNORM, &bgra8_properties);
        adapter_info.supports_bgra8_texture =
            (bgra8_properties.optimalTilingFeatures &
             VK_FORMAT_FEATURE_SAMPLED_IMAGE_BIT) != 0;
        adapter_info.supports_bgra8_surface =
            bgra8_presentable &&
            (bgra8_properties.optimalTilingFeatures &
             VK_FORMAT_FEATURE_COLOR_ATTACHMENT_BIT) != 0;
        VkFormatProperties d24s8_properties{};
        vkGetPhysicalDeviceFormatProperties(
            physical, VK_FORMAT_D24_UNORM_S8_UINT, &d24s8_properties);
        adapter_info.supports_d24s8_depth_stencil =
            (d24s8_properties.optimalTilingFeatures &
             VK_FORMAT_FEATURE_DEPTH_STENCIL_ATTACHMENT_BIT) != 0;
        const char* capture_dir =
            std::getenv("SHIFT_D3D9_PACKET_CAPTURE_DIR");
        if (capture_dir != nullptr && capture_dir[0] != '\0') {
            guest_d3d9_packet_capture =
                std::make_unique<shift::vulkan::D3d9PacketCaptureAdapter>(
                    capture_dir);
            std::string error;
            if (!guest_d3d9_packet_capture->install(adapter_info, error)) {
                guest_d3d9_packet_capture.reset();
                throw std::runtime_error(
                    "could not install D3D9 packet capture: " + error);
            }
        }
        return adapter_info;
    }

    static bool create_guest_d3d9_device_callback(
        void* context, uint32_t focus_window, uint32_t behavior_flags,
        shift::runtime::RecompiledGuestD3d9PresentationParameters& parameters,
        std::string& error) {
        auto* runtime = static_cast<Runtime*>(context);
        return runtime && runtime->create_guest_d3d9_device(
                              focus_window, behavior_flags, parameters,
                              error);
    }

    static bool clear_guest_d3d9_callback(
        void* context, uint32_t flags, uint32_t color, uint32_t depth_bits,
        uint32_t stencil, uint32_t rect_count, std::string& error) {
        auto* runtime = static_cast<Runtime*>(context);
        return runtime && runtime->queue_guest_d3d9_clear(
                              flags, color, depth_bits, stencil, rect_count,
                              error);
    }

    static bool present_guest_d3d9_callback(void* context,
                                             std::string& error) {
        auto* runtime = static_cast<Runtime*>(context);
        return runtime && runtime->queue_guest_d3d9_present(error);
    }

    bool queue_guest_d3d9_clear(uint32_t flags, uint32_t color,
                                uint32_t depth_bits, uint32_t stencil,
                                uint32_t rect_count, std::string& error) {
        constexpr uint32_t full_color_depth_stencil_clear = 0x7;
        if (flags != full_color_depth_stencil_clear || rect_count != 0) {
            error = "only a full color/depth/stencil clear is supported";
            return false;
        }
        float depth = 0.0f;
        std::memcpy(&depth, &depth_bits, sizeof(depth));
        if (!std::isfinite(depth) || depth < 0.0f || depth > 1.0f) {
            error = "D3D9 clear depth is outside [0, 1]";
            return false;
        }
        if (guest_d3d9_clear_request_count == UINT64_MAX) {
            error = "D3D9 clear request counter is exhausted";
            return false;
        }
        guest_d3d9_clear_color = color;
        guest_d3d9_clear_depth_bits = depth_bits;
        guest_d3d9_clear_stencil = stencil;
        ++guest_d3d9_clear_request_count;
        return true;
    }

    bool queue_guest_d3d9_present(std::string& error) {
        if (guest_d3d9_present_request_count == UINT64_MAX) {
            error = "D3D9 present request counter is exhausted";
            return false;
        }
        ++guest_d3d9_present_request_count;
        return true;
    }

    static bool create_guest_d3d9_texture_callback(
        void* context, uint32_t guest_texture, uint32_t guest_device,
        uint32_t width, uint32_t height, uint32_t levels, uint32_t usage,
        uint32_t format, uint32_t pool, std::string& error) {
        auto* runtime = static_cast<Runtime*>(context);
        return runtime && runtime->create_guest_d3d9_texture(
                              guest_texture, guest_device, width, height,
                              levels, usage, format, pool, error);
    }

    static void release_guest_d3d9_texture_callback(void* context,
                                                   uint32_t guest_texture) {
        auto* runtime = static_cast<Runtime*>(context);
        if (!runtime) return;
        const auto image = runtime->guest_texture_images.find(guest_texture);
        if (image == runtime->guest_texture_images.end()) return;
        image->second.destroy();
        runtime->guest_texture_images.erase(image);
    }

    bool create_guest_d3d9_texture(
        uint32_t guest_texture, uint32_t guest_device, uint32_t width,
        uint32_t height, uint32_t levels, uint32_t usage, uint32_t format,
        uint32_t pool, std::string& error) {
        if (!guest_d3d9_device_bound || guest_texture == 0 ||
            guest_device == 0 || width == 0 || height == 0 || levels != 1 ||
            usage != 1 || format != 21 || pool != 0) {
            error = "unsupported retail D3D9 texture description";
            return false;
        }
        if (guest_texture_images.find(guest_texture) !=
            guest_texture_images.end()) {
            error = "guest D3D9 texture address is already allocated";
            return false;
        }
        constexpr VkFormat vk_format = VK_FORMAT_B8G8R8A8_UNORM;
        constexpr VkImageUsageFlags image_usage =
            VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT |
            VK_IMAGE_USAGE_TRANSFER_SRC_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT;
        VkFormatProperties format_properties{};
        vkGetPhysicalDeviceFormatProperties(physical, vk_format,
                                            &format_properties);
        const VkFormatFeatureFlags required_features =
            VK_FORMAT_FEATURE_SAMPLED_IMAGE_BIT |
            VK_FORMAT_FEATURE_COLOR_ATTACHMENT_BIT |
            VK_FORMAT_FEATURE_TRANSFER_SRC_BIT |
            VK_FORMAT_FEATURE_TRANSFER_DST_BIT;
        if ((format_properties.optimalTilingFeatures & required_features) !=
            required_features) {
            error = "Vulkan BGRA8 texture format lacks required features";
            return false;
        }
        VkImageFormatProperties image_properties{};
        const VkResult support = vkGetPhysicalDeviceImageFormatProperties(
            physical, vk_format, VK_IMAGE_TYPE_2D, VK_IMAGE_TILING_OPTIMAL,
            image_usage, 0, &image_properties);
        if (support != VK_SUCCESS ||
            width > image_properties.maxExtent.width ||
            height > image_properties.maxExtent.height) {
            error = "Vulkan cannot allocate the requested BGRA8 texture";
            return false;
        }
        Image image;
        try {
            create_image(width, height, 1, vk_format, 0, image_usage,
                         VK_IMAGE_ASPECT_COLOR_BIT, image);
        } catch (const std::exception& exception) {
            image.destroy();
            error = exception.what();
            return false;
        }
        const auto [inserted_image, inserted] =
            guest_texture_images.emplace(guest_texture, std::move(image));
        if (!inserted) {
            image.destroy();
            error = "guest D3D9 texture was concurrently allocated";
            return false;
        }
        (void)inserted_image;
        const char* trace = std::getenv("SHIFT_TRACE_D3D9_RESOURCES");
        if (!trace || !*trace) trace = std::getenv("SHIFT_TRACE_D3D9_TEXTURES");
        if (trace && *trace) {
            std::fprintf(stderr,
                         "shift_runtime: guest D3D9 Vulkan image created "
                         "texture=0x%08x device=0x%08x extent=%ux%u "
                         "format=%u levels=%u usage=0x%x pool=%u\n",
                         guest_texture, guest_device, width, height, format,
                         levels, usage, pool);
        }
        return true;
    }

    static bool create_guest_d3d9_vertex_buffer_callback(
        void* context, uint32_t guest_buffer, uint32_t guest_device,
        uint32_t size, uint32_t usage, uint32_t fvf, uint32_t pool,
        std::string& error) {
        auto* runtime = static_cast<Runtime*>(context);
        return runtime && runtime->create_guest_d3d9_vertex_buffer(
                              guest_buffer, guest_device, size, usage, fvf,
                              pool, error);
    }

    static bool update_guest_d3d9_vertex_buffer_callback(
        void* context, uint32_t guest_buffer, uint32_t offset,
        const uint8_t* data, size_t size, std::string& error) {
        auto* runtime = static_cast<Runtime*>(context);
        return runtime && runtime->update_guest_d3d9_vertex_buffer(
                              guest_buffer, offset, data, size, error);
    }

    static void release_guest_d3d9_vertex_buffer_callback(
        void* context, uint32_t guest_buffer) {
        auto* runtime = static_cast<Runtime*>(context);
        if (!runtime) return;
        const auto buffer = runtime->guest_vertex_buffers.find(guest_buffer);
        if (buffer == runtime->guest_vertex_buffers.end()) return;
        buffer->second.destroy();
        runtime->guest_vertex_buffers.erase(buffer);
        runtime->guest_vertex_buffer_sizes.erase(guest_buffer);
    }

    static bool create_guest_d3d9_index_buffer_callback(
        void* context, uint32_t guest_buffer, uint32_t guest_device,
        uint32_t size, uint32_t usage, uint32_t format, uint32_t pool,
        std::string& error) {
        auto* runtime = static_cast<Runtime*>(context);
        return runtime && runtime->create_guest_d3d9_index_buffer(
                              guest_buffer, guest_device, size, usage, format,
                              pool, error);
    }

    static bool update_guest_d3d9_index_buffer_callback(
        void* context, uint32_t guest_buffer, uint32_t offset,
        const uint8_t* data, size_t size, std::string& error) {
        auto* runtime = static_cast<Runtime*>(context);
        return runtime && runtime->update_guest_d3d9_index_buffer(
                              guest_buffer, offset, data, size, error);
    }

    static void release_guest_d3d9_index_buffer_callback(
        void* context, uint32_t guest_buffer) {
        auto* runtime = static_cast<Runtime*>(context);
        if (!runtime) return;
        const auto buffer = runtime->guest_index_buffers.find(guest_buffer);
        if (buffer == runtime->guest_index_buffers.end()) return;
        buffer->second.destroy();
        runtime->guest_index_buffers.erase(buffer);
        runtime->guest_index_buffer_sizes.erase(guest_buffer);
    }

    bool create_guest_d3d9_vertex_buffer(
        uint32_t guest_buffer, uint32_t guest_device, uint32_t size,
        uint32_t usage, uint32_t fvf, uint32_t pool, std::string& error) {
        if (!guest_d3d9_device_bound || guest_buffer == 0 || guest_device == 0 ||
            size == 0 || (pool != 0 && pool != 1) ||
            (pool == 1 && (usage & 0x200) != 0)) {
            error = "unsupported retail D3D9 vertex buffer description";
            return false;
        }
        if (guest_vertex_buffers.find(guest_buffer) !=
            guest_vertex_buffers.end()) {
            error = "guest D3D9 vertex buffer address is already allocated";
            return false;
        }
        Buffer buffer;
        try {
            create_buffer(nullptr, size,
                          VK_BUFFER_USAGE_VERTEX_BUFFER_BIT |
                              VK_BUFFER_USAGE_TRANSFER_SRC_BIT |
                              VK_BUFFER_USAGE_TRANSFER_DST_BIT,
                          buffer);
        } catch (const std::exception& exception) {
            buffer.destroy();
            error = exception.what();
            return false;
        }
        const auto [inserted_buffer, inserted] =
            guest_vertex_buffers.emplace(guest_buffer, std::move(buffer));
        if (!inserted) {
            buffer.destroy();
            error = "guest D3D9 vertex buffer was concurrently allocated";
            return false;
        }
        guest_vertex_buffer_sizes.emplace(guest_buffer, size);
        (void)inserted_buffer;
        const char* trace = std::getenv("SHIFT_TRACE_D3D9_RESOURCES");
        if (trace && *trace) {
            std::fprintf(stderr,
                         "shift_runtime: guest D3D9 Vulkan vertex buffer "
                         "created buffer=0x%08x device=0x%08x size=%u "
                         "usage=0x%x fvf=0x%x pool=%u\n",
                         guest_buffer, guest_device, size, usage, fvf, pool);
        }
        return true;
    }

    bool update_guest_d3d9_vertex_buffer(
        uint32_t guest_buffer, uint32_t offset, const uint8_t* data,
        size_t size, std::string& error) {
        const auto buffer = guest_vertex_buffers.find(guest_buffer);
        const auto buffer_size = guest_vertex_buffer_sizes.find(guest_buffer);
        if (buffer == guest_vertex_buffers.end() ||
            buffer_size == guest_vertex_buffer_sizes.end() || !data || size == 0 ||
            offset > buffer_size->second || size > buffer_size->second - offset) {
            error = "invalid guest D3D9 vertex buffer update";
            return false;
        }
        void* mapped = nullptr;
        const VkResult map_result = vkMapMemory(
            device, buffer->second.memory, 0, VK_WHOLE_SIZE, 0, &mapped);
        if (map_result != VK_SUCCESS) {
            error = "could not map guest D3D9 vertex buffer memory";
            return false;
        }
        std::memcpy(static_cast<uint8_t*>(mapped) + offset, data, size);
        vkUnmapMemory(device, buffer->second.memory);
        const char* trace = std::getenv("SHIFT_TRACE_D3D9_RESOURCES");
        if (trace && *trace) {
            std::fprintf(stderr,
                         "shift_runtime: guest D3D9 vertex buffer updated "
                         "buffer=0x%08x offset=%u size=%zu\n",
                         guest_buffer, offset, size);
        }
        return true;
    }

    bool create_guest_d3d9_index_buffer(
        uint32_t guest_buffer, uint32_t guest_device, uint32_t size,
        uint32_t usage, uint32_t format, uint32_t pool, std::string& error) {
        if (!guest_d3d9_device_bound || guest_buffer == 0 || guest_device == 0 ||
            size == 0 || (format != 101 && format != 102) ||
            (pool != 0 && pool != 1) ||
            (pool == 1 && (usage & 0x200) != 0)) {
            error = "unsupported retail D3D9 index buffer description";
            return false;
        }
        if (guest_index_buffers.find(guest_buffer) !=
            guest_index_buffers.end()) {
            error = "guest D3D9 index buffer address is already allocated";
            return false;
        }
        Buffer buffer;
        try {
            create_buffer(nullptr, size,
                          VK_BUFFER_USAGE_INDEX_BUFFER_BIT |
                              VK_BUFFER_USAGE_TRANSFER_SRC_BIT |
                              VK_BUFFER_USAGE_TRANSFER_DST_BIT,
                          buffer);
        } catch (const std::exception& exception) {
            buffer.destroy();
            error = exception.what();
            return false;
        }
        const auto [inserted_buffer, inserted] =
            guest_index_buffers.emplace(guest_buffer, std::move(buffer));
        if (!inserted) {
            buffer.destroy();
            error = "guest D3D9 index buffer was concurrently allocated";
            return false;
        }
        guest_index_buffer_sizes.emplace(guest_buffer, size);
        (void)inserted_buffer;
        const char* trace = std::getenv("SHIFT_TRACE_D3D9_RESOURCES");
        if (trace && *trace) {
            std::fprintf(stderr,
                         "shift_runtime: guest D3D9 Vulkan index buffer "
                         "created buffer=0x%08x device=0x%08x size=%u "
                         "usage=0x%x format=%u pool=%u\n",
                         guest_buffer, guest_device, size, usage, format, pool);
        }
        return true;
    }

    bool update_guest_d3d9_index_buffer(
        uint32_t guest_buffer, uint32_t offset, const uint8_t* data,
        size_t size, std::string& error) {
        const auto buffer = guest_index_buffers.find(guest_buffer);
        const auto buffer_size = guest_index_buffer_sizes.find(guest_buffer);
        if (buffer == guest_index_buffers.end() ||
            buffer_size == guest_index_buffer_sizes.end() || !data || size == 0 ||
            offset > buffer_size->second || size > buffer_size->second - offset) {
            error = "invalid guest D3D9 index buffer update";
            return false;
        }
        void* mapped = nullptr;
        const VkResult map_result = vkMapMemory(
            device, buffer->second.memory, 0, VK_WHOLE_SIZE, 0, &mapped);
        if (map_result != VK_SUCCESS) {
            error = "could not map guest D3D9 index buffer memory";
            return false;
        }
        std::memcpy(static_cast<uint8_t*>(mapped) + offset, data, size);
        vkUnmapMemory(device, buffer->second.memory);
        const char* trace = std::getenv("SHIFT_TRACE_D3D9_RESOURCES");
        if (trace && *trace) {
            std::fprintf(stderr,
                         "shift_runtime: guest D3D9 index buffer updated "
                         "buffer=0x%08x offset=%u size=%zu\n",
                         guest_buffer, offset, size);
        }
        return true;
    }

    bool image_supports_samples(VkFormat format, VkImageUsageFlags usage,
                                VkSampleCountFlagBits samples) const {
        return (image_sample_count_mask(format, usage) & samples) != 0;
    }

    uint32_t image_sample_count_mask(VkFormat format,
                                    VkImageUsageFlags usage) const {
        VkImageFormatProperties properties{};
        const VkResult result = vkGetPhysicalDeviceImageFormatProperties(
            physical, format, VK_IMAGE_TYPE_2D, VK_IMAGE_TILING_OPTIMAL,
            usage, 0, &properties);
        return result == VK_SUCCESS
                   ? static_cast<uint32_t>(properties.sampleCounts)
                   : 0;
    }

    bool create_guest_d3d9_device(
        uint32_t focus_window, uint32_t behavior_flags,
        shift::runtime::RecompiledGuestD3d9PresentationParameters& parameters,
        std::string& error) {
        constexpr uint32_t guest_window = 0x00030008;
        guest_d3d9_focus_window = focus_window;
        guest_d3d9_behavior_flags = behavior_flags;
        guest_d3d9_presentation = parameters;
        if (guest_d3d9_device_bound || !window || !window->connection ||
            window->window == XCB_WINDOW_NONE || !physical || !device ||
            surface == VK_NULL_HANDLE) {
            error = "Vulkan presentation surface is not ready";
            return false;
        }
        if (focus_window != guest_window) {
            error = "CreateDevice focus window does not match the guest window";
            return false;
        }
        if (parameters.device_window != guest_window) {
            error = "CreateDevice presentation window does not match the guest window";
            return false;
        }
        if (parameters.windowed > 1) {
            error = "invalid D3D9 windowed flag";
            return false;
        }
        if (parameters.back_buffer_format != 21 &&
            parameters.back_buffer_format != 22) {
            error = "unsupported D3D9 backbuffer format";
            return false;
        }
        if (parameters.back_buffer_count > 1) {
            error = "D3D9 backbuffer count exceeds the Vulkan profile";
            return false;
        }
        if (parameters.swap_effect != 1) {
            error = "unsupported D3D9 swap effect";
            return false;
        }
        if (parameters.multisample_quality != 0) {
            error = "unsupported D3D9 multisample quality";
            return false;
        }
        if (parameters.enable_auto_depth_stencil > 1) {
            error = "invalid D3D9 auto depth/stencil flag";
            return false;
        }

        VkSampleCountFlagBits samples = VK_SAMPLE_COUNT_1_BIT;
        if (parameters.multisample_type != 0) {
            if (parameters.multisample_type == 1 ||
                parameters.multisample_type > 64 ||
                (parameters.multisample_type &
                 (parameters.multisample_type - 1)) != 0) {
                error = "unsupported D3D9 multisample type";
                return false;
            }
            samples = static_cast<VkSampleCountFlagBits>(
                parameters.multisample_type);
        }
        if (!image_supports_samples(
                VK_FORMAT_B8G8R8A8_UNORM,
                VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT |
                    (samples == VK_SAMPLE_COUNT_1_BIT
                         ? 0
                         : VK_IMAGE_USAGE_TRANSIENT_ATTACHMENT_BIT),
                samples)) {
            error = "Vulkan backbuffer format does not support requested MSAA";
            return false;
        }

        VkFormat requested_depth_format = depth_format;
        if (parameters.enable_auto_depth_stencil != 0) {
            if (parameters.auto_depth_stencil_format != 75) {
                error = "unsupported retail D3D9 depth/stencil format";
                return false;
            }
            requested_depth_format = VK_FORMAT_D24_UNORM_S8_UINT;
            if (!image_supports_samples(
                    requested_depth_format,
                    VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT, samples)) {
                error = "Vulkan D24S8 format does not support requested MSAA";
                return false;
            }
        } else if (!image_supports_samples(
                       requested_depth_format,
                       VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT,
                       samples)) {
            error = "Vulkan depth format does not support requested MSAA";
            return false;
        }

        const uint32_t requested_width = parameters.back_buffer_width == 0
                                             ? window->width
                                             : parameters.back_buffer_width;
        const uint32_t requested_height = parameters.back_buffer_height == 0
                                              ? window->height
                                              : parameters.back_buffer_height;
        try {
            if (requested_width != window->width ||
                requested_height != window->height) {
                window->resize(requested_width, requested_height);
            }
            if (swapchain == VK_NULL_HANDLE) create_swapchain();
        } catch (const std::exception& exception) {
            error = exception.what();
            return false;
        }
        if (swapchain_extent.width == 0 || swapchain_extent.height == 0) {
            error = "Vulkan swapchain has an empty extent";
            return false;
        }

        parameters.back_buffer_width = swapchain_extent.width;
        parameters.back_buffer_height = swapchain_extent.height;
        parameters.back_buffer_count =
            parameters.back_buffer_count == 0 ? 1
                                               : parameters.back_buffer_count;
        guest_sample_count = samples;
        depth_format = requested_depth_format;
        guest_d3d9_presentation = parameters;
        guest_d3d9_device_bound = true;
        return true;
    }

    void create_instance() {
        const std::vector<const char*> extensions = {
            VK_KHR_SURFACE_EXTENSION_NAME,
            VK_KHR_XCB_SURFACE_EXTENSION_NAME
        };

        VkApplicationInfo app{};
        app.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
        app.pApplicationName = "Need for Speed: SHIFT Linux Test Runtime";
        app.applicationVersion = 1;
        app.pEngineName = "SHIFT";
        app.engineVersion = 1;
        app.apiVersion = VK_API_VERSION_1_0;

        VkInstanceCreateInfo create{};
        create.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
        create.pApplicationInfo = &app;
        validation.create_instance(create, extensions, instance);
    }

    void create_surface() {
        VkXcbSurfaceCreateInfoKHR create{};
        create.sType = VK_STRUCTURE_TYPE_XCB_SURFACE_CREATE_INFO_KHR;
        create.connection = window->connection;
        create.window = window->window;

        vk_check(vkCreateXcbSurfaceKHR(
                     instance, &create, nullptr, &surface),
                 "vkCreateXcbSurfaceKHR failed");
    }

    bool pick_queue_families(VkPhysicalDevice candidate) {
        uint32_t count = 0;
        vkGetPhysicalDeviceQueueFamilyProperties(candidate, &count, nullptr);
        std::vector<VkQueueFamilyProperties> families(count);
        vkGetPhysicalDeviceQueueFamilyProperties(
            candidate, &count, families.data());

        int graphics = -1;
        int present = -1;
        for (uint32_t i = 0; i < count; ++i) {
            if ((families[i].queueFlags & VK_QUEUE_GRAPHICS_BIT) != 0u &&
                graphics < 0) {
                graphics = static_cast<int>(i);
            }

            VkBool32 supports_present = VK_FALSE;
            vk_check(vkGetPhysicalDeviceSurfaceSupportKHR(
                         candidate, i, surface, &supports_present),
                     "vkGetPhysicalDeviceSurfaceSupportKHR failed");
            if (supports_present == VK_TRUE && present < 0) {
                present = static_cast<int>(i);
            }
        }

        if (graphics < 0 || present < 0) return false;
        graphics_family = static_cast<uint32_t>(graphics);
        present_family = static_cast<uint32_t>(present);
        return true;
    }

    void create_device() {
        uint32_t count = 0;
        vk_check(vkEnumeratePhysicalDevices(
                     instance, &count, nullptr),
                 "vkEnumeratePhysicalDevices(count) failed");
        if (count == 0) throw std::runtime_error("no Vulkan physical devices");

        std::vector<VkPhysicalDevice> devices(count);
        vk_check(vkEnumeratePhysicalDevices(
                     instance, &count, devices.data()),
                 "vkEnumeratePhysicalDevices(data) failed");

        for (VkPhysicalDevice candidate : devices) {
            if (pick_queue_families(candidate)) {
                physical = candidate;
                break;
            }
        }
        if (!physical) {
            throw std::runtime_error(
                "no Vulkan device supports graphics + XCB presentation");
        }
        vkGetPhysicalDeviceProperties(physical, &physical_properties);
        vkGetPhysicalDeviceFeatures(physical, &physical_features);

        const float priority = 1.0f;
        std::array<VkDeviceQueueCreateInfo, 2> queue_infos{};
        queue_infos[0].sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
        queue_infos[0].queueFamilyIndex = graphics_family;
        queue_infos[0].queueCount = 1;
        queue_infos[0].pQueuePriorities = &priority;

        uint32_t queue_count = 1;
        if (present_family != graphics_family) {
            queue_infos[1] = queue_infos[0];
            queue_infos[1].queueFamilyIndex = present_family;
            queue_count = 2;
        }

        const char* device_extensions[] = {
            VK_KHR_SWAPCHAIN_EXTENSION_NAME
        };

        VkDeviceCreateInfo create{};
        create.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
        create.queueCreateInfoCount = queue_count;
        create.pQueueCreateInfos = queue_infos.data();
        create.enabledExtensionCount = 1;
        create.ppEnabledExtensionNames = device_extensions;
        VkPhysicalDeviceFeatures enabled_features{};
        enabled_features.samplerAnisotropy =
            physical_features.samplerAnisotropy;
        enabled_features.largePoints = physical_features.largePoints;
        create.pEnabledFeatures = &enabled_features;

        vk_check(vkCreateDevice(
                     physical, &create, nullptr, &device),
                 "vkCreateDevice failed");

        vkGetDeviceQueue(
            device, graphics_family, 0, &graphics_queue);
        vkGetDeviceQueue(
            device, present_family, 0, &present_queue);
    }

    void create_swapchain() {
        VkSurfaceCapabilitiesKHR caps{};
        vk_check(vkGetPhysicalDeviceSurfaceCapabilitiesKHR(
                     physical, surface, &caps),
                 "surface capabilities failed");

        uint32_t format_count = 0;
        vk_check(vkGetPhysicalDeviceSurfaceFormatsKHR(
                     physical, surface, &format_count, nullptr),
                 "surface formats failed");
        if (format_count == 0) throw std::runtime_error("no Vulkan surface formats");

        std::vector<VkSurfaceFormatKHR> formats(format_count);
        vk_check(vkGetPhysicalDeviceSurfaceFormatsKHR(
                     physical, surface, &format_count, formats.data()),
                 "surface formats failed");

        VkSurfaceFormatKHR chosen = formats.front();
        for (const auto& format : formats) {
            if (format.format == VK_FORMAT_B8G8R8A8_UNORM &&
                format.colorSpace == VK_COLOR_SPACE_SRGB_NONLINEAR_KHR) {
                chosen = format;
                break;
            }
        }
        swapchain_format = chosen.format;

        swapchain_extent = caps.currentExtent;
        if (swapchain_extent.width == std::numeric_limits<uint32_t>::max()) {
            swapchain_extent = {
                std::clamp(kWindowWidth, caps.minImageExtent.width,
                           caps.maxImageExtent.width),
                std::clamp(kWindowHeight, caps.minImageExtent.height,
                           caps.maxImageExtent.height)
            };
        }

        uint32_t image_count = caps.minImageCount + 1;
        if (caps.maxImageCount != 0) {
            image_count = std::min(image_count, caps.maxImageCount);
        }

        VkSwapchainCreateInfoKHR create{};
        create.sType = VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR;
        create.surface = surface;
        create.minImageCount = image_count;
        create.imageFormat = chosen.format;
        create.imageColorSpace = chosen.colorSpace;
        create.imageExtent = swapchain_extent;
        create.imageArrayLayers = 1;
        create.imageUsage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT;
        const std::array<uint32_t, 2> queue_families = {
            graphics_family, present_family
        };
        if (graphics_family != present_family) {
            create.imageSharingMode = VK_SHARING_MODE_CONCURRENT;
            create.queueFamilyIndexCount =
                static_cast<uint32_t>(queue_families.size());
            create.pQueueFamilyIndices = queue_families.data();
        } else {
            create.imageSharingMode = VK_SHARING_MODE_EXCLUSIVE;
        }
        create.preTransform = caps.currentTransform;
        create.compositeAlpha = VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR;
        create.presentMode = VK_PRESENT_MODE_FIFO_KHR;
        create.clipped = VK_TRUE;

        vk_check(vkCreateSwapchainKHR(
                     device, &create, nullptr, &swapchain),
                 "vkCreateSwapchainKHR failed");

        vk_check(vkGetSwapchainImagesKHR(
                     device, swapchain, &image_count, nullptr),
                 "vkGetSwapchainImagesKHR(count) failed");
        swapchain_images.resize(image_count);
        vk_check(vkGetSwapchainImagesKHR(
                     device, swapchain, &image_count, swapchain_images.data()),
                 "vkGetSwapchainImagesKHR(data) failed");

        swapchain_views.resize(swapchain_images.size());
        for (size_t i = 0; i < swapchain_images.size(); ++i) {
            VkImageViewCreateInfo view{};
            view.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
            view.image = swapchain_images[i];
            view.viewType = VK_IMAGE_VIEW_TYPE_2D;
            view.format = swapchain_format;
            view.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
            view.subresourceRange.baseMipLevel = 0;
            view.subresourceRange.levelCount = 1;
            view.subresourceRange.baseArrayLayer = 0;
            view.subresourceRange.layerCount = 1;
            vk_check(vkCreateImageView(
                         device, &view, nullptr, &swapchain_views[i]),
                     "vkCreateImageView failed");
        }
    }

    VkShaderModule load_shader(const std::string& path) {
        const auto code = read_spirv(path);
        VkShaderModuleCreateInfo create{};
        create.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
        create.codeSize = code.size() * sizeof(uint32_t);
        create.pCode = code.data();

        VkShaderModule module = VK_NULL_HANDLE;
        vk_check(vkCreateShaderModule(
                     device, &create, nullptr, &module),
                 "vkCreateShaderModule failed");
        return module;
    }

    void create_image(
        uint32_t width,
        uint32_t height,
        uint32_t layers,
        VkFormat format,
        VkImageCreateFlags flags,
        VkImageUsageFlags usage,
        VkImageAspectFlags aspect,
        Image& out,
        VkSampleCountFlagBits samples = VK_SAMPLE_COUNT_1_BIT) {
        VkImageCreateInfo create{};
        create.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
        create.flags = flags;
        create.imageType = VK_IMAGE_TYPE_2D;
        create.format = format;
        create.extent = {width, height, 1};
        create.mipLevels = 1;
        create.arrayLayers = layers;
        create.samples = samples;
        create.tiling = VK_IMAGE_TILING_OPTIMAL;
        create.usage = usage;
        create.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        vk_check(vkCreateImage(device, &create, nullptr, &out.handle),
                 "vkCreateImage failed");
        out.device = device;
        out.layers = layers;

        VkMemoryRequirements requirements{};
        vkGetImageMemoryRequirements(device, out.handle, &requirements);
        VkMemoryAllocateInfo allocate{};
        allocate.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
        allocate.allocationSize = requirements.size;
        allocate.memoryTypeIndex = find_memory_type(
            physical, requirements.memoryTypeBits,
            VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        vk_check(vkAllocateMemory(
                     device, &allocate, nullptr, &out.memory),
                 "vkAllocateMemory image failed");
        vk_check(vkBindImageMemory(
                     device, out.handle, out.memory, 0),
                 "vkBindImageMemory failed");

        VkImageViewCreateInfo view{};
        view.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
        view.image = out.handle;
        view.viewType = layers == 6 ? VK_IMAGE_VIEW_TYPE_CUBE : VK_IMAGE_VIEW_TYPE_2D;
        view.format = format;
        view.subresourceRange.aspectMask = aspect;
        view.subresourceRange.levelCount = 1;
        view.subresourceRange.layerCount = layers;
        vk_check(vkCreateImageView(
                     device, &view, nullptr, &out.view),
                 "vkCreateImageView resource failed");
    }

    void create_depth_resources() {
        VkFormatProperties properties{};
        vkGetPhysicalDeviceFormatProperties(
            physical, depth_format, &properties);
        if ((properties.optimalTilingFeatures &
             VK_FORMAT_FEATURE_DEPTH_STENCIL_ATTACHMENT_BIT) == 0u) {
            throw std::runtime_error(
                "selected depth/stencil attachment format is unsupported");
        }

        if (guest_sample_count != VK_SAMPLE_COUNT_1_BIT) {
            multisample_color_images.resize(swapchain_views.size());
            for (auto& image : multisample_color_images) {
                create_image(
                    swapchain_extent.width,
                    swapchain_extent.height,
                    1,
                    swapchain_format,
                    0,
                    VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT |
                        VK_IMAGE_USAGE_TRANSIENT_ATTACHMENT_BIT,
                    VK_IMAGE_ASPECT_COLOR_BIT,
                    image,
                    guest_sample_count);
            }
        }

        depth_images.resize(swapchain_views.size());
        const VkImageAspectFlags depth_aspect =
            depth_format == VK_FORMAT_D24_UNORM_S8_UINT ||
                    depth_format == VK_FORMAT_D32_SFLOAT_S8_UINT
                ? VK_IMAGE_ASPECT_DEPTH_BIT | VK_IMAGE_ASPECT_STENCIL_BIT
                : VK_IMAGE_ASPECT_DEPTH_BIT;
        for (auto& image : depth_images) {
            create_image(
                swapchain_extent.width,
                swapchain_extent.height,
                1,
                depth_format,
                0,
                VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT,
                depth_aspect,
                image,
                guest_sample_count);
        }
    }

    VkSampler create_sampler(uint32_t mode) {
        const bool linear = mode == 2 || mode == 4;
        const bool clamp = mode == 3 || mode == 4;
        VkSamplerCreateInfo create{};
        create.sType = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO;
        create.magFilter = linear ? VK_FILTER_LINEAR : VK_FILTER_NEAREST;
        create.minFilter = linear ? VK_FILTER_LINEAR : VK_FILTER_NEAREST;
        create.mipmapMode = VK_SAMPLER_MIPMAP_MODE_NEAREST;
        create.addressModeU = clamp ? VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE :
                                      VK_SAMPLER_ADDRESS_MODE_REPEAT;
        create.addressModeV = clamp ? VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE :
                                      VK_SAMPLER_ADDRESS_MODE_REPEAT;
        create.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
        create.maxLod = 1.0f;
        VkSampler sampler = VK_NULL_HANDLE;
        vk_check(vkCreateSampler(
                     device, &create, nullptr, &sampler),
                 "vkCreateSampler failed");
        return sampler;
    }

    void create_material_resources(
        const BundleAssets& bundle,
        MaterialDraw& draw) {
        if (bundle.vertex_constants.size() != kBundleConstantBytes ||
            bundle.pixel_constants.size() != kBundleConstantBytes) {
            throw std::runtime_error("bundle constants are incomplete");
        }

        create_buffer(
            bundle.vertex_constants.data(), kBundleConstantBytes,
            VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT, draw.vertex_constants);
        create_buffer(
            bundle.pixel_constants.data(), kBundleConstantBytes,
            VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT, draw.pixel_constants);

        draw.texture_staging.resize(bundle.textures.size());
        draw.texture_images.resize(bundle.textures.size());
        draw.texture_samplers.resize(bundle.textures.size());
        for (size_t i = 0; i < bundle.textures.size(); ++i) {
            const BundleTexture& texture = bundle.textures[i];
            create_buffer(
                texture.pixels.data(),
                texture.pixels.size(),
                VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
                draw.texture_staging[i]);
            create_image(
                texture.width, texture.height, 1,
                VK_FORMAT_R8G8B8A8_UNORM,
                0,
                VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_SAMPLED_BIT,
                VK_IMAGE_ASPECT_COLOR_BIT,
                draw.texture_images[i]);
            draw.texture_samplers[i] = create_sampler(texture.sampler_mode);
        }

        if (bundle.has_cube) {
            create_buffer(
                bundle.cube.pixels.data(),
                bundle.cube.pixels.size(),
                VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
                draw.cube_staging);
            create_image(
                bundle.cube.width, bundle.cube.height, 6,
                VK_FORMAT_R8G8B8A8_UNORM,
                VK_IMAGE_CREATE_CUBE_COMPATIBLE_BIT,
                VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_SAMPLED_BIT,
                VK_IMAGE_ASPECT_COLOR_BIT,
                draw.cube_image);
            draw.cube_sampler = create_sampler(4);
        }

        VkDescriptorSetLayoutBinding set0_bindings[2]{};
        set0_bindings[0].binding = 14;
        set0_bindings[0].descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
        set0_bindings[0].descriptorCount = 1;
        set0_bindings[0].stageFlags = VK_SHADER_STAGE_VERTEX_BIT;
        set0_bindings[1].binding = 15;
        set0_bindings[1].descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
        set0_bindings[1].descriptorCount = 1;
        set0_bindings[1].stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT;

        VkDescriptorSetLayoutCreateInfo set0_info{};
        set0_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
        set0_info.bindingCount = 2;
        set0_info.pBindings = set0_bindings;
        vk_check(vkCreateDescriptorSetLayout(
                     device, &set0_info, nullptr, &draw.set0_layout),
                 "vkCreateDescriptorSetLayout set0 failed");

        std::map<uint32_t, VkDescriptorImageInfo> sampled;
        for (size_t i = 0; i < bundle.textures.size(); ++i) {
            const uint32_t reg = bundle.textures[i].register_index;
            VkDescriptorImageInfo info{};
            info.sampler = draw.texture_samplers[i];
            info.imageView = draw.texture_images[i].view;
            info.imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
            if (!sampled.emplace(reg, info).second) {
                throw std::runtime_error("duplicate bundle sampler register");
            }
        }
        if (bundle.has_cube) {
            VkDescriptorImageInfo info{};
            info.sampler = draw.cube_sampler;
            info.imageView = draw.cube_image.view;
            info.imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
            if (!sampled.emplace(bundle.cube.register_index, info).second) {
                throw std::runtime_error(
                    "cube sampler register collides with 2D texture");
            }
        }

        std::vector<VkDescriptorSetLayoutBinding> set1_bindings;
        set1_bindings.reserve(sampled.size());
        for (const auto& item : sampled) {
            VkDescriptorSetLayoutBinding binding{};
            binding.binding = item.first;
            binding.descriptorType =
                VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
            binding.descriptorCount = 1;
            binding.stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT;
            set1_bindings.push_back(binding);
        }

        VkDescriptorSetLayoutCreateInfo set1_info{};
        set1_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
        set1_info.bindingCount =
            static_cast<uint32_t>(set1_bindings.size());
        set1_info.pBindings =
            set1_bindings.empty() ? nullptr : set1_bindings.data();
        vk_check(vkCreateDescriptorSetLayout(
                     device, &set1_info, nullptr, &draw.set1_layout),
                 "vkCreateDescriptorSetLayout set1 failed");

        std::vector<VkDescriptorPoolSize> pool_sizes;
        pool_sizes.push_back({VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, 2});
        if (!sampled.empty()) {
            pool_sizes.push_back({
                VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
                static_cast<uint32_t>(sampled.size())
            });
        }
        VkDescriptorPoolCreateInfo pool{};
        pool.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;
        pool.maxSets = 2;
        pool.poolSizeCount = static_cast<uint32_t>(pool_sizes.size());
        pool.pPoolSizes = pool_sizes.data();
        vk_check(vkCreateDescriptorPool(
                     device, &pool, nullptr, &draw.descriptor_pool),
                 "vkCreateDescriptorPool failed");

        VkDescriptorSetAllocateInfo set0_alloc{};
        set0_alloc.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
        set0_alloc.descriptorPool = draw.descriptor_pool;
        set0_alloc.descriptorSetCount = 1;
        set0_alloc.pSetLayouts = &draw.set0_layout;
        vk_check(vkAllocateDescriptorSets(
                     device, &set0_alloc, &draw.set0),
                 "vkAllocateDescriptorSets set0 failed");

        VkDescriptorBufferInfo vertex_info{
            draw.vertex_constants.handle, 0, kBundleConstantBytes
        };
        VkDescriptorBufferInfo pixel_info{
            draw.pixel_constants.handle, 0, kBundleConstantBytes
        };
        VkWriteDescriptorSet writes[2]{};
        writes[0].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
        writes[0].dstSet = draw.set0;
        writes[0].dstBinding = 14;
        writes[0].descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
        writes[0].descriptorCount = 1;
        writes[0].pBufferInfo = &vertex_info;
        writes[1] = writes[0];
        writes[1].dstBinding = 15;
        writes[1].pBufferInfo = &pixel_info;
        vkUpdateDescriptorSets(device, 2, writes, 0, nullptr);

        if (!set1_bindings.empty()) {
            VkDescriptorSetAllocateInfo set1_alloc{};
            set1_alloc.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
            set1_alloc.descriptorPool = draw.descriptor_pool;
            set1_alloc.descriptorSetCount = 1;
            set1_alloc.pSetLayouts = &draw.set1_layout;
            vk_check(vkAllocateDescriptorSets(
                         device, &set1_alloc, &draw.set1),
                     "vkAllocateDescriptorSets set1 failed");

            std::vector<VkWriteDescriptorSet> image_writes;
            image_writes.reserve(sampled.size());
            std::vector<VkDescriptorImageInfo> image_infos;
            image_infos.reserve(sampled.size());
            for (const auto& item : sampled) {
                image_infos.push_back(item.second);
            }
            size_t image_index = 0;
            for (const auto& item : sampled) {
                VkWriteDescriptorSet write{};
                write.sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
                write.dstSet = draw.set1;
                write.dstBinding = item.first;
                write.descriptorType =
                    VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
                write.descriptorCount = 1;
                write.pImageInfo = &image_infos[image_index++];
                image_writes.push_back(write);
            }
            vkUpdateDescriptorSets(
                device,
                static_cast<uint32_t>(image_writes.size()),
                image_writes.data(),
                0,
                nullptr);
        }
    }

    void upload_material_resources(
        const BundleAssets& bundle,
        MaterialDraw& draw) {
        if (draw.texture_staging.empty() && !draw.cube_staging.handle) {
            return;
        }

        VkCommandBufferAllocateInfo allocate{};
        allocate.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
        allocate.commandPool = command_pool;
        allocate.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        allocate.commandBufferCount = 1;
        VkCommandBuffer command = VK_NULL_HANDLE;
        vk_check(vkAllocateCommandBuffers(
                     device, &allocate, &command),
                 "vkAllocateCommandBuffers resource upload failed");

        VkCommandBufferBeginInfo begin{};
        begin.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
        begin.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        vk_check(vkBeginCommandBuffer(command, &begin),
                 "vkBeginCommandBuffer resource upload failed");

        auto transition = [&](VkImage image, uint32_t layers,
                              VkImageLayout old_layout,
                              VkImageLayout new_layout,
                              VkAccessFlags src_access,
                              VkAccessFlags dst_access,
                              VkPipelineStageFlags src_stage,
                              VkPipelineStageFlags dst_stage) {
            VkImageMemoryBarrier barrier{};
            barrier.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
            barrier.srcAccessMask = src_access;
            barrier.dstAccessMask = dst_access;
            barrier.oldLayout = old_layout;
            barrier.newLayout = new_layout;
            barrier.image = image;
            barrier.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
            barrier.subresourceRange.levelCount = 1;
            barrier.subresourceRange.layerCount = layers;
            vkCmdPipelineBarrier(
                command, src_stage, dst_stage, 0,
                0, nullptr, 0, nullptr, 1, &barrier);
        };

        for (size_t i = 0; i < draw.texture_staging.size(); ++i) {
            transition(
                draw.texture_images[i].handle, 1,
                VK_IMAGE_LAYOUT_UNDEFINED,
                VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                0, VK_ACCESS_TRANSFER_WRITE_BIT,
                VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                VK_PIPELINE_STAGE_TRANSFER_BIT);

            VkBufferImageCopy copy{};
            copy.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
            copy.imageSubresource.layerCount = 1;
            copy.imageExtent = {
                bundle.textures[i].width,
                bundle.textures[i].height,
                1
            };
            vkCmdCopyBufferToImage(
                command, draw.texture_staging[i].handle,
                draw.texture_images[i].handle,
                VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                1, &copy);

            transition(
                draw.texture_images[i].handle, 1,
                VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                VK_ACCESS_TRANSFER_WRITE_BIT,
                VK_ACCESS_SHADER_READ_BIT,
                VK_PIPELINE_STAGE_TRANSFER_BIT,
                VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT);
        }

        if (draw.cube_staging.handle) {
            transition(
                draw.cube_image.handle, 6,
                VK_IMAGE_LAYOUT_UNDEFINED,
                VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                0, VK_ACCESS_TRANSFER_WRITE_BIT,
                VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                VK_PIPELINE_STAGE_TRANSFER_BIT);

            const VkDeviceSize face_bytes =
                static_cast<VkDeviceSize>(bundle.cube.width) *
                static_cast<VkDeviceSize>(bundle.cube.height) * 4u;
            for (uint32_t face = 0; face < 6; ++face) {
                VkBufferImageCopy copy{};
                copy.bufferOffset =
                    static_cast<VkDeviceSize>(face) * face_bytes;
                copy.imageSubresource.aspectMask =
                    VK_IMAGE_ASPECT_COLOR_BIT;
                copy.imageSubresource.baseArrayLayer = face;
                copy.imageSubresource.layerCount = 1;
                copy.imageExtent = {
                    bundle.cube.width,
                    bundle.cube.height,
                    1
                };
                vkCmdCopyBufferToImage(
                    command, draw.cube_staging.handle,
                    draw.cube_image.handle,
                    VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                    1, &copy);
            }

            transition(
                draw.cube_image.handle, 6,
                VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                VK_ACCESS_TRANSFER_WRITE_BIT,
                VK_ACCESS_SHADER_READ_BIT,
                VK_PIPELINE_STAGE_TRANSFER_BIT,
                VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT);
        }

        vk_check(vkEndCommandBuffer(command),
                 "vkEndCommandBuffer resource upload failed");

        VkSubmitInfo submit{};
        submit.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
        submit.commandBufferCount = 1;
        submit.pCommandBuffers = &command;
        vk_check(vkQueueSubmit(
                     graphics_queue, 1, &submit, VK_NULL_HANDLE),
                 "vkQueueSubmit resource upload failed");
        vk_check(vkQueueWaitIdle(
                     graphics_queue),
                 "vkQueueWaitIdle resource upload failed");
        vkFreeCommandBuffers(device, command_pool, 1, &command);

        for (auto& staging : draw.texture_staging) staging.destroy();
        draw.texture_staging.clear();
        draw.cube_staging.destroy();
    }

    void create_render_pass() {
        if (render_pass != VK_NULL_HANDLE) return;

        const bool multisampled =
            guest_sample_count != VK_SAMPLE_COUNT_1_BIT;
        std::array<VkAttachmentDescription, 3> attachments{};
        attachments[0].format = swapchain_format;
        attachments[0].samples = guest_sample_count;
        attachments[0].loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
        attachments[0].storeOp = multisampled
                                     ? VK_ATTACHMENT_STORE_OP_DONT_CARE
                                     : VK_ATTACHMENT_STORE_OP_STORE;
        attachments[0].initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        attachments[0].finalLayout = multisampled
                                         ? VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL
                                         : VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;
        attachments[1].format = depth_format;
        attachments[1].samples = guest_sample_count;
        attachments[1].loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
        attachments[1].storeOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
        const bool has_stencil =
            depth_format == VK_FORMAT_D16_UNORM_S8_UINT ||
            depth_format == VK_FORMAT_D24_UNORM_S8_UINT ||
            depth_format == VK_FORMAT_D32_SFLOAT_S8_UINT;
        attachments[1].stencilLoadOp = has_stencil
                                           ? VK_ATTACHMENT_LOAD_OP_CLEAR
                                           : VK_ATTACHMENT_LOAD_OP_DONT_CARE;
        attachments[1].stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
        attachments[1].initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        attachments[1].finalLayout =
            VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;
        if (multisampled) {
            attachments[2].format = swapchain_format;
            attachments[2].samples = VK_SAMPLE_COUNT_1_BIT;
            attachments[2].loadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
            attachments[2].storeOp = VK_ATTACHMENT_STORE_OP_STORE;
            attachments[2].initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
            attachments[2].finalLayout = VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;
        }

        VkAttachmentReference color_ref{};
        color_ref.attachment = 0;
        color_ref.layout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
        VkAttachmentReference depth_ref{};
        depth_ref.attachment = 1;
        depth_ref.layout =
            VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;
        VkAttachmentReference resolve_ref{};
        resolve_ref.attachment = 2;
        resolve_ref.layout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;

        VkSubpassDescription subpass{};
        subpass.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
        subpass.colorAttachmentCount = 1;
        subpass.pColorAttachments = &color_ref;
        subpass.pResolveAttachments = multisampled ? &resolve_ref : nullptr;
        subpass.pDepthStencilAttachment = &depth_ref;

        VkSubpassDependency dependency{};
        dependency.srcSubpass = VK_SUBPASS_EXTERNAL;
        dependency.dstSubpass = 0;
        dependency.srcStageMask =
            VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT |
            VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT;
        dependency.dstStageMask =
            VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT |
            VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT;
        dependency.dstAccessMask =
            VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT |
            VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT;

        VkRenderPassCreateInfo pass{};
        pass.sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
        pass.attachmentCount = multisampled ? 3 : 2;
        pass.pAttachments = attachments.data();
        pass.subpassCount = 1;
        pass.pSubpasses = &subpass;
        pass.dependencyCount = 1;
        pass.pDependencies = &dependency;
        vk_check(vkCreateRenderPass(
                     device, &pass, nullptr, &render_pass),
                 "vkCreateRenderPass failed");
    }

    void create_pipeline_common(
        const PacketGeometry& geometry,
        const std::string& vertex_shader_path,
        const std::string& fragment_shader_path,
        bool uses_material_descriptors,
        const BundlePipelineState& material_pipeline_state,
        VkDescriptorSetLayout material_set0,
        VkDescriptorSetLayout material_set1,
        VkShaderModule& out_vertex_shader,
        VkShaderModule& out_fragment_shader,
        VkPipelineLayout& out_pipeline_layout,
        VkPipeline& out_pipeline) {

        if (render_pass == VK_NULL_HANDLE) {
            throw std::runtime_error(
                "render pass must exist before pipeline creation");
        }

        out_vertex_shader = load_shader(vertex_shader_path);
        out_fragment_shader = load_shader(fragment_shader_path);

        VkPushConstantRange push{};
        push.stageFlags = VK_SHADER_STAGE_VERTEX_BIT;
        push.offset = 0;
        push.size = sizeof(float) * 16;

        const std::array<VkDescriptorSetLayout, 2> descriptor_set_layouts = {
            material_set0, material_set1
        };
        VkPipelineLayoutCreateInfo layout{};
        layout.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
        if (uses_material_descriptors) {
            layout.setLayoutCount =
                static_cast<uint32_t>(descriptor_set_layouts.size());
            layout.pSetLayouts = descriptor_set_layouts.data();
        } else {
            layout.pushConstantRangeCount = 1;
            layout.pPushConstantRanges = &push;
        }
        vk_check(vkCreatePipelineLayout(
                     device, &layout, nullptr, &out_pipeline_layout),
                 "vkCreatePipelineLayout failed");

        VkPipelineShaderStageCreateInfo stages[2]{};
        stages[0].sType =
            VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module = out_vertex_shader;
        stages[0].pName = "main";
        stages[1].sType =
            VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module = out_fragment_shader;
        stages[1].pName = "main";

        VkVertexInputBindingDescription binding{};
        binding.binding = 0;
        binding.stride = geometry.stride;
        binding.inputRate = VK_VERTEX_INPUT_RATE_VERTEX;

        auto vk_format = [](uint32_t format) -> VkFormat {
            switch (format) {
                case 1: return VK_FORMAT_R32G32_SFLOAT;
                case 2: return VK_FORMAT_R32G32B32_SFLOAT;
                case 3: return VK_FORMAT_R32G32B32A32_SFLOAT;
                case 4: return VK_FORMAT_R8G8B8A8_UNORM;
                case 5: return VK_FORMAT_R8G8B8A8_UINT;
                default: return VK_FORMAT_UNDEFINED;
            }
        };

        std::vector<VkVertexInputAttributeDescription> vertex_attributes;
        vertex_attributes.reserve(geometry.attributes.size());
        for (const auto& input : geometry.attributes) {
            VkVertexInputAttributeDescription attribute{};
            attribute.location = input.location;
            attribute.binding = 0;
            attribute.format = vk_format(input.format);
            attribute.offset = input.offset;
            if (attribute.format == VK_FORMAT_UNDEFINED) {
                throw std::runtime_error(
                    "unknown runtime vertex attribute format");
            }
            vertex_attributes.push_back(attribute);
        }
        if (vertex_attributes.empty()) {
            throw std::runtime_error(
                "runtime geometry has no vertex attributes");
        }

        VkPipelineVertexInputStateCreateInfo vertex_input{};
        vertex_input.sType =
            VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO;
        vertex_input.vertexBindingDescriptionCount = 1;
        vertex_input.pVertexBindingDescriptions = &binding;
        vertex_input.vertexAttributeDescriptionCount =
            static_cast<uint32_t>(vertex_attributes.size());
        vertex_input.pVertexAttributeDescriptions =
            vertex_attributes.data();

        VkPipelineInputAssemblyStateCreateInfo assembly{};
        assembly.sType =
            VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO;
        assembly.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;

        VkViewport viewport{};
        viewport.width = static_cast<float>(swapchain_extent.width);
        viewport.height = static_cast<float>(swapchain_extent.height);
        viewport.maxDepth = 1.0f;

        VkRect2D scissor{};
        scissor.extent = swapchain_extent;

        VkPipelineViewportStateCreateInfo viewport_state{};
        viewport_state.sType =
            VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO;
        viewport_state.viewportCount = 1;
        viewport_state.pViewports = &viewport;
        viewport_state.scissorCount = 1;
        viewport_state.pScissors = &scissor;

        VkPipelineRasterizationStateCreateInfo raster{};
        raster.sType =
            VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO;
        raster.polygonMode = VK_POLYGON_MODE_FILL;
        raster.cullMode = material_pipeline_state.cull_mode;
        raster.frontFace = VK_FRONT_FACE_COUNTER_CLOCKWISE;
        raster.lineWidth = 1.0f;

        VkPipelineMultisampleStateCreateInfo multisample{};
        multisample.sType =
            VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO;
        multisample.rasterizationSamples = guest_sample_count;

        VkPipelineDepthStencilStateCreateInfo depth_state{};
        depth_state.sType =
            VK_STRUCTURE_TYPE_PIPELINE_DEPTH_STENCIL_STATE_CREATE_INFO;
        depth_state.depthTestEnable =
            material_pipeline_state.depth_test_enable;
        depth_state.depthWriteEnable =
            material_pipeline_state.depth_write_enable;
        depth_state.depthCompareOp =
            material_pipeline_state.depth_compare_op;

        VkPipelineColorBlendAttachmentState color_blend{};
        color_blend.blendEnable = material_pipeline_state.blend_enable;
        color_blend.srcColorBlendFactor =
            material_pipeline_state.src_color_blend_factor;
        color_blend.dstColorBlendFactor =
            material_pipeline_state.dst_color_blend_factor;
        color_blend.colorBlendOp =
            material_pipeline_state.color_blend_op;
        color_blend.srcAlphaBlendFactor =
            material_pipeline_state.src_alpha_blend_factor;
        color_blend.dstAlphaBlendFactor =
            material_pipeline_state.dst_alpha_blend_factor;
        color_blend.alphaBlendOp =
            material_pipeline_state.alpha_blend_op;
        color_blend.colorWriteMask =
            VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
            VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT;

        VkPipelineColorBlendStateCreateInfo blend{};
        blend.sType =
            VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO;
        blend.attachmentCount = 1;
        blend.pAttachments = &color_blend;

        VkGraphicsPipelineCreateInfo create{};
        create.sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO;
        create.stageCount = 2;
        create.pStages = stages;
        create.pVertexInputState = &vertex_input;
        create.pInputAssemblyState = &assembly;
        create.pViewportState = &viewport_state;
        create.pRasterizationState = &raster;
        create.pMultisampleState = &multisample;
        create.pDepthStencilState = &depth_state;
        create.pColorBlendState = &blend;
        create.layout = out_pipeline_layout;
        create.renderPass = render_pass;
        create.subpass = 0;

        vk_check(vkCreateGraphicsPipelines(
                     device, VK_NULL_HANDLE, 1, &create,
                     nullptr, &out_pipeline),
                 "vkCreateGraphicsPipelines failed");
    }

    void create_mesh_pipeline(
        const std::string& shader_dir,
        const PacketGeometry& geometry) {
        BundlePipelineState state{};
        state.cull_mode = VK_CULL_MODE_BACK_BIT;
        create_pipeline_common(
            geometry,
            shader_dir + "/runtime.vert.spv",
            shader_dir + "/runtime.frag.spv",
            false,
            state,
            VK_NULL_HANDLE,
            VK_NULL_HANDLE,
            vertex_shader,
            fragment_shader,
            pipeline_layout,
            pipeline);
    }

    void create_material_pipeline(
        const PacketGeometry& geometry,
        const BundleAssets& bundle,
        MaterialDraw& draw) {
        create_pipeline_common(
            geometry,
            bundle.vertex_shader_path,
            bundle.fragment_shader_path,
            true,
            bundle.pipeline_state,
            draw.set0_layout,
            draw.set1_layout,
            draw.vertex_shader,
            draw.fragment_shader,
            draw.pipeline_layout,
            draw.pipeline);
    }

    void create_buffer(
        const void* data, VkDeviceSize size,
        VkBufferUsageFlags usage, Buffer& out) {

        VkBufferCreateInfo create{};
        create.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
        create.size = size;
        create.usage = usage;
        create.sharingMode = VK_SHARING_MODE_EXCLUSIVE;

        vk_check(vkCreateBuffer(
                     device, &create, nullptr, &out.handle),
                 "vkCreateBuffer failed");
        out.device = device;

        VkMemoryRequirements requirements{};
        vkGetBufferMemoryRequirements(
            device, out.handle, &requirements);

        VkMemoryAllocateInfo allocate{};
        allocate.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
        allocate.allocationSize = requirements.size;
        allocate.memoryTypeIndex = find_memory_type(
            physical, requirements.memoryTypeBits,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
            VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);

        vk_check(vkAllocateMemory(
                     device, &allocate, nullptr, &out.memory),
                 "vkAllocateMemory failed");
        vk_check(vkBindBufferMemory(
                     device, out.handle, out.memory, 0),
                 "vkBindBufferMemory failed");

        void* mapped = nullptr;
        vk_check(vkMapMemory(
                     device, out.memory, 0, size, 0, &mapped),
                 "vkMapMemory failed");
        if (data) std::memcpy(mapped, data, static_cast<size_t>(size));
        vkUnmapMemory(device, out.memory);
    }

    void create_geometry(
        const PacketGeometry& geometry,
        Buffer& out_vertex_buffer,
        Buffer& out_index_buffer,
        uint32_t& out_first_index,
        uint32_t& out_index_count) {
        if (geometry.indices.empty() || geometry.attributes.empty() ||
            geometry.stride == 0) {
            throw std::runtime_error(
                "runtime geometry has no drawable vertex data");
        }
        if (!geometry.vertex_bytes.empty()) {
            create_buffer(
                geometry.vertex_bytes.data(),
                static_cast<VkDeviceSize>(
                    geometry.vertex_bytes.size()),
                VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
                out_vertex_buffer);
        } else if (!geometry.positions.empty()) {
            create_buffer(
                geometry.positions.data(),
                static_cast<VkDeviceSize>(
                    geometry.positions.size() * sizeof(float)),
                VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
                out_vertex_buffer);
        } else {
            throw std::runtime_error(
                "runtime geometry has no vertex payload");
        }
        create_buffer(
            geometry.indices.data(),
            static_cast<VkDeviceSize>(
                geometry.indices.size() * sizeof(uint32_t)),
            VK_BUFFER_USAGE_INDEX_BUFFER_BIT,
            out_index_buffer);
        if (geometry.first_index >= geometry.indices.size()) {
            throw std::runtime_error(
                "runtime geometry first_index is out of range");
        }
        out_first_index = geometry.first_index;
        out_index_count = static_cast<uint32_t>(
            geometry.indices.size() - out_first_index);
        if (out_index_count == 0) {
            throw std::runtime_error(
                "runtime geometry has no drawable indices");
        }
    }

    void create_framebuffers() {
        if (depth_images.size() != swapchain_views.size()) {
            throw std::runtime_error(
                "depth image count does not match swapchain image count");
        }
        const bool multisampled =
            guest_sample_count != VK_SAMPLE_COUNT_1_BIT;
        if (multisampled &&
            multisample_color_images.size() != swapchain_views.size()) {
            throw std::runtime_error(
                "multisample color image count does not match the swapchain");
        }
        framebuffers.resize(swapchain_views.size());
        for (size_t i = 0; i < swapchain_views.size(); ++i) {
            std::array<VkImageView, 3> attachments{};
            uint32_t attachment_count = 2;
            if (multisampled) {
                attachments = {multisample_color_images[i].view,
                               depth_images[i].view, swapchain_views[i]};
                attachment_count = 3;
            } else {
                attachments[0] = swapchain_views[i];
                attachments[1] = depth_images[i].view;
            }
            VkFramebufferCreateInfo create{};
            create.sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
            create.renderPass = render_pass;
            create.attachmentCount = attachment_count;
            create.pAttachments = attachments.data();
            create.width = swapchain_extent.width;
            create.height = swapchain_extent.height;
            create.layers = 1;
            vk_check(vkCreateFramebuffer(
                         device, &create, nullptr, &framebuffers[i]),
                     "vkCreateFramebuffer failed");
        }
    }

    void create_sync_and_commands() {
        VkCommandPoolCreateInfo pool{};
        pool.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
        pool.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
        pool.queueFamilyIndex = graphics_family;
        vk_check(vkCreateCommandPool(
                     device, &pool, nullptr, &command_pool),
                 "vkCreateCommandPool failed");

        command_buffers.resize(kFramesInFlight);
        VkCommandBufferAllocateInfo allocate{};
        allocate.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
        allocate.commandPool = command_pool;
        allocate.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        allocate.commandBufferCount =
            static_cast<uint32_t>(command_buffers.size());
        vk_check(vkAllocateCommandBuffers(
                     device, &allocate, command_buffers.data()),
                 "vkAllocateCommandBuffers failed");

        VkSemaphoreCreateInfo semaphore{};
        semaphore.sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO;

        VkFenceCreateInfo fence{};
        fence.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
        fence.flags = VK_FENCE_CREATE_SIGNALED_BIT;

        for (size_t i = 0; i < kFramesInFlight; ++i) {
            vk_check(vkCreateSemaphore(
                         device, &semaphore, nullptr, &image_available[i]),
                     "vkCreateSemaphore failed");
            vk_check(vkCreateFence(
                         device, &fence, nullptr, &fences[i]),
                     "vkCreateFence failed");
        }
        render_finished.resize(swapchain_images.size(), VK_NULL_HANDLE);
        for (auto& finished : render_finished) {
            vk_check(vkCreateSemaphore(device, &semaphore, nullptr, &finished),
                     "vkCreateSemaphore presentation failed");
        }
    }

    void record(VkCommandBuffer command, uint32_t image_index,
                bool guest_d3d9_frame, bool guest_d3d9_clear) {
        VkCommandBufferBeginInfo begin{};
        begin.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
        vk_check(vkBeginCommandBuffer(
                     command, &begin),
                 "vkBeginCommandBuffer failed");

        VkRenderPassBeginInfo pass{};
        pass.sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
        pass.renderPass = render_pass;
        pass.framebuffer = framebuffers[image_index];
        pass.renderArea.extent = swapchain_extent;

        std::array<VkClearValue, 3> clear{};
        if (guest_d3d9_clear) {
            clear[0].color.float32[0] =
                static_cast<float>((guest_d3d9_clear_color >> 16) & 0xff) /
                255.0f;
            clear[0].color.float32[1] =
                static_cast<float>((guest_d3d9_clear_color >> 8) & 0xff) /
                255.0f;
            clear[0].color.float32[2] =
                static_cast<float>(guest_d3d9_clear_color & 0xff) / 255.0f;
            clear[0].color.float32[3] =
                static_cast<float>((guest_d3d9_clear_color >> 24) & 0xff) /
                255.0f;
            std::memcpy(&clear[1].depthStencil.depth,
                        &guest_d3d9_clear_depth_bits, sizeof(float));
            clear[1].depthStencil.stencil = guest_d3d9_clear_stencil;
        } else {
            clear[0].color.float32[0] = 0.018f;
            clear[0].color.float32[1] = 0.022f;
            clear[0].color.float32[2] = 0.032f;
            clear[0].color.float32[3] = 1.0f;
            clear[1].depthStencil.depth = 1.0f;
        }
        pass.clearValueCount =
            guest_sample_count == VK_SAMPLE_COUNT_1_BIT ? 2 : 3;
        pass.pClearValues = clear.data();

        vkCmdBeginRenderPass(
            command, &pass, VK_SUBPASS_CONTENTS_INLINE);

        if (guest_d3d9_frame) {
            // Guest draw calls are not translated yet; present the queued clear.
        } else if (material_mode) {
            for (const MaterialDraw& draw : material_draws) {
                vkCmdBindPipeline(
                    command,
                    VK_PIPELINE_BIND_POINT_GRAPHICS,
                    draw.pipeline);

                VkDeviceSize offset = 0;
                vkCmdBindVertexBuffers(
                    command, 0, 1, &draw.vertex_buffer.handle, &offset);
                vkCmdBindIndexBuffer(
                    command, draw.index_buffer.handle,
                    0, VK_INDEX_TYPE_UINT32);

                vkCmdBindDescriptorSets(
                    command,
                    VK_PIPELINE_BIND_POINT_GRAPHICS,
                    draw.pipeline_layout,
                    0, 1, &draw.set0, 0, nullptr);
                if (draw.set1 != VK_NULL_HANDLE) {
                    vkCmdBindDescriptorSets(
                        command,
                        VK_PIPELINE_BIND_POINT_GRAPHICS,
                        draw.pipeline_layout,
                        1, 1, &draw.set1, 0, nullptr);
                }

                vkCmdDrawIndexed(
                    command, draw.index_count, 1,
                    draw.first_index, 0, 0);
            }
        } else {
            vkCmdBindPipeline(
                command, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline);

            VkDeviceSize offset = 0;
            vkCmdBindVertexBuffers(
                command, 0, 1, &vertex_buffer.handle, &offset);
            vkCmdBindIndexBuffer(
                command, index_buffer.handle, 0, VK_INDEX_TYPE_UINT32);

            const std::array<float, 16> mvp = {
                1.05f, 0.0f, 0.0f, 0.0f,
                0.0f, -1.05f, 0.0f, 0.0f,
                0.0f, 0.0f, 0.8f, 0.0f,
                0.0f, 0.0f, 0.0f, 1.0f
            };
            vkCmdPushConstants(
                command, pipeline_layout, VK_SHADER_STAGE_VERTEX_BIT,
                0, sizeof(mvp), mvp.data());

            vkCmdDrawIndexed(
                command, index_count, 1, first_index, 0, 0);
        }

        vkCmdEndRenderPass(command);

        vk_check(vkEndCommandBuffer(
                     command),
                 "vkEndCommandBuffer failed");
    }

    bool frame() {
        frame_stop_reason.clear();
        const size_t slot = frame_slot % kFramesInFlight;
        vk_check(vkWaitForFences(
                     device, 1, &fences[slot], VK_TRUE, UINT64_MAX),
                 "vkWaitForFences failed");

        uint32_t image_index = 0;
        const VkResult acquire = vkAcquireNextImageKHR(
            device, swapchain, UINT64_MAX,
            image_available[slot], VK_NULL_HANDLE,
            &image_index);

        if (acquire == VK_ERROR_OUT_OF_DATE_KHR) {
            frame_stop_reason = "acquire_out_of_date";
            return false;
        }
        if (acquire != VK_SUBOPTIMAL_KHR) {
            vk_check(acquire, "vkAcquireNextImageKHR failed");
        }

        vk_check(vkResetFences(
                     device, 1, &fences[slot]),
                 "vkResetFences failed");
        vk_check(vkResetCommandBuffer(
                     command_buffers[slot], 0),
                 "vkResetCommandBuffer failed");

        const bool guest_d3d9_frame =
            guest_d3d9_vulkan_present_submission_count <
            guest_d3d9_present_request_count;
        const bool guest_d3d9_clear =
            guest_d3d9_frame &&
            guest_d3d9_vulkan_clear_submission_count <
                guest_d3d9_clear_request_count;
        record(command_buffers[slot], image_index, guest_d3d9_frame,
               guest_d3d9_clear);

        const VkPipelineStageFlags wait_stage =
            VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
        VkSubmitInfo submit{};
        submit.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
        submit.waitSemaphoreCount = 1;
        submit.pWaitSemaphores = &image_available[slot];
        submit.pWaitDstStageMask = &wait_stage;
        submit.commandBufferCount = 1;
        submit.pCommandBuffers = &command_buffers[slot];
        submit.signalSemaphoreCount = 1;
        submit.pSignalSemaphores = &render_finished[image_index];

        vk_check(vkQueueSubmit(
                     graphics_queue, 1, &submit, fences[slot]),
                 "vkQueueSubmit failed");
        if (guest_d3d9_clear) {
            ++guest_d3d9_vulkan_clear_submission_count;
        }

        VkPresentInfoKHR present{};
        present.sType = VK_STRUCTURE_TYPE_PRESENT_INFO_KHR;
        present.waitSemaphoreCount = 1;
        present.pWaitSemaphores = &render_finished[image_index];
        present.swapchainCount = 1;
        present.pSwapchains = &swapchain;
        present.pImageIndices = &image_index;

        const VkResult present_result =
            vkQueuePresentKHR(present_queue, &present);

        ++frame_slot;
        if (present_result == VK_ERROR_OUT_OF_DATE_KHR) {
            frame_stop_reason = "present_out_of_date";
            return false;
        }
        if (present_result != VK_SUBOPTIMAL_KHR) {
            vk_check(present_result, "vkQueuePresentKHR failed");
        }
        if (guest_d3d9_frame) {
            ++guest_d3d9_vulkan_present_submission_count;
        }
        return true;
    }

    void destroy() {
        if (device != VK_NULL_HANDLE) {
            vkDeviceWaitIdle(device);
        }

        vertex_buffer.destroy();
        index_buffer.destroy();
        for (auto& draw : material_draws) {
            draw.destroy(device);
        }
        material_draws.clear();

        for (size_t i = 0; i < kFramesInFlight; ++i) {
            if (image_available[i]) {
                vkDestroySemaphore(device, image_available[i], nullptr);
            }
            if (fences[i]) {
                vkDestroyFence(device, fences[i], nullptr);
            }
        }

        for (auto finished : render_finished) {
            if (finished) vkDestroySemaphore(device, finished, nullptr);
        }
        render_finished.clear();

        if (command_pool) {
            vkDestroyCommandPool(device, command_pool, nullptr);
        }
        for (auto framebuffer : framebuffers) {
            vkDestroyFramebuffer(device, framebuffer, nullptr);
        }
        for (auto& image : depth_images) {
            image.destroy();
        }
        depth_images.clear();
        for (auto& image : multisample_color_images) {
            image.destroy();
        }
        multisample_color_images.clear();
        for (auto& [guest_texture, image] : guest_texture_images) {
            (void)guest_texture;
            image.destroy();
        }
        guest_texture_images.clear();
        for (auto& [guest_buffer, buffer] : guest_vertex_buffers) {
            (void)guest_buffer;
            buffer.destroy();
        }
        guest_vertex_buffers.clear();
        guest_vertex_buffer_sizes.clear();
        for (auto& [guest_buffer, buffer] : guest_index_buffers) {
            (void)guest_buffer;
            buffer.destroy();
        }
        guest_index_buffers.clear();
        guest_index_buffer_sizes.clear();
        if (pipeline) {
            vkDestroyPipeline(device, pipeline, nullptr);
        }
        if (pipeline_layout) {
            vkDestroyPipelineLayout(device, pipeline_layout, nullptr);
        }
        if (render_pass) {
            vkDestroyRenderPass(device, render_pass, nullptr);
        }
        if (vertex_shader) {
            vkDestroyShaderModule(device, vertex_shader, nullptr);
        }
        if (fragment_shader) {
            vkDestroyShaderModule(device, fragment_shader, nullptr);
        }
        for (auto view : swapchain_views) {
            vkDestroyImageView(device, view, nullptr);
        }
        if (swapchain) {
            vkDestroySwapchainKHR(device, swapchain, nullptr);
        }
        if (device) {
            vkDestroyDevice(device, nullptr);
        }
        if (surface) {
            vkDestroySurfaceKHR(instance, surface, nullptr);
        }
        if (instance) {
            validation.detach(instance);
            vkDestroyInstance(instance, nullptr);
        }

        instance = VK_NULL_HANDLE;
        surface = VK_NULL_HANDLE;
        physical = VK_NULL_HANDLE;
        device = VK_NULL_HANDLE;
    }
};

struct Args {
    std::string mesh;
    std::string bundle;
    std::string bundle_set;
    std::string scene_set;
    std::string camera_state;
    std::string physics_manifest;
    std::string participant_boundary;
    std::string solver_frame;
    std::string body_solver_export_frame;
    std::string generated_body_constraint_frame;
    std::string constraint_sample_relation_frame;
    std::string constraint_relation_reset_frame;
    std::string post_solve_projection;
    std::string shader_dir;
    std::string input_script;
    std::string recompiled_module;
    std::vector<std::string> recompiled_supplement_modules;
    std::vector<std::string> recompiled_override_modules;
    std::string pe_image;
    uint32_t recompiled_step = 0;
    bool recompiled_step_enabled = false;
    bool recompiled_entrypoint_enabled = false;
    int frames = kDefaultFrames;
    bool frames_explicit = false;
    bool continuous = false;
    bool persist_post_solve_body_state = false;
    bool validation = false;
};

Args parse_args(int argc, char** argv) {
    Args args;
    for (int i = 1; i < argc; ++i) {
        const std::string option = argv[i];
        if (option == "--recompiled-entrypoint") {
            args.recompiled_entrypoint_enabled = true;
            continue;
        }
        if (option == "--mesh" || option == "--bundle" ||
            option == "--bundle-set" ||
            option == "--scene-set" ||
            option == "--camera-state" ||
            option == "--physics-manifest" ||
            option == "--participant-boundary" ||
            option == "--solver-frame" ||
            option == "--body-solver-export-frame" ||
            option == "--generated-body-constraint-frame" ||
            option == "--constraint-sample-relation-frame" ||
            option == "--constraint-relation-reset-frame" ||
            option == "--post-solve-projection" ||
            option == "--shader-dir" ||
            option == "--input-script" ||
            option == "--recompiled-module" ||
            option == "--recompiled-supplement" ||
            option == "--recompiled-override" ||
            option == "--pe-image" ||
            option == "--recompiled-step" ||
            option == "--frames") {
            if (i + 1 >= argc) {
                throw std::runtime_error(
                    "missing value for " + option);
            }
            const std::string value = argv[++i];
            if (option == "--mesh") args.mesh = value;
            else if (option == "--bundle") args.bundle = value;
            else if (option == "--bundle-set") args.bundle_set = value;
            else if (option == "--scene-set") args.scene_set = value;
            else if (option == "--camera-state") args.camera_state = value;
            else if (option == "--physics-manifest") {
                args.physics_manifest = value;
            } else if (option == "--participant-boundary") {
                args.participant_boundary = value;
            } else if (option == "--solver-frame") {
                args.solver_frame = value;
            } else if (option == "--body-solver-export-frame") {
                args.body_solver_export_frame = value;
            } else if (option == "--generated-body-constraint-frame") {
                args.generated_body_constraint_frame = value;
            } else if (option == "--constraint-sample-relation-frame") {
                args.constraint_sample_relation_frame = value;
            } else if (option == "--constraint-relation-reset-frame") {
                args.constraint_relation_reset_frame = value;
            } else if (option == "--post-solve-projection") {
                args.post_solve_projection = value;
            } else if (option == "--shader-dir") {
                args.shader_dir = value;
            } else if (option == "--input-script") {
                args.input_script = value;
            } else if (option == "--recompiled-module") {
                args.recompiled_module = value;
            } else if (option == "--recompiled-supplement") {
                args.recompiled_supplement_modules.push_back(value);
            } else if (option == "--recompiled-override") {
                args.recompiled_override_modules.push_back(value);
            } else if (option == "--pe-image") {
                args.pe_image = value;
            } else if (option == "--recompiled-step") {
                args.recompiled_step = parse_guest_address(value);
                args.recompiled_step_enabled = true;
            } else {
                args.frames = std::max(1, std::stoi(value));
                args.frames_explicit = true;
            }
        } else if (option == "--continuous") {
            args.continuous = true;
        } else if (option == "--persist-post-solve-body-state") {
            args.persist_post_solve_body_state = true;
        } else if (option == "--validation") {
            args.validation = true;
        } else if (option == "--help") {
            std::cout
                << "usage: shift_runtime "
                << "(--mesh FILE | --bundle DIR | --bundle-set DIR | --scene-set DIR) "
                << "--shader-dir DIR [--camera-state FILE] "
                << "[--participant-boundary FILE] "
                << "[--solver-frame FILE] "
                << "[--body-solver-export-frame FILE] "
                << "[--generated-body-constraint-frame FILE] "
                << "[--constraint-sample-relation-frame FILE] "
                << "[--constraint-relation-reset-frame FILE] "
                << "[--post-solve-projection FILE] "
                << "[--persist-post-solve-body-state] "
                << "[--input-script FILE] [--frames N] "
                << "[--recompiled-module ELF [--recompiled-supplement ELF ...] "
                << "[--recompiled-override ELF ...] "
                << "[--recompiled-step ADDRESS] "
                << "[--pe-image PE32 [--recompiled-entrypoint]]] "
                << "[--continuous] [--validation]\n";
            std::exit(EXIT_SUCCESS);
        } else {
            throw std::runtime_error(
                "unknown option: " + option);
        }
    }

    const int source_count =
        (!args.mesh.empty() ? 1 : 0) +
        (!args.bundle.empty() ? 1 : 0) +
        (!args.bundle_set.empty() ? 1 : 0) +
        (!args.scene_set.empty() ? 1 : 0);
    if (source_count != 1) {
        throw std::runtime_error(
            "exactly one of --mesh, --bundle, --bundle-set or --scene-set is required");
    }
    if (args.shader_dir.empty()) {
        throw std::runtime_error(
            "--shader-dir is required");
    }
    if (args.recompiled_module.empty() &&
        (args.recompiled_step_enabled || args.recompiled_entrypoint_enabled ||
         !args.recompiled_supplement_modules.empty() ||
         !args.recompiled_override_modules.empty())) {
        throw std::runtime_error(
            "--recompiled-module is required for P-code execution");
    }
    if (!args.recompiled_module.empty() && !args.recompiled_step_enabled &&
        !args.recompiled_entrypoint_enabled) {
        throw std::runtime_error(
            "provide --recompiled-step or --recompiled-entrypoint with --recompiled-module");
    }
    if (!args.pe_image.empty() && args.recompiled_module.empty()) {
        throw std::runtime_error(
            "--pe-image requires --recompiled-module");
    }
    if (args.recompiled_entrypoint_enabled && args.pe_image.empty()) {
        throw std::runtime_error(
            "--recompiled-entrypoint requires --pe-image");
    }
    return args;
}

}  // namespace

int main(int argc, char** argv) {
    Runtime runtime;
    Window window;

    try {
        const Args args = parse_args(argc, argv);
        runtime.validation.enabled = args.validation;
        std::unique_ptr<shift::runtime::RecompiledPcodeModule>
            recompiled_module;
        shift::runtime::Pe32ImageInfo recompiled_pe_image_info{};
        bool recompiled_pe_image_loaded = false;
        uint64_t recompiled_pe_entry_point_invocations = 0;
        if (!args.recompiled_module.empty()) {
            recompiled_module =
                std::make_unique<shift::runtime::RecompiledPcodeModule>(
                    args.recompiled_module);
            if (!recompiled_module->set_guest_display_mode(
                    kWindowWidth, kWindowHeight, 0,
                    kD3dDisplayFormatX8R8G8B8)) {
                throw std::runtime_error(recompiled_module->last_error());
            }
            for (const auto& override_module :
                 args.recompiled_override_modules) {
                if (!recompiled_module->load_override_module(override_module)) {
                    throw std::runtime_error(
                        recompiled_module->last_error());
                }
            }
            for (const auto& supplement : args.recompiled_supplement_modules) {
                if (!recompiled_module->load_supplemental_module(supplement)) {
                    throw std::runtime_error(
                        recompiled_module->last_error());
                }
            }
            if (!args.pe_image.empty()) {
                recompiled_pe_image_info =
                    recompiled_module->load_pe32_image(args.pe_image);
                recompiled_pe_image_loaded = true;
                std::cerr << "Loaded PE32 image into P-code guest RAM: base="
                          << format_guest_address(
                                 recompiled_pe_image_info.image_base)
                          << " size=" << recompiled_pe_image_info.image_size
                          << " entry="
                          << format_guest_address(
                                 recompiled_pe_image_info.entry_point)
                          << " sections="
                          << recompiled_pe_image_info.section_count
                          << " imports="
                          << recompiled_pe_image_info.import_function_count
                          << '\n';
            }
        }

        const bool input_script_mode =
            !args.input_script.empty();
        InputScript input_script{};
        if (input_script_mode) {
            input_script = load_input_script(
                args.input_script);
        }
        const shift::runtime::RuntimeLoopPolicy loop_policy =
            shift::runtime::make_runtime_loop_policy(
                args.continuous,
                args.frames_explicit,
                args.frames,
                input_script_mode,
                input_script.steps.size());
        const int frame_limit = loop_policy.frame_limit;

        PacketGeometry mesh_geometry;
        std::vector<PacketGeometry> material_geometry;
        std::vector<BundleAssets> material_assets;
        const bool bundle_set_mode = !args.bundle_set.empty();
        const bool scene_set_mode = !args.scene_set.empty();
        const bool material_set_mode =
            bundle_set_mode || scene_set_mode;
        const bool material_mode =
            !args.bundle.empty() || material_set_mode;

        if (material_set_mode) {
            const std::string& set_root =
                scene_set_mode ? args.scene_set : args.bundle_set;
            const std::vector<std::string> children =
                load_bundle_set_paths(set_root, scene_set_mode);
            material_geometry.reserve(children.size());
            material_assets.reserve(children.size());
            for (const std::string& child : children) {
                material_geometry.push_back(
                    load_bundle_geometry(child));
                material_assets.push_back(
                    load_bundle_assets(child));
            }
        } else if (!args.bundle.empty()) {
            material_geometry.push_back(
                load_bundle_geometry(args.bundle));
            material_assets.push_back(
                load_bundle_assets(args.bundle));
        } else {
            const shift::ir::Mesh mesh =
                shift::ir::loadMgeo(args.mesh);
            mesh_geometry.positions.reserve(
                mesh.positions.size() * 3u);
            for (const auto& vertex : mesh.positions) {
                mesh_geometry.positions.push_back(vertex.x);
                mesh_geometry.positions.push_back(vertex.y);
                mesh_geometry.positions.push_back(vertex.z);
            }
            mesh_geometry.indices = mesh.indices;
            mesh_geometry.attributes = {{
                0, 2, 0,
                static_cast<uint32_t>(sizeof(float) * 3u)
            }};
            mesh_geometry.stride = sizeof(float) * 3u;
            mesh_geometry.source = "MGEO";
        }

        size_t geometry_vertices = 0;
        size_t geometry_indices = 0;
        size_t world_transform_draws = 0;
        size_t affine_world_transform_draws = 0;
        std::string geometry_source;
        if (material_mode) {
            geometry_source = scene_set_mode
                ? "SHIFT.NativeSceneVulkanSet/1"
                : bundle_set_mode
                    ? "SHIFT.BMWVulkanBundleSet/1"
                    : "SHIFT.BMWVulkanBundle/1";
            for (const auto& geometry : material_geometry) {
                geometry_vertices += geometry.positions.size() / 3u;
                geometry_indices += geometry.indices.size();
                if (geometry.world_transform_applied) {
                    ++world_transform_draws;
                    if (geometry.world_transform_mode != "translation") {
                        ++affine_world_transform_draws;
                    }
                }
            }
        } else {
            geometry_source = mesh_geometry.source;
            geometry_vertices =
                mesh_geometry.positions.size() / 3u;
            geometry_indices = mesh_geometry.indices.size();
        }

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeRuntimeBootstrap/1\",\n"
            << "  \"geometry_source\": \""
            << geometry_source << "\",\n"
            << "  \"geometry_vertices\": "
            << geometry_vertices << ",\n"
            << "  \"geometry_indices\": "
            << geometry_indices << ",\n"
            << "  \"material_mode\": "
            << (material_mode ? "true" : "false") << ",\n"
            << "  \"bundle_set_mode\": "
            << (bundle_set_mode ? "true" : "false") << ",\n"
            << "  \"scene_set_mode\": "
            << (scene_set_mode ? "true" : "false") << ",\n"
            << "  \"material_draws\": "
            << material_geometry.size() << ",\n"
            << "  \"world_transform_draws\": "
            << world_transform_draws << ",\n"
            << "  \"affine_world_transform_draws\": "
            << affine_world_transform_draws << ",\n"
            << "  \"input_script_mode\": "
            << (input_script_mode ? "true" : "false") << ",\n"
            << "  \"input_script_steps\": "
            << input_script.steps.size() << ",\n"
            << "  \"continuous_mode\": "
            << (loop_policy.continuous ? "true" : "false") << ",\n"
            << "  \"frame_limit_enabled\": "
            << (loop_policy.frame_limit_enabled ? "true" : "false") << ",\n"
            << "  \"runtime_loop_schedule\": "
            << "\"one-native-fixed-step-per-render-frame-non-retail\",\n"
            << "  \"solver_frame_mode\": "
            << (!args.solver_frame.empty() ? "true" : "false") << ",\n"
            << "  \"body_solver_export_frame_mode\": "
            << (!args.body_solver_export_frame.empty() ? "true" : "false")
            << ",\n"
            << "  \"generated_body_constraint_frame_mode\": "
            << (!args.generated_body_constraint_frame.empty() ?
                "true" : "false")
            << ",\n"
            << "  \"constraint_sample_relation_frame_mode\": "
            << (!args.constraint_sample_relation_frame.empty() ?
                "true" : "false")
            << ",\n"
            << "  \"constraint_relation_reset_frame_mode\": "
            << (!args.constraint_relation_reset_frame.empty() ?
                "true" : "false")
            << ",\n"
            << "  \"post_solve_projection_mode\": "
            << (!args.post_solve_projection.empty() ? "true" : "false")
            << ",\n"
            << "  \"frames_requested\": "
            << (loop_policy.frame_limit_enabled ? frame_limit : 0) << "\n"
            << "}\n";

        window.create();
        runtime.window = &window;
        runtime.create_instance();
        runtime.create_surface();
        runtime.create_device();
        if (recompiled_module) {
            const auto adapter_info = runtime.recompiled_d3d9_adapter_info();
            if (!recompiled_module->set_guest_d3d9_adapter_info(
                    adapter_info)) {
                throw std::runtime_error(recompiled_module->last_error());
            }
        }
        if (recompiled_module && args.recompiled_entrypoint_enabled) {
            const int result = recompiled_module->call_pe32_entry_point();
            if (result != 0) {
                throw std::runtime_error(
                    "recompiled PE32 entry point " +
                    format_guest_address(
                        recompiled_pe_image_info.entry_point) +
                    " failed after " +
                    std::to_string(
                        recompiled_module->dispatched_function_count()) +
                    " P-code function dispatches across " +
                    std::to_string(recompiled_module
                                       ->unique_dispatched_function_count()) +
                    " unique functions: " +
                    recompiled_module->last_error());
            }
            ++recompiled_pe_entry_point_invocations;
        }
        if (runtime.swapchain == VK_NULL_HANDLE) {
            runtime.create_swapchain();
        }
        runtime.create_depth_resources();
        runtime.create_render_pass();

        runtime.material_mode = material_mode;
        if (material_mode) {
            if (material_geometry.size() !=
                material_assets.size()) {
                throw std::runtime_error(
                    "material geometry/assets count mismatch");
            }
            runtime.material_draws.resize(
                material_geometry.size());
            for (size_t i = 0;
                 i < material_geometry.size(); ++i) {
                MaterialDraw& draw =
                    runtime.material_draws[i];
                runtime.create_material_resources(
                    material_assets[i], draw);
                runtime.create_material_pipeline(
                    material_geometry[i],
                    material_assets[i],
                    draw);
                runtime.create_geometry(
                    material_geometry[i],
                    draw.vertex_buffer,
                    draw.index_buffer,
                    draw.first_index,
                    draw.index_count);
            }
        } else {
            runtime.create_mesh_pipeline(
                args.shader_dir, mesh_geometry);
            runtime.create_geometry(
                mesh_geometry,
                runtime.vertex_buffer,
                runtime.index_buffer,
                runtime.first_index,
                runtime.index_count);
        }

        runtime.create_framebuffers();
        runtime.create_sync_and_commands();
        if (material_mode) {
            for (size_t i = 0;
                 i < material_assets.size(); ++i) {
                runtime.upload_material_resources(
                    material_assets[i],
                    runtime.material_draws[i]);
            }
        }

        int rendered = 0;
        uint64_t simulation_steps = 0;
        uint64_t recompiled_step_invocations = 0;
        bool quit = false;
        std::string quit_reason;
        InputState live_input{};
        shift::runtime::NativeRuntimeState native_state{};
        const bool camera_state_bridge_loaded =
            !args.camera_state.empty();
        if (camera_state_bridge_loaded) {
            load_camera_state_bridge(
                args.camera_state,
                native_state.camera);
        }
        if (!args.physics_manifest.empty()) {
            native_state.physics.workspace =
                load_physics_manifest(
                    args.physics_manifest);
        }
        if (!args.participant_boundary.empty()) {
            load_participant_boundary(
                args.participant_boundary,
                native_state.physics);
        }

        const bool solver_frame_mode =
            !args.solver_frame.empty();
        shift::runtime::physics::PreparedBuiltinSolverFrame
            solver_frame{};
        uint64_t solver_frame_steps = 0;
        double solver_frame_max_oracle_error = 0.0;
        std::size_t solver_frame_scalar_count = 0;
        std::size_t solver_frame_reset_node_count = 0;
        if (solver_frame_mode) {
            if (args.physics_manifest.empty()) {
                throw std::runtime_error(
                    "--solver-frame requires --physics-manifest");
            }
            if (args.participant_boundary.empty()) {
                throw std::runtime_error(
                    "--solver-frame requires --participant-boundary");
            }
            if (!native_state.physics.workspace.ready) {
                throw std::runtime_error(
                    "solver frame requires a ready physics workspace");
            }
            if (!native_state.physics.participant_ready ||
                !native_state.physics.participant_identity_join_proven) {
                throw std::runtime_error(
                    "solver frame requires ready runtime participant evidence");
            }
            solver_frame =
                shift::runtime::physics::
                    load_prepared_builtin_solver_frame(
                        args.solver_frame);
            solver_frame_scalar_count =
                solver_frame.matrix.size();
            solver_frame_reset_node_count =
                solver_frame.reset_nodes.size();
            if (solver_frame_scalar_count !=
                native_state.physics.workspace.scalar_count) {
                throw std::runtime_error(
                    "solver frame scalar count does not match physics workspace");
            }
        }
        const bool body_solver_export_frame_mode =
            !args.body_solver_export_frame.empty();
        shift::runtime::physics::PreparedBodySolverExportFrame
            body_solver_export_frame{};
        uint64_t body_solver_export_join_steps = 0;
        double body_solver_export_max_rhs_join_error = 0.0;
        double body_solver_export_max_matrix_join_error = 0.0;
        if (body_solver_export_frame_mode) {
            if (!solver_frame_mode) {
                throw std::runtime_error(
                    "--body-solver-export-frame requires --solver-frame");
            }
            body_solver_export_frame =
                shift::runtime::physics::
                    load_prepared_body_solver_export_frame(
                        args.body_solver_export_frame);
            if (body_solver_export_frame.scalar_count !=
                solver_frame_scalar_count) {
                throw std::runtime_error(
                    "BODY solver export scalar count does not match solver frame");
            }
            shift::runtime::physics::
                verify_body_export_matches_builtin_solver_frame(
                    body_solver_export_frame,
                    solver_frame);
        }

        const bool generated_body_constraint_frame_mode =
            !args.generated_body_constraint_frame.empty();
        const bool constraint_sample_relation_frame_mode =
            !args.constraint_sample_relation_frame.empty();
        const bool constraint_relation_reset_frame_mode =
            !args.constraint_relation_reset_frame.empty();
        shift::runtime::physics::PreparedGeneratedBodyConstraintFrame
            generated_body_constraint_frame{};
        shift::runtime::physics::PreparedConstraintSampleRelationFrame
            constraint_sample_relation_frame{};
        shift::runtime::physics::PreparedConstraintRelationResetFrame
            constraint_relation_reset_frame{};
        uint64_t generated_body_constraint_join_steps = 0;
        uint64_t constraint_sample_relation_refresh_steps = 0;
        double generated_body_constraint_max_rhs_join_error = 0.0;
        double generated_body_constraint_max_matrix_join_error = 0.0;
        std::size_t generated_body_constraint_body_count = 0;
        std::size_t generated_body_constraint_joint_count = 0;
        std::size_t generated_body_constraint_hinge_count = 0;
        std::size_t generated_body_constraint_bar_count = 0;
        std::size_t constraint_sample_relation_joint_count = 0;
        std::size_t constraint_sample_relation_hinge_count = 0;
        std::size_t constraint_sample_relation_bar_count = 0;
        std::size_t constraint_sample_relation_refreshed_joint_samples = 0;
        std::size_t constraint_sample_relation_refreshed_hinge_samples = 0;
        std::size_t constraint_sample_relation_refreshed_bar_samples = 0;
        uint64_t constraint_relation_reset_selection_steps = 0;
        std::size_t constraint_relation_reset_joint_count = 0;
        std::size_t constraint_relation_reset_hinge_count = 0;
        std::size_t constraint_relation_reset_bar_count = 0;
        std::size_t constraint_relation_reset_selected_joint_count = 0;
        std::size_t constraint_relation_reset_selected_hinge_count = 0;
        std::size_t constraint_relation_reset_selected_bar_count = 0;
        std::size_t constraint_relation_reset_node_count = 0;
        std::size_t constraint_relation_reset_call_count = 0;
        bool constraint_relation_reset_matches_solver_frame = false;
        if (constraint_relation_reset_frame_mode &&
            !constraint_sample_relation_frame_mode) {
            throw std::runtime_error(
                "--constraint-relation-reset-frame requires "
                "--constraint-sample-relation-frame");
        }
        if (constraint_sample_relation_frame_mode &&
            !generated_body_constraint_frame_mode) {
            throw std::runtime_error(
                "--constraint-sample-relation-frame requires "
                "--generated-body-constraint-frame");
        }
        if (generated_body_constraint_frame_mode) {
            if (!solver_frame_mode) {
                throw std::runtime_error(
                    "--generated-body-constraint-frame requires --solver-frame");
            }
            if (body_solver_export_frame_mode) {
                throw std::runtime_error(
                    "--generated-body-constraint-frame cannot be combined "
                    "with --body-solver-export-frame");
            }
            generated_body_constraint_frame =
                shift::runtime::physics::
                    load_prepared_generated_body_constraint_frame(
                        args.generated_body_constraint_frame);
            if (generated_body_constraint_frame.scalar_count !=
                solver_frame_scalar_count) {
                throw std::runtime_error(
                    "generated BODY scalar count does not match solver frame");
            }
            if (generated_body_constraint_frame.bodies.size() !=
                native_state.physics.workspace.body_count) {
                throw std::runtime_error(
                    "generated BODY count does not match physics workspace");
            }

            shift::runtime::physics::GeneratedBodySolverFrameJoinResult
                generated_join{};
            if (constraint_sample_relation_frame_mode) {
                constraint_sample_relation_frame =
                    shift::runtime::physics::
                        load_prepared_constraint_sample_relation_frame(
                            args.constraint_sample_relation_frame);
                if (constraint_sample_relation_frame.body_count !=
                    native_state.physics.workspace.body_count) {
                    throw std::runtime_error(
                        "constraint relation BODY count does not match "
                        "physics workspace");
                }
                constraint_sample_relation_joint_count =
                    constraint_sample_relation_frame.joints.size();
                constraint_sample_relation_hinge_count =
                    constraint_sample_relation_frame.hinges.size();
                constraint_sample_relation_bar_count =
                    constraint_sample_relation_frame.bars.size();
                if (constraint_sample_relation_joint_count !=
                        native_state.physics.workspace.joint_hinge_count ||
                    constraint_sample_relation_hinge_count !=
                        native_state.physics.workspace.joint_hinge_count ||
                    constraint_sample_relation_bar_count !=
                        native_state.physics.workspace.bar_count) {
                    throw std::runtime_error(
                        "constraint relation counts do not match "
                        "physics workspace");
                }

                const auto refreshed =
                    shift::runtime::physics::
                        refresh_generated_body_constraint_frame(
                            generated_body_constraint_frame,
                            constraint_sample_relation_frame);
                constraint_sample_relation_refreshed_joint_samples =
                    refreshed.refreshed_joint_sample_count;
                constraint_sample_relation_refreshed_hinge_samples =
                    refreshed.refreshed_hinge_sample_count;
                constraint_sample_relation_refreshed_bar_samples =
                    refreshed.refreshed_bar_sample_count;
                generated_join =
                    shift::runtime::physics::
                        verify_generated_body_constraint_frame_matches_builtin_solver_frame(
                            refreshed.frame,
                            solver_frame);
                if (generated_join.joint_sample_count !=
                        constraint_sample_relation_refreshed_joint_samples ||
                    generated_join.hinge_sample_count !=
                        constraint_sample_relation_refreshed_hinge_samples ||
                    generated_join.bar_sample_count !=
                        constraint_sample_relation_refreshed_bar_samples) {
                    throw std::runtime_error(
                        "refreshed generated BODY sample counts do not match "
                        "constraint relation endpoint coverage");
                }
            } else {
                generated_join =
                    shift::runtime::physics::
                        verify_generated_body_constraint_frame_matches_builtin_solver_frame(
                            generated_body_constraint_frame,
                            solver_frame);
                if (generated_join.joint_sample_count !=
                        native_state.physics.workspace.joint_hinge_count ||
                    generated_join.hinge_sample_count !=
                        native_state.physics.workspace.joint_hinge_count ||
                    generated_join.bar_sample_count !=
                        native_state.physics.workspace.bar_count) {
                    throw std::runtime_error(
                        "generated BODY sample counts do not match physics workspace");
                }
            }

            generated_body_constraint_body_count =
                generated_join.body_count;
            generated_body_constraint_joint_count =
                generated_join.joint_sample_count;
            generated_body_constraint_hinge_count =
                generated_join.hinge_sample_count;
            generated_body_constraint_bar_count =
                generated_join.bar_sample_count;
        }

        if (constraint_relation_reset_frame_mode) {
            constraint_relation_reset_frame =
                shift::runtime::physics::
                    load_prepared_constraint_relation_reset_frame(
                        args.constraint_relation_reset_frame);
            const auto reset_selection =
                shift::runtime::physics::
                    select_fun_007b3f40_reset_nodes(
                        generated_body_constraint_frame,
                        constraint_sample_relation_frame,
                        constraint_relation_reset_frame);
            constraint_relation_reset_joint_count =
                reset_selection.joint_relation_count;
            constraint_relation_reset_hinge_count =
                reset_selection.hinge_relation_count;
            constraint_relation_reset_bar_count =
                reset_selection.bar_relation_count;
            constraint_relation_reset_selected_joint_count =
                reset_selection.selected_joint_relation_count;
            constraint_relation_reset_selected_hinge_count =
                reset_selection.selected_hinge_relation_count;
            constraint_relation_reset_selected_bar_count =
                reset_selection.selected_bar_relation_count;
            constraint_relation_reset_call_count =
                reset_selection.reset_nodes.size();

            const auto normalized_reset_nodes =
                shift::runtime::physics::
                    normalize_fun_007b3f40_reset_nodes(
                        reset_selection.reset_nodes);
            constraint_relation_reset_node_count =
                normalized_reset_nodes.size();
            shift::runtime::physics::
                verify_fun_007b3f40_reset_nodes_match(
                    reset_selection,
                    solver_frame.reset_nodes);
            constraint_relation_reset_matches_solver_frame = true;
        }

        const bool post_solve_projection_mode =
            !args.post_solve_projection.empty();
        if (args.persist_post_solve_body_state &&
            !post_solve_projection_mode) {
            throw std::runtime_error(
                "--persist-post-solve-body-state requires --post-solve-projection");
        }
        shift::runtime::physics::PreparedPostSolveBodyProjection
            post_solve_projection{};
        std::vector<shift::runtime::physics::BodyAccumulatorState>
            persistent_post_solve_bodies;
        uint64_t post_solve_projection_steps = 0;
        uint64_t persistent_post_solve_body_steps = 0;
        double post_solve_max_oracle_error = 0.0;
        double post_solve_max_solver_join_error = 0.0;
        double post_solve_max_delta_error = 0.0;
        std::size_t post_solve_body_count = 0;
        std::size_t post_solve_joint_count = 0;
        std::size_t post_solve_hinge_count = 0;
        std::size_t post_solve_bar_count = 0;
        if (post_solve_projection_mode) {
            if (!solver_frame_mode) {
                throw std::runtime_error(
                    "--post-solve-projection requires --solver-frame");
            }
            post_solve_projection =
                shift::runtime::physics::
                    load_prepared_post_solve_body_projection(
                        args.post_solve_projection);
            post_solve_body_count =
                post_solve_projection.bodies.size();
            post_solve_joint_count =
                post_solve_projection.joints.size();
            post_solve_hinge_count =
                post_solve_projection.hinges.size();
            post_solve_bar_count =
                post_solve_projection.bars.size();
            if (post_solve_projection.solver_vector.size() !=
                solver_frame_scalar_count) {
                throw std::runtime_error(
                    "post-solve projection scalar count does not match solver frame");
            }
            if (post_solve_body_count !=
                native_state.physics.workspace.body_count) {
                throw std::runtime_error(
                    "post-solve projection body count does not match physics workspace");
            }
            if (post_solve_joint_count !=
                    native_state.physics.workspace.joint_hinge_count ||
                post_solve_hinge_count !=
                    native_state.physics.workspace.joint_hinge_count ||
                post_solve_bar_count !=
                    native_state.physics.workspace.bar_count) {
                throw std::runtime_error(
                    "post-solve projection constraint counts do not match physics workspace");
            }
            if (args.persist_post_solve_body_state) {
                persistent_post_solve_bodies =
                    post_solve_projection.bodies;
            }
        }

        const auto start =
            std::chrono::steady_clock::now();

        while (loop_policy.should_continue(quit, rendered)) {
            window.poll(
                quit, live_input, quit_reason,
                recompiled_module && args.recompiled_entrypoint_enabled
                    ? recompiled_module.get()
                    : nullptr);

            if (recompiled_module && args.recompiled_entrypoint_enabled) {
                const int result = recompiled_module->run_guest_threads();
                if (result != 0) {
                    throw std::runtime_error(
                        "recompiled guest scheduler failed after " +
                        std::to_string(
                            recompiled_module->dispatched_function_count()) +
                        " P-code function dispatches across " +
                        std::to_string(recompiled_module
                                           ->unique_dispatched_function_count()) +
                        " unique functions: " +
                        recompiled_module->last_error());
                }
            }

            const InputState step_input =
                input_script_mode
                    ? input_script.steps.at(
                        static_cast<size_t>(simulation_steps))
                    : live_input;

            shift::runtime::VehicleControlIntent intent{};
            intent.throttle = step_input.throttle;
            intent.brake = step_input.brake;
            intent.steer_left = step_input.steer_left;
            intent.steer_right = step_input.steer_right;
            native_state.fixed_step(intent);
            if (recompiled_module && args.recompiled_step_enabled) {
                const int result = recompiled_module->call(
                    args.recompiled_step);
                if (result != 0) {
                    throw std::runtime_error(
                        "recompiled P-code step " +
                        format_guest_address(args.recompiled_step) +
                        " failed: " + recompiled_module->last_error());
                }
                ++recompiled_step_invocations;
            }
            if (solver_frame_mode) {
                if (!native_state.physics.participant_ready ||
                    !native_state.physics.participant_identity_join_proven) {
                    throw std::runtime_error(
                        "solver frame lost ready participant identity");
                }
                if (body_solver_export_frame_mode) {
                    const auto body_join =
                        shift::runtime::physics::
                            verify_body_export_matches_builtin_solver_frame(
                                body_solver_export_frame,
                                solver_frame);
                    body_solver_export_max_rhs_join_error =
                        std::max(
                            body_solver_export_max_rhs_join_error,
                            body_join.max_rhs_join_error);
                    body_solver_export_max_matrix_join_error =
                        std::max(
                            body_solver_export_max_matrix_join_error,
                            body_join.max_matrix_join_error);
                    ++body_solver_export_join_steps;
                }
                if (generated_body_constraint_frame_mode) {
                    shift::runtime::physics::
                        GeneratedBodySolverFrameJoinResult generated_join{};
                    if (constraint_sample_relation_frame_mode) {
                        const auto refreshed =
                            shift::runtime::physics::
                                refresh_generated_body_constraint_frame(
                                    generated_body_constraint_frame,
                                    constraint_sample_relation_frame);
                        generated_join =
                            shift::runtime::physics::
                                verify_generated_body_constraint_frame_matches_builtin_solver_frame(
                                    refreshed.frame,
                                    solver_frame);
                        ++constraint_sample_relation_refresh_steps;
                    } else {
                        generated_join =
                            shift::runtime::physics::
                                verify_generated_body_constraint_frame_matches_builtin_solver_frame(
                                    generated_body_constraint_frame,
                                    solver_frame);
                    }
                    generated_body_constraint_max_rhs_join_error =
                        std::max(
                            generated_body_constraint_max_rhs_join_error,
                            generated_join.max_rhs_join_error);
                    generated_body_constraint_max_matrix_join_error =
                        std::max(
                            generated_body_constraint_max_matrix_join_error,
                            generated_join.max_matrix_join_error);
                    ++generated_body_constraint_join_steps;
                }
                if (constraint_relation_reset_frame_mode) {
                    const auto reset_selection =
                        shift::runtime::physics::
                            select_fun_007b3f40_reset_nodes(
                                generated_body_constraint_frame,
                                constraint_sample_relation_frame,
                                constraint_relation_reset_frame);
                    shift::runtime::physics::
                        verify_fun_007b3f40_reset_nodes_match(
                            reset_selection,
                            solver_frame.reset_nodes);
                    ++constraint_relation_reset_selection_steps;
                }
                const auto solver_result =
                    shift::runtime::physics::
                        execute_prepared_builtin_solver_frame(
                            solver_frame);
                solver_frame_max_oracle_error =
                    std::max(
                        solver_frame_max_oracle_error,
                        solver_result.max_absolute_error);
                ++solver_frame_steps;
                if (post_solve_projection_mode) {
                    const auto projection_result =
                        args.persist_post_solve_body_state
                            ? shift::runtime::physics::
                                execute_post_solve_body_projection_with_state(
                                    post_solve_projection,
                                    solver_result.solution,
                                    persistent_post_solve_bodies)
                            : shift::runtime::physics::
                                execute_post_solve_body_projection_with_solution(
                                    post_solve_projection,
                                    solver_result.solution);
                    post_solve_max_oracle_error =
                        std::max(
                            post_solve_max_oracle_error,
                            projection_result.max_absolute_error);
                    post_solve_max_solver_join_error =
                        std::max(
                            post_solve_max_solver_join_error,
                            projection_result.max_solver_vector_join_error);
                    post_solve_max_delta_error =
                        std::max(
                            post_solve_max_delta_error,
                            projection_result.max_delta_error);
                    if (args.persist_post_solve_body_state) {
                        persistent_post_solve_bodies =
                            projection_result.bodies;
                        ++persistent_post_solve_body_steps;
                    }
                    ++post_solve_projection_steps;
                }
            }
            ++simulation_steps;

            if (!runtime.frame()) break;
            ++rendered;
        }

        vk_check(vkDeviceWaitIdle(runtime.device),
                 "vkDeviceWaitIdle failed");

        const auto elapsed_ms =
            std::chrono::duration_cast<
                std::chrono::milliseconds>(
                std::chrono::steady_clock::now() -
                start).count();

        size_t texture_count = 0;
        bool has_cube = false;
        for (const auto& draw : runtime.material_draws) {
            texture_count += draw.texture_images.size();
            has_cube =
                has_cube || draw.cube_image.handle !=
                            VK_NULL_HANDLE;
        }

        const auto material_draw_count = runtime.material_draws.size();
        const auto depth_buffer_count = runtime.depth_images.size();
        const std::string loop_exit_reason = !runtime.frame_stop_reason.empty()
            ? runtime.frame_stop_reason
            : !quit_reason.empty()
                ? quit_reason
                : (loop_policy.frame_limit_enabled && rendered >= frame_limit
                       ? "frame_limit"
                       : "loop_condition");
        runtime.destroy();
        window.destroy();
        const auto validation_errors = runtime.validation.error_count();
        const auto guest_scheduler_state = recompiled_module
            ? recompiled_module->guest_scheduler_snapshot()
            : shift::runtime::RecompiledGuestSchedulerSnapshot{};

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeRuntimeFrameLoop/1\",\n"
            << "  \"frames_rendered\": "
            << rendered << ",\n"
            << "  \"loop_exit_reason\": \""
            << loop_exit_reason << "\",\n"
            << "  \"recompiled_pcode_module_loaded\": "
            << (recompiled_module ? "true" : "false") << ",\n"
            << "  \"recompiled_pcode_supplement_count\": "
            << args.recompiled_supplement_modules.size() << ",\n"
            << "  \"recompiled_pe_image_loaded\": "
            << (recompiled_pe_image_loaded ? "true" : "false") << ",\n"
            << "  \"recompiled_pe_image_base\": \""
            << (recompiled_pe_image_loaded
                    ? format_guest_address(recompiled_pe_image_info.image_base)
                    : std::string())
            << "\",\n"
            << "  \"recompiled_pe_image_size\": "
            << recompiled_pe_image_info.image_size << ",\n"
            << "  \"recompiled_pe_entry_point\": \""
            << (recompiled_pe_image_loaded
                    ? format_guest_address(recompiled_pe_image_info.entry_point)
                    : std::string())
            << "\",\n"
            << "  \"recompiled_pe_entry_point_invocations\": "
            << recompiled_pe_entry_point_invocations << ",\n"
            << "  \"recompiled_pe_entry_point_complete\": "
            << (recompiled_module && args.recompiled_entrypoint_enabled &&
                        recompiled_module->pe32_entry_point_complete()
                    ? "true"
                    : "false")
            << ",\n"
            << "  \"recompiled_guest_scheduler\": \""
            << (recompiled_module && args.recompiled_entrypoint_enabled
                    ? "cooperative-host-coroutines"
                    : "disabled")
            << "\",\n"
            << "  \"guest_d3d9_device\": {\n"
            << "    \"bound\": "
            << (runtime.guest_d3d9_device_bound ? "true" : "false")
            << ",\n"
            << "    \"focus_window\": \""
            << format_guest_address(runtime.guest_d3d9_focus_window)
            << "\",\n"
            << "    \"behavior_flags\": "
            << runtime.guest_d3d9_behavior_flags << ",\n"
            << "    \"presentation_parameters\": {\n"
            << "      \"back_buffer_width\": "
            << runtime.guest_d3d9_presentation.back_buffer_width << ",\n"
            << "      \"back_buffer_height\": "
            << runtime.guest_d3d9_presentation.back_buffer_height << ",\n"
            << "      \"back_buffer_format\": "
            << runtime.guest_d3d9_presentation.back_buffer_format << ",\n"
            << "      \"back_buffer_count\": "
            << runtime.guest_d3d9_presentation.back_buffer_count << ",\n"
            << "      \"multisample_type\": "
            << runtime.guest_d3d9_presentation.multisample_type << ",\n"
            << "      \"multisample_quality\": "
            << runtime.guest_d3d9_presentation.multisample_quality << ",\n"
            << "      \"swap_effect\": "
            << runtime.guest_d3d9_presentation.swap_effect << ",\n"
            << "      \"device_window\": \""
            << format_guest_address(
                   runtime.guest_d3d9_presentation.device_window)
            << "\",\n"
            << "      \"windowed\": "
            << (runtime.guest_d3d9_presentation.windowed != 0
                    ? "true"
                    : "false")
            << ",\n"
            << "      \"enable_auto_depth_stencil\": "
            << (runtime.guest_d3d9_presentation.enable_auto_depth_stencil != 0
                    ? "true"
                    : "false")
            << ",\n"
            << "      \"auto_depth_stencil_format\": "
            << runtime.guest_d3d9_presentation.auto_depth_stencil_format
            << ",\n"
            << "      \"flags\": "
            << runtime.guest_d3d9_presentation.flags << ",\n"
            << "      \"fullscreen_refresh_rate\": "
            << runtime.guest_d3d9_presentation.fullscreen_refresh_rate
            << ",\n"
            << "      \"presentation_interval\": "
            << runtime.guest_d3d9_presentation.presentation_interval << "\n"
            << "    },\n"
            << "    \"vulkan_sample_count\": "
            << static_cast<uint32_t>(runtime.guest_sample_count) << ",\n"
            << "    \"vulkan_depth_format\": "
            << static_cast<uint32_t>(runtime.depth_format) << "\n"
            << "  },\n"
            << "  \"recompiled_guest_scheduler_state\": {\n"
            << "    \"entry_point_started\": "
            << (guest_scheduler_state.entry_point_started ? "true" : "false")
            << ",\n"
            << "    \"entry_point_complete\": "
            << (guest_scheduler_state.entry_point_complete ? "true" : "false")
            << ",\n"
            << "    \"main_thread_started\": "
            << (guest_scheduler_state.main_thread_started ? "true" : "false")
            << ",\n"
            << "    \"main_thread_completed\": "
            << (guest_scheduler_state.main_thread_completed ? "true" : "false")
            << ",\n"
            << "    \"main_thread_waiting\": "
            << (guest_scheduler_state.main_thread_waiting ? "true" : "false")
            << ",\n"
            << "    \"main_thread_runnable\": "
            << (guest_scheduler_state.main_thread_runnable ? "true" : "false")
            << ",\n"
            << "    \"main_thread_exit_requested\": "
            << (guest_scheduler_state.main_thread_exit_requested ? "true" : "false")
            << ",\n"
            << "    \"main_thread_wait_handle\": \""
            << format_guest_address(guest_scheduler_state.main_thread_wait_handle)
            << "\",\n"
            << "    \"main_thread_wait_result\": \""
            << format_guest_address(guest_scheduler_state.main_thread_wait_result)
            << "\",\n"
            << "    \"main_thread_current_function\": \""
            << format_guest_address(
                   guest_scheduler_state.main_thread_current_function)
            << "\",\n"
            << "    \"main_thread_call_stack\": "
            << format_guest_call_stack(
                   guest_scheduler_state.main_thread_call_stack)
            << ",\n"
            << "    \"main_thread_recent_functions\": "
            << format_guest_call_stack(
                   guest_scheduler_state.main_thread_recent_functions)
            << ",\n"
            << "    \"ui_state_gate_trace_enabled\": "
            << (guest_scheduler_state.ui_state_gate_trace_enabled
                    ? "true"
                    : "false")
            << ",\n"
            << "    \"ui_state_gate_trace_truncated\": "
            << (guest_scheduler_state.ui_state_gate_trace_truncated
                    ? "true"
                    : "false")
            << ",\n"
            << "    \"ui_state_gate_trace\": "
            << format_ui_state_gate_trace(
                   guest_scheduler_state.ui_state_gate_trace)
            << ",\n"
            << "    \"d3d9_create_device_attempted\": "
            << (guest_scheduler_state.d3d9_create_device_attempted
                    ? "true"
                    : "false")
            << ",\n"
            << "    \"d3d9_create_device_callback_called\": "
            << (guest_scheduler_state.d3d9_create_device_callback_called
                    ? "true"
                    : "false")
            << ",\n"
            << "    \"d3d9_create_device_hresult\": \""
            << format_guest_address(
                   guest_scheduler_state.d3d9_create_device_hresult)
            << "\",\n"
            << "    \"d3d9_create_device_rejection\": "
            << format_json_string(
                   guest_scheduler_state.d3d9_create_device_rejection)
            << ",\n"
            << "    \"d3d9_clear_request\": {\"call_count\": "
            << guest_scheduler_state.d3d9_clear_call_count
            << ", \"flags\": \""
            << format_guest_address(
                   guest_scheduler_state.d3d9_last_clear_flags)
            << "\", \"color\": \""
            << format_guest_address(
                   guest_scheduler_state.d3d9_last_clear_color)
            << "\", \"depth_bits\": \""
            << format_guest_address(
                   guest_scheduler_state.d3d9_last_clear_depth_bits)
            << "\", \"stencil\": "
            << guest_scheduler_state.d3d9_last_clear_stencil
            << ", \"rect_count\": "
            << guest_scheduler_state.d3d9_last_clear_rect_count << "},\n"
            << "    \"d3d9_vulkan_bridge\": {\"clear_requests\": "
            << runtime.guest_d3d9_clear_request_count
            << ", \"present_requests\": "
            << runtime.guest_d3d9_present_request_count
            << ", \"clear_submissions\": "
            << runtime.guest_d3d9_vulkan_clear_submission_count
            << ", \"present_submissions\": "
            << runtime.guest_d3d9_vulkan_present_submission_count
            << ", \"pending_presents\": "
            << (runtime.guest_d3d9_present_request_count -
                runtime.guest_d3d9_vulkan_present_submission_count)
            << ", \"guest_draw_translation\": false},\n"
            << "    \"last_load_library\": {\"name\": "
            << format_json_string(
                   guest_scheduler_state.last_load_library_name)
            << ", \"handle\": \""
            << format_guest_address(
                   guest_scheduler_state.last_load_library_handle)
            << "\", \"last_error\": "
            << guest_scheduler_state.last_load_library_error << "},\n"
            << "    \"guest_call_trace_enabled\": "
            << (guest_scheduler_state.guest_call_trace_enabled
                    ? "true"
                    : "false")
            << ",\n"
            << "    \"guest_call_trace_truncated\": "
            << (guest_scheduler_state.guest_call_trace_truncated
                    ? "true"
                    : "false")
            << ",\n"
            << "    \"guest_call_trace_caller\": \""
            << format_guest_address(
                   guest_scheduler_state.guest_call_trace_caller)
            << "\",\n"
            << "    \"guest_call_trace_targets\": "
            << format_guest_call_trace_addresses(
                   guest_scheduler_state.guest_call_trace_targets)
            << ",\n"
            << "    \"guest_call_trace_imports\": "
            << format_guest_call_trace_imports(
                   guest_scheduler_state.guest_call_trace_imports)
            << ",\n"
            << "    \"guest_call_trace_slot_offsets\": "
            << format_guest_call_trace_addresses(
                   guest_scheduler_state.guest_call_trace_slot_offsets)
            << ",\n"
            << "    \"guest_call_trace_target_slot_offsets\": "
            << format_guest_call_trace_addresses(
                   guest_scheduler_state
                       .guest_call_trace_target_slot_offsets)
            << ",\n"
            << "    \"guest_call_trace_stack_slot_offsets\": "
            << format_guest_call_trace_addresses(
                   guest_scheduler_state.guest_call_trace_stack_slot_offsets)
            << ",\n"
            << "    \"guest_call_trace_string_slot_offsets\": "
            << format_guest_call_trace_addresses(
                   guest_scheduler_state.guest_call_trace_string_slot_offsets)
            << ",\n"
            << "    \"guest_call_trace\": "
            << format_guest_call_trace(
                   guest_scheduler_state.guest_call_trace)
            << ",\n"
            << "    \"ready_thread_count\": "
            << guest_scheduler_state.ready_thread_count << ",\n"
            << "    \"worker_thread_count\": "
            << guest_scheduler_state.worker_thread_count << ",\n"
            << "    \"worker_waiting_count\": "
            << guest_scheduler_state.worker_waiting_count << ",\n"
            << "    \"worker_runnable_count\": "
            << guest_scheduler_state.worker_runnable_count << ",\n"
            << "    \"worker_completed_count\": "
            << guest_scheduler_state.worker_completed_count << "\n"
            << "  },\n"
            << "  \"recompiled_pe_section_count\": "
            << recompiled_pe_image_info.section_count << ",\n"
            << "  \"recompiled_pe_import_module_count\": "
            << recompiled_pe_image_info.import_module_count << ",\n"
            << "  \"recompiled_pe_import_function_count\": "
            << recompiled_pe_image_info.import_function_count << ",\n"
            << "  \"recompiled_pe_import_stub_base\": \""
            << (recompiled_pe_image_loaded &&
                        recompiled_pe_image_info.import_function_count != 0
                    ? format_guest_address(
                          recompiled_pe_image_info.import_stub_base)
                    : std::string())
            << "\",\n"
            << "  \"recompiled_pcode_step_address\": \""
            << (recompiled_module && args.recompiled_step_enabled
                    ? format_guest_address(args.recompiled_step)
                    : std::string())
            << "\",\n"
            << "  \"recompiled_pcode_step_invocations\": "
            << recompiled_step_invocations << ",\n"
            << "  \"recompiled_pcode_functions_dispatched\": "
            << (recompiled_module
                    ? recompiled_module->dispatched_function_count()
                    : 0)
            << ",\n"
            << "  \"recompiled_pcode_unique_functions_dispatched\": "
            << (recompiled_module
                    ? recompiled_module->unique_dispatched_function_count()
                    : 0)
            << ",\n"
            << "  \"recompiled_pcode_frozen_corpus_function_count\": "
            << kFrozenRetailPcodeFunctionCount << ",\n"
            << "  \"recompiled_pcode_unique_function_coverage_percent\": "
            << (recompiled_module
                    ? (100.0 * static_cast<double>(
                                   recompiled_module->unique_dispatched_function_count()) /
                       static_cast<double>(kFrozenRetailPcodeFunctionCount))
                    : 0.0)
            << ",\n"
            << "  \"recompiled_pcode_step_schedule\": \""
            << (args.recompiled_step_enabled
                    ? "one-configured-function-per-native-fixed-step-non-retail"
                    : recompiled_pe_entry_point_invocations != 0
                          ? "PE32-entry-point-once-before-frame-loop"
                          : "disabled")
            << "\",\n"
            << "  \"simulation_steps\": "
            << simulation_steps << ",\n"
            << "  \"fixed_dt\": "
            << kFixedDt << ",\n"
            << "  \"continuous_mode\": "
            << (loop_policy.continuous ? "true" : "false") << ",\n"
            << "  \"frame_limit_enabled\": "
            << (loop_policy.frame_limit_enabled ? "true" : "false") << ",\n"
            << "  \"runtime_loop_schedule\": "
            << "\"one-native-fixed-step-per-render-frame-non-retail\",\n"
            << "  \"input_layer\": "
            << "\"SHIFT.NativeRuntimeInput/1\",\n"
            << "  \"input_source\": \""
            << (input_script_mode ? "script" : "keyboard")
            << "\",\n"
            << "  \"input_script_steps\": "
            << input_script.steps.size() << ",\n"
            << "  \"state_layer\": "
            << "\"SHIFT.NativeRuntimeState/1\",\n"
            << "  \"camera_state_bridge_loaded\": "
            << (camera_state_bridge_loaded ? "true" : "false")
            << ",\n"
            << "  \"camera_active_buffer\": "
            << native_state.camera.active_index << ",\n"
            << "  \"camera_update_in_progress\": "
            << (native_state.camera.update_in_progress ?
                "true" : "false") << ",\n"
            << "  \"camera_snapshot_count\": "
            << native_state.camera.snapshot_count << ",\n"
            << "  \"camera_native_updates\": "
            << native_state.camera.native_update_count << ",\n"
            << "  \"camera_snapshot_mode\": "
            << native_state.camera.last_snapshot.manager_mode << ",\n"
            << "  \"camera_snapshot_id\": "
            << native_state.camera.last_snapshot.camera_id << ",\n"
            << "  \"camera_schedule\": "
            << "\"native-fixed-step-non-retail-timing\",\n"
            << "  \"camera_manager_mode\": "
            << native_state.camera.active().manager_mode << ",\n"
            << "  \"camera_buffer_sub_index\": "
            << native_state.camera.active().buffer_sub_index << ",\n"
            << "  \"camera_id\": "
            << native_state.camera.active().camera_id << ",\n"
            << "  \"camera_active_group\": "
            << native_state.camera.active().active_group << ",\n"
            << "  \"camera_group_restore_value\": "
            << native_state.camera.active().group_restore_value
            << ",\n"
            << "  \"camera_active_buffer_sub_flag\": "
            << static_cast<unsigned>(
                native_state.camera.active().active_buffer_sub_flag)
            << ",\n"
            << "  \"vehicle_control_throttle\": "
            << (native_state.physics.last_input.throttle ?
                "true" : "false") << ",\n"
            << "  \"vehicle_control_brake\": "
            << (native_state.physics.last_input.brake ?
                "true" : "false") << ",\n"
            << "  \"vehicle_control_steer_left\": "
            << (native_state.physics.last_input.steer_left ?
                "true" : "false") << ",\n"
            << "  \"vehicle_control_steer_right\": "
            << (native_state.physics.last_input.steer_right ?
                "true" : "false") << ",\n"
            << "  \"vehicle_control_steer_axis\": "
            << native_state.physics.last_input.steer_axis()
            << ",\n"
            << "  \"vehicle_control_throttle_steps\": "
            << native_state.physics.throttle_steps << ",\n"
            << "  \"vehicle_control_brake_steps\": "
            << native_state.physics.brake_steps << ",\n"
            << "  \"vehicle_control_steer_left_steps\": "
            << native_state.physics.steer_left_steps << ",\n"
            << "  \"vehicle_control_steer_right_steps\": "
            << native_state.physics.steer_right_steps << ",\n"
            << "  \"vehicle_control_neutral_steps\": "
            << native_state.physics.neutral_input_steps << ",\n"
            << "  \"physics_participant_contract_ready\": "
            << (native_state.physics.participant_contract_ready ?
                "true" : "false") << ",\n"
            << "  \"physics_participant_registry_ready\": "
            << (native_state.physics.participant_registry_ready ?
                "true" : "false") << ",\n"
            << "  \"physics_selector_context_separate\": "
            << (native_state.physics.selector_context_separate ?
                "true" : "false") << ",\n"
            << "  \"physics_registry_slot_stride\": "
            << native_state.physics.registry_slot_stride << ",\n"
            << "  \"physics_participant_descriptor_type\": "
            << native_state.physics.participant_descriptor_type
            << ",\n"
            << "  \"physics_participant_identity_join_proven\": "
            << (native_state.physics.participant_identity_join_proven ?
                "true" : "false") << ",\n"
            << "  \"physics_participant_ready\": "
            << (native_state.physics.participant_ready ?
                "true" : "false") << ",\n"
            << "  \"physics_participant_registry_index\": "
            << native_state.physics.participant_registry_index
            << ",\n"
            << "  \"physics_selector_ordinal\": "
            << native_state.physics.selector_ordinal
            << ",\n"
            << "  \"physics_participant_process_state\": "
            << native_state.physics.participant_process_state
            << ",\n"
            << "  \"physics_participant_topology_steps\": "
            << native_state.physics.participant_topology_steps
            << ",\n"
            << "  \"physics_participant_ready_steps\": "
            << native_state.physics.participant_ready_steps
            << ",\n"
            << "  \"physics_participant_unresolved_steps\": "
            << native_state.physics.participant_unresolved_steps
            << ",\n"
            << "  \"physics_participant_index\": "
            << native_state.physics.participant_index
            << ",\n"
            << "  \"physics_participant_mode\": "
            << native_state.physics.participant_mode
            << ",\n"
            << "  \"physics_workspace_ready\": "
            << (native_state.physics.workspace.ready ?
                "true" : "false") << ",\n"
            << "  \"physics_workspace_scalars\": "
            << native_state.physics.workspace.scalar_count
            << ",\n"
            << "  \"physics_workspace_matrix_bytes\": "
            << native_state.physics.workspace.matrix_bytes
            << ",\n"
            << "  \"physics_solver_frame_loaded\": "
            << (solver_frame_mode ? "true" : "false") << ",\n"
            << "  \"physics_solver_frame_scalar_count\": "
            << solver_frame_scalar_count << ",\n"
            << "  \"physics_solver_frame_reset_node_count\": "
            << solver_frame_reset_node_count << ",\n"
            << "  \"physics_solver_effective_reset_node_count\": "
            << solver_frame_reset_node_count
            << ",\n"
            << "  \"physics_solver_frame_reset_nodes_consumed\": true,\n"
            << "  \"physics_solver_frame_steps\": "
            << solver_frame_steps << ",\n"
            << "  \"physics_solver_frame_max_oracle_error\": "
            << solver_frame_max_oracle_error << ",\n"
            << "  \"physics_body_solver_export_frame_loaded\": "
            << (body_solver_export_frame_mode ? "true" : "false")
            << ",\n"
            << "  \"physics_body_solver_export_join_steps\": "
            << body_solver_export_join_steps << ",\n"
            << "  \"physics_body_solver_export_max_rhs_join_error\": "
            << body_solver_export_max_rhs_join_error << ",\n"
            << "  \"physics_body_solver_export_max_matrix_join_error\": "
            << body_solver_export_max_matrix_join_error << ",\n"
            << "  \"physics_generated_body_constraint_frame_loaded\": "
            << (generated_body_constraint_frame_mode ? "true" : "false")
            << ",\n"
            << "  \"physics_generated_body_constraint_body_count\": "
            << generated_body_constraint_body_count << ",\n"
            << "  \"physics_generated_body_constraint_joint_count\": "
            << generated_body_constraint_joint_count << ",\n"
            << "  \"physics_generated_body_constraint_hinge_count\": "
            << generated_body_constraint_hinge_count << ",\n"
            << "  \"physics_generated_body_constraint_bar_count\": "
            << generated_body_constraint_bar_count << ",\n"
            << "  \"physics_generated_body_constraint_join_steps\": "
            << generated_body_constraint_join_steps << ",\n"
            << "  \"physics_generated_body_constraint_native_generation_steps\": "
            << generated_body_constraint_join_steps << ",\n"
            << "  \"physics_generated_body_constraint_max_rhs_join_error\": "
            << generated_body_constraint_max_rhs_join_error << ",\n"
            << "  \"physics_generated_body_constraint_max_matrix_join_error\": "
            << generated_body_constraint_max_matrix_join_error << ",\n"
            << "  \"physics_generated_body_constraint_values_stored_in_packet\": false,\n"
            << "  \"physics_constraint_sample_relation_frame_loaded\": "
            << (constraint_sample_relation_frame_mode ? "true" : "false")
            << ",\n"
            << "  \"physics_constraint_sample_relation_joint_count\": "
            << constraint_sample_relation_joint_count << ",\n"
            << "  \"physics_constraint_sample_relation_hinge_count\": "
            << constraint_sample_relation_hinge_count << ",\n"
            << "  \"physics_constraint_sample_relation_bar_count\": "
            << constraint_sample_relation_bar_count << ",\n"
            << "  \"physics_constraint_sample_relation_refreshed_joint_samples\": "
            << constraint_sample_relation_refreshed_joint_samples << ",\n"
            << "  \"physics_constraint_sample_relation_refreshed_hinge_samples\": "
            << constraint_sample_relation_refreshed_hinge_samples << ",\n"
            << "  \"physics_constraint_sample_relation_refreshed_bar_samples\": "
            << constraint_sample_relation_refreshed_bar_samples << ",\n"
            << "  \"physics_constraint_sample_relation_refresh_steps\": "
            << constraint_sample_relation_refresh_steps << ",\n"
            << "  \"physics_constraint_sample_relation_values_stored_in_packet\": false,\n"
            << "  \"physics_constraint_relation_reset_frame_loaded\": "
            << (constraint_relation_reset_frame_mode ? "true" : "false")
            << ",\n"
            << "  \"physics_constraint_relation_reset_joint_count\": "
            << constraint_relation_reset_joint_count << ",\n"
            << "  \"physics_constraint_relation_reset_hinge_count\": "
            << constraint_relation_reset_hinge_count << ",\n"
            << "  \"physics_constraint_relation_reset_bar_count\": "
            << constraint_relation_reset_bar_count << ",\n"
            << "  \"physics_constraint_relation_reset_selected_joint_count\": "
            << constraint_relation_reset_selected_joint_count << ",\n"
            << "  \"physics_constraint_relation_reset_selected_hinge_count\": "
            << constraint_relation_reset_selected_hinge_count << ",\n"
            << "  \"physics_constraint_relation_reset_selected_bar_count\": "
            << constraint_relation_reset_selected_bar_count << ",\n"
            << "  \"physics_constraint_relation_reset_call_count\": "
            << constraint_relation_reset_call_count << ",\n"
            << "  \"physics_constraint_relation_reset_node_count\": "
            << constraint_relation_reset_node_count << ",\n"
            << "  \"physics_constraint_relation_reset_matches_solver_frame\": "
            << (constraint_relation_reset_matches_solver_frame ?
                "true" : "false") << ",\n"
            << "  \"physics_constraint_relation_reset_selection_steps\": "
            << constraint_relation_reset_selection_steps << ",\n"
            << "  \"physics_constraint_relation_reset_state_offset\": 112,\n"
            << "  \"physics_constraint_relation_reset_tested_bit\": 0,\n"
            << "  \"physics_constraint_relation_reset_nodes_stored_in_packet\": false,\n"
            << "  \"physics_solver_provider_present\": false,\n"
            << "  \"physics_post_solve_projection_loaded\": "
            << (post_solve_projection_mode ? "true" : "false") << ",\n"
            << "  \"physics_post_solve_projection_body_count\": "
            << post_solve_body_count << ",\n"
            << "  \"physics_post_solve_projection_joint_count\": "
            << post_solve_joint_count << ",\n"
            << "  \"physics_post_solve_projection_hinge_count\": "
            << post_solve_hinge_count << ",\n"
            << "  \"physics_post_solve_projection_bar_count\": "
            << post_solve_bar_count << ",\n"
            << "  \"physics_post_solve_projection_steps\": "
            << post_solve_projection_steps << ",\n"
            << "  \"physics_post_solve_projection_max_solver_join_error\": "
            << post_solve_max_solver_join_error << ",\n"
            << "  \"physics_post_solve_projection_max_oracle_error\": "
            << post_solve_max_oracle_error << ",\n"
            << "  \"physics_post_solve_projection_max_delta_error\": "
            << post_solve_max_delta_error << ",\n"
            << "  \"physics_post_solve_persistent_body_state_enabled\": "
            << (args.persist_post_solve_body_state ? "true" : "false")
            << ",\n"
            << "  \"physics_post_solve_persistent_body_state_steps\": "
            << persistent_post_solve_body_steps << ",\n"
            << "  \"physics_solver_post_solve_body_state_applied\": "
            << (post_solve_projection_mode &&
                post_solve_projection_steps == solver_frame_steps &&
                post_solve_projection_steps > 0 ? "true" : "false")
            << ",\n"
            << "  \"physics_solver_persistent_body_accumulator_state_applied\": "
            << (args.persist_post_solve_body_state &&
                persistent_post_solve_body_steps == solver_frame_steps &&
                persistent_post_solve_body_steps > 0 ? "true" : "false")
            << ",\n"
            << "  \"physics_solver_persistent_vehicle_state_applied\": false,\n"
            << "  \"material_mode\": "
            << (runtime.material_mode ? "true" : "false")
            << ",\n"
            << "  \"bundle_set_mode\": "
            << (bundle_set_mode ? "true" : "false")
            << ",\n"
            << "  \"material_draws\": "
            << material_draw_count << ",\n"
            << "  \"bundle_2d_textures\": "
            << texture_count << ",\n"
            << "  \"bundle_cube\": "
            << (has_cube ? "true" : "false") << ",\n"
            << "  \"depth_buffers\": "
            << depth_buffer_count << ",\n"
            << "  \"depth_test\": true,\n"
            << "  \"elapsed_ms\": "
            << elapsed_ms << ",\n"
            << "  \"validation_enabled\": "
            << (args.validation ? "true" : "false") << ",\n"
            << "  \"validation_errors\": " << validation_errors << ",\n"
            << "  \"status\": \""
            << (validation_errors == 0 ? "ok" : "validation-failed") << "\"\n"
            << "}\n";

        return rendered > 0 && validation_errors == 0 ?
            EXIT_SUCCESS : EXIT_FAILURE;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime: "
            << error.what() << "\n";
        runtime.destroy();
        window.destroy();
        return EXIT_FAILURE;
    }
}
