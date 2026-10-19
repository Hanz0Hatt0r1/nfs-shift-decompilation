#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace shift::runtime {

struct Pe32ImageInfo {
    uint32_t image_base = 0;
    uint32_t image_size = 0;
    uint32_t entry_point = 0;
    uint16_t section_count = 0;
    uint32_t import_module_count = 0;
    uint32_t import_function_count = 0;
    uint32_t import_stub_base = 0;
};

struct RecompiledUiStateGateTraceEvent {
    uint64_t dispatch_count = 0;
    uint32_t thread_id = 0;
    uint32_t function = 0;
    uint32_t caller = 0;
    uint32_t ecx_entry = 0;
    uint32_t eax_entry = 0;
    uint32_t esp_entry = 0;
    uint32_t gate_state_word = 0;
    uint32_t gate_callback_object = 0;
    uint64_t gate_state_last_writer_sequence = 0;
    uint64_t gate_state_last_writer_dispatch_count = 0;
    uint32_t gate_state_last_writer_function = 0;
    uint32_t gate_state_last_writer_ecx = 0;
    uint32_t gate_state_last_writer_caller_function = 0;
    uint32_t gate_state_last_writer_call_return_address = 0;
    uint32_t gate_state_last_writer_caller_return_address = 0;
    uint32_t gate_state_last_writer_ancestor_function = 0;
    uint32_t gate_state_last_writer_ancestor_caller_function = 0;
    uint32_t gate_state_last_writer_ancestor_return_address = 0;
    uint32_t gate_state_last_writer_thread_id = 0;
    uint32_t gate_state_last_writer_address = 0;
    uint32_t gate_state_last_writer_size = 0;
    uint32_t gate_state_last_writer_word_value = 0;
    uint32_t callback_target = 0;
    uint32_t eax_return = 0;
    uint8_t helper_flag_byte = 0;
    bool has_gate_state_word = false;
    bool has_gate_callback_object = false;
    bool has_gate_state_last_writer = false;
    bool has_gate_state_last_writer_ecx = false;
    bool has_gate_state_last_writer_caller_function = false;
    bool has_gate_state_last_writer_call_return_address = false;
    bool has_gate_state_last_writer_caller_return_address = false;
    bool has_gate_state_last_writer_ancestor_function = false;
    bool has_gate_state_last_writer_ancestor_caller_function = false;
    bool has_gate_state_last_writer_ancestor_return_address = false;
    bool has_callback_target = false;
    bool has_helper_flag_byte = false;
    bool completed = false;
};

struct RecompiledGuestCallTraceEvent {
    uint64_t dispatch_count = 0;
    uint32_t thread_id = 0;
    uint32_t function = 0;
    uint32_t caller = 0;
    uint32_t return_address = 0;
    uint32_t ecx_entry = 0;
    uint32_t eax_entry = 0;
    uint32_t edx_entry = 0;
    std::string import_name;
    bool has_return_address = false;
    bool is_import = false;
};

struct RecompiledGuestD3d9PresentationParameters {
    uint32_t back_buffer_width = 0;
    uint32_t back_buffer_height = 0;
    uint32_t back_buffer_format = 0;
    uint32_t back_buffer_count = 0;
    uint32_t multisample_type = 0;
    uint32_t multisample_quality = 0;
    uint32_t swap_effect = 0;
    uint32_t device_window = 0;
    uint32_t windowed = 0;
    uint32_t enable_auto_depth_stencil = 0;
    uint32_t auto_depth_stencil_format = 0;
    uint32_t flags = 0;
    uint32_t fullscreen_refresh_rate = 0;
    uint32_t presentation_interval = 0;
};

using RecompiledGuestD3d9CreateDeviceCallback = bool (*) (
    void* context, uint32_t focus_window, uint32_t behavior_flags,
    RecompiledGuestD3d9PresentationParameters& parameters,
    std::string& error);
using RecompiledGuestD3d9CreateTextureCallback = bool (*) (
    void* context, uint32_t guest_texture, uint32_t guest_device,
    uint32_t width, uint32_t height, uint32_t levels, uint32_t usage,
    uint32_t format, uint32_t pool, std::string& error);
using RecompiledGuestD3d9ReleaseTextureCallback = void (*) (
    void* context, uint32_t guest_texture);
using RecompiledGuestD3d9CreateVertexBufferCallback = bool (*) (
    void* context, uint32_t guest_buffer, uint32_t guest_device,
    uint32_t size, uint32_t usage, uint32_t fvf, uint32_t pool,
    std::string& error);
using RecompiledGuestD3d9UpdateVertexBufferCallback = bool (*) (
    void* context, uint32_t guest_buffer, uint32_t offset,
    const uint8_t* data, size_t size, std::string& error);
