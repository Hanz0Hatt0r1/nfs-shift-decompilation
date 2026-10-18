#pragma once

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
    size_t ready_thread_count = 0;
    size_t worker_thread_count = 0;
    size_t worker_waiting_count = 0;
    size_t worker_runnable_count = 0;
    size_t worker_completed_count = 0;
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