using RecompiledGuestD3d9ReleaseVertexBufferCallback = void (*) (
    void* context, uint32_t guest_buffer);

struct RecompiledGuestD3d9AdapterInfo {
    // D3DCAPS9 is 76 little-endian 32-bit words, including its float fields.
    std::array<uint32_t, 76> caps{};
    uint32_t vendor_id = 0;
    uint32_t device_id = 0;
    std::string description;
    bool supports_bgra8_surface = false;
    bool supports_bgra8_texture = false;
    bool supports_d24s8_depth_stencil = false;
    uint32_t bgra8_sample_count_mask = 0;
    uint32_t d24s8_sample_count_mask = 0;
    void* backend_context = nullptr;
    RecompiledGuestD3d9CreateDeviceCallback create_device = nullptr;
    RecompiledGuestD3d9CreateTextureCallback create_texture = nullptr;
    RecompiledGuestD3d9ReleaseTextureCallback release_texture = nullptr;
    RecompiledGuestD3d9CreateVertexBufferCallback create_vertex_buffer = nullptr;
    RecompiledGuestD3d9UpdateVertexBufferCallback update_vertex_buffer = nullptr;
    RecompiledGuestD3d9ReleaseVertexBufferCallback release_vertex_buffer = nullptr;
};

struct RecompiledGuestSchedulerSnapshot {
    bool entry_point_started = false;
    bool entry_point_complete = false;
    bool main_thread_started = false;
    bool main_thread_completed = false;
    bool main_thread_waiting = false;
    bool main_thread_runnable = false;
    bool main_thread_exit_requested = false;
    uint32_t main_thread_wait_handle = 0;
    uint32_t main_thread_wait_result = 0;
    uint32_t main_thread_current_function = 0;
    std::vector<uint32_t> main_thread_call_stack;
    std::vector<uint32_t> main_thread_recent_functions;
    bool ui_state_gate_trace_enabled = false;
    bool ui_state_gate_trace_truncated = false;
    std::vector<RecompiledUiStateGateTraceEvent> ui_state_gate_trace;
    bool guest_call_trace_enabled = false;
    bool guest_call_trace_truncated = false;
    uint32_t guest_call_trace_caller = 0;
    std::vector<RecompiledGuestCallTraceEvent> guest_call_trace;
    size_t ready_thread_count = 0;
    size_t worker_thread_count = 0;
    size_t worker_waiting_count = 0;
    size_t worker_runnable_count = 0;
    size_t worker_completed_count = 0;
    bool d3d9_create_device_attempted = false;
    bool d3d9_create_device_callback_called = false;
    uint32_t d3d9_create_device_hresult = UINT32_MAX;
    std::string d3d9_create_device_rejection;
    uint32_t d3d9_clear_call_count = 0;
    uint32_t d3d9_last_clear_flags = 0;
    uint32_t d3d9_last_clear_color = 0;
    uint32_t d3d9_last_clear_depth_bits = 0;
    uint32_t d3d9_last_clear_stencil = 0;
    uint32_t d3d9_last_clear_rect_count = 0;
    std::string last_load_library_name;
    uint32_t last_load_library_handle = 0;
    uint32_t last_load_library_error = 0;
};

class RecompiledPcodeModule {
public:
    explicit RecompiledPcodeModule(const std::string& shared_object_path);
    ~RecompiledPcodeModule();

    RecompiledPcodeModule(const RecompiledPcodeModule&) = delete;
    RecompiledPcodeModule& operator=(const RecompiledPcodeModule&) = delete;
    RecompiledPcodeModule(RecompiledPcodeModule&&) = delete;
    RecompiledPcodeModule& operator=(RecompiledPcodeModule&&) = delete;

    int call(uint32_t guest_address);
    Pe32ImageInfo load_pe32_image(const std::string& path);
    int call_pe32_entry_point();
    int run_guest_threads();
    bool pe32_entry_point_complete() const;
    RecompiledGuestSchedulerSnapshot guest_scheduler_snapshot() const;
    bool load_supplemental_module(const std::string& shared_object_path);
    bool load_override_module(const std::string& shared_object_path);
    bool set_guest_display_mode(uint32_t width, uint32_t height,
                                uint32_t refresh_rate, uint32_t format);
    bool set_guest_d3d9_adapter_info(
        const RecompiledGuestD3d9AdapterInfo& adapter_info);
    uint64_t dispatched_function_count() const;
    uint64_t unique_dispatched_function_count() const;
    const std::string& last_error() const;

    bool read_guest(const char* space, uint64_t offset, size_t size,
                    uint8_t* output);
    bool write_guest(const char* space, uint64_t offset, size_t size,
                     const uint8_t* input);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace shift::runtime
