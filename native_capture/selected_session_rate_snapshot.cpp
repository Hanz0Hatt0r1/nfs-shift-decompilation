#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <tlhelp32.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cwchar>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <string>
#include <thread>

namespace {

constexpr std::uintptr_t kPreferredImageBase = 0x00400000u;
constexpr std::uintptr_t kPhysicsManagerRva = 0x00c104e0u - kPreferredImageBase;
constexpr std::uintptr_t kPhysicsManagerVtableRva = 0x00b04524u - kPreferredImageBase;
constexpr std::uintptr_t kPhysicsTweakerTickRateRva = 0x00c130d2u - kPreferredImageBase;
constexpr std::uintptr_t kPostPhysicsTweakerLoadFlagOffset = 0x2abu;
constexpr std::uintptr_t kManagerRateOffset = 0x388u;
constexpr std::uintptr_t kManagerReciprocalOffset = 0x38cu;
constexpr std::uintptr_t kManagerRateOver30Offset = 0x390u;
constexpr std::uintptr_t kManagerThirtyOverRateOffset = 0x394u;

struct Options {
    std::wstring process_name = L"SHIFT.exe";
    std::string output = "selected_session_physics_tweaker_rate.json";
    unsigned long long timeout_ms = 30000;
    unsigned stable_samples = 5;
    unsigned sample_interval_ms = 100;
    bool self_test = false;
};

struct Observation {
    std::uint32_t manager_vtable = 0;
    std::uint8_t post_load_flag = 0;
    std::uint16_t loaded_rate_hz = 0;
    std::uint32_t manager_rate_hz = 0;
    float reciprocal = 0.0f;
    float rate_over_30 = 0.0f;
    float thirty_over_rate = 0.0f;
    bool vtable_matches = false;
    bool relationships_valid = false;
    bool ready = false;
};

std::string json_quote(const std::string& value) {
    std::ostringstream out;
    out << '"';
    for (unsigned char ch : value) {
        switch (ch) {
        case '\\': out << "\\\\"; break;
        case '"': out << "\\\""; break;
        case '\n': out << "\\n"; break;
        case '\r': out << "\\r"; break;
        case '\t': out << "\\t"; break;
        default:
            if (ch < 0x20) {
                out << "\\u" << std::hex << std::setw(4) << std::setfill('0')
                    << static_cast<unsigned>(ch)
                    << std::dec << std::setfill(' ');
            } else {
                out << static_cast<char>(ch);
            }
        }
    }
    out << '"';
    return out.str();
}

std::string narrow(const std::wstring& value) {
    if (value.empty()) return {};
    const int size = WideCharToMultiByte(
        CP_UTF8, 0, value.c_str(), static_cast<int>(value.size()),
        nullptr, 0, nullptr, nullptr);
    if (size <= 0) return {};
    std::string result(static_cast<std::size_t>(size), '\0');
    WideCharToMultiByte(
        CP_UTF8, 0, value.c_str(), static_cast<int>(value.size()),
        result.data(), size, nullptr, nullptr);
    return result;
}

bool iequals(const wchar_t* lhs, const std::wstring& rhs) {
    return lhs && _wcsicmp(lhs, rhs.c_str()) == 0;
}

DWORD find_process_id(const std::wstring& process_name) {
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snapshot == INVALID_HANDLE_VALUE) return 0;
    PROCESSENTRY32W entry{};
    entry.dwSize = sizeof(entry);
    DWORD pid = 0;
    if (Process32FirstW(snapshot, &entry)) {
        do {
            if (iequals(entry.szExeFile, process_name)) {
                pid = entry.th32ProcessID;
                break;
            }
        } while (Process32NextW(snapshot, &entry));
    }
    CloseHandle(snapshot);
    return pid;
}

bool find_main_module(
    DWORD pid,
    const std::wstring& process_name,
    std::uintptr_t& base,
    std::size_t& size,
    std::wstring& path) {
    HANDLE snapshot = CreateToolhelp32Snapshot(
        TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid);
    if (snapshot == INVALID_HANDLE_VALUE) return false;
    MODULEENTRY32W entry{};
    entry.dwSize = sizeof(entry);
    bool found = false;
    if (Module32FirstW(snapshot, &entry)) {
        do {
            if (iequals(entry.szModule, process_name)) {
                base = reinterpret_cast<std::uintptr_t>(entry.modBaseAddr);
                size = static_cast<std::size_t>(entry.modBaseSize);
                path = entry.szExePath;
                found = true;
                break;
            }
        } while (Module32NextW(snapshot, &entry));
    }
    CloseHandle(snapshot);
    return found;
}

template <typename T>
bool read_value(HANDLE process, std::uintptr_t address, T& value) {
    SIZE_T bytes = 0;
    return ReadProcessMemory(
               process,
               reinterpret_cast<const void*>(address),
               &value,
               sizeof(value),
               &bytes) != FALSE &&
           bytes == sizeof(value);
}

bool close_float(float actual, double expected) {
    if (!std::isfinite(actual) || !std::isfinite(expected)) return false;
    const double delta = std::fabs(static_cast<double>(actual) - expected);
    const double scale = std::max(1.0, std::fabs(expected));
    return delta <= 1.0e-5 * scale;
}

Observation observe(HANDLE process, std::uintptr_t image_base) {
    Observation value{};
    const std::uintptr_t manager = image_base + kPhysicsManagerRva;
    const std::uint32_t expected_vtable = static_cast<std::uint32_t>(
        image_base + kPhysicsManagerVtableRva);

    bool ok = true;
    ok = ok && read_value(process, manager, value.manager_vtable);
    ok = ok && read_value(
        process,
        manager + kPostPhysicsTweakerLoadFlagOffset,
        value.post_load_flag);
    ok = ok && read_value(
        process,
        image_base + kPhysicsTweakerTickRateRva,
        value.loaded_rate_hz);
    ok = ok && read_value(
        process, manager + kManagerRateOffset, value.manager_rate_hz);
    ok = ok && read_value(
        process, manager + kManagerReciprocalOffset, value.reciprocal);
    ok = ok && read_value(
        process, manager + kManagerRateOver30Offset, value.rate_over_30);
    ok = ok && read_value(
        process, manager + kManagerThirtyOverRateOffset, value.thirty_over_rate);

    value.vtable_matches = ok && value.manager_vtable == expected_vtable;
    if (ok && value.manager_rate_hz > 0) {
        const double rate = static_cast<double>(value.manager_rate_hz);
        value.relationships_valid =
            close_float(value.reciprocal, 1.0 / rate) &&
            close_float(value.rate_over_30, rate / 30.0) &&
            close_float(value.thirty_over_rate, 30.0 / rate);
    }
    value.ready = ok && value.vtable_matches &&
        value.post_load_flag == 1 && value.loaded_rate_hz > 0 &&
        value.manager_rate_hz > 0 && value.relationships_valid;
    return value;
}

void write_report(
    const Options& options,
    bool ready,
    const std::string& status,
    const std::string& error,
    DWORD pid,
    std::uintptr_t image_base,
    std::size_t image_size,
    const std::wstring& image_path,
    const Observation& first,
    const Observation& last,
    unsigned stable_count,
    bool self_test) {
    std::ofstream output(options.output, std::ios::binary | std::ios::trunc);
    if (!output) {
        throw std::runtime_error("cannot open output JSON: " + options.output);
    }
    output << std::setprecision(17);
    output << "{\n"
           << "  \"format\": \"SHIFT.SelectedSessionPhysicsTweakerRateSnapshot/1\",\n"
           << "  \"status\": " << json_quote(status) << ",\n"
           << "  \"ready\": " << (ready ? "true" : "false") << ",\n"
           << "  \"self_test\": " << (self_test ? "true" : "false") << ",\n"
           << "  \"error\": " << (error.empty() ? "null" : json_quote(error)) << ",\n"
           << "  \"process\": {\n"
           << "    \"pid\": " << pid << ",\n"
           << "    \"image_base\": \"0x" << std::hex << image_base << std::dec << "\",\n"
           << "    \"image_size\": " << image_size << ",\n"
           << "    \"image_path\": " << json_quote(narrow(image_path)) << "\n"
           << "  },\n"
           << "  \"anchors\": {\n"
           << "    \"preferred_image_base\": \"0x00400000\",\n"
           << "    \"cphysics_manager_rva\": \"0x008104e0\",\n"
           << "    \"cphysics_manager_vtable_rva\": \"0x00704524\",\n"
           << "    \"post_physics_tweaker_load_flag_offset\": \"0x2ab\",\n"
           << "    \"physics_tweaker_tick_rate_rva\": \"0x008130d2\",\n"
           << "    \"manager_rate_offset\": \"0x388\"\n"
           << "  },\n"
           << "  \"selected_session\": {\n"
           << "    \"loaded_tick_rate_hz\": " << last.loaded_rate_hz << ",\n"
           << "    \"post_load_flag\": " << static_cast<unsigned>(last.post_load_flag) << ",\n"
           << "    \"source_backed_manager_vtable_matches\": "
           << (last.vtable_matches ? "true" : "false") << ",\n"
           << "    \"stable_sample_count\": " << stable_count << ",\n"
           << "    \"stable_loaded_rate\": "
           << ((stable_count >= options.stable_samples && first.loaded_rate_hz == last.loaded_rate_hz) ? "true" : "false") << "\n"
           << "  },\n"
           << "  \"current_manager\": {\n"
           << "    \"rate_hz\": " << last.manager_rate_hz << ",\n"
           << "    \"reciprocal_seconds\": " << last.reciprocal << ",\n"
           << "    \"rate_over_30\": " << last.rate_over_30 << ",\n"
           << "    \"thirty_over_rate\": " << last.thirty_over_rate << ",\n"
           << "    \"relationships_valid\": "
           << (last.relationships_valid ? "true" : "false") << ",\n"
           << "    \"equals_loaded_tick_rate\": "
           << (last.manager_rate_hz == last.loaded_rate_hz ? "true" : "false") << "\n"
           << "  },\n"
           << "  \"adjudication\": {\n"
           << "    \"selected_session_loaded_rate_observed_after_PhysicsTweaker_load\": "
           << (ready ? "true" : "false") << ",\n"
           << "    \"constructor_default_180_used_as_admission_basis\": false,\n"
           << "    \"current_manager_rate_is_assumed_constant\": false,\n"
           << "    \"retail_inner_substep_execution_admitted\": false\n"
           << "  }\n"
           << "}\n";
}

Options parse_options(int argc, wchar_t** argv) {
    Options options{};
    for (int index = 1; index < argc; ++index) {
        const std::wstring arg = argv[index];
        auto require_value = [&](const wchar_t* name) -> std::wstring {
            if (index + 1 >= argc) {
                throw std::runtime_error("missing value for " + narrow(name));
            }
            return argv[++index];
        };
        if (arg == L"--process-name") {
            options.process_name = require_value(L"--process-name");
        } else if (arg == L"--output") {
            options.output = narrow(require_value(L"--output"));
        } else if (arg == L"--timeout-ms") {
            options.timeout_ms = std::stoull(require_value(L"--timeout-ms"));
        } else if (arg == L"--stable-samples") {
            options.stable_samples = static_cast<unsigned>(
                std::stoul(require_value(L"--stable-samples")));
        } else if (arg == L"--sample-interval-ms") {
            options.sample_interval_ms = static_cast<unsigned>(
                std::stoul(require_value(L"--sample-interval-ms")));
        } else if (arg == L"--self-test") {
            options.self_test = true;
        } else {
            throw std::runtime_error("unknown argument: " + narrow(arg));
        }
    }
    if (options.stable_samples == 0 || options.sample_interval_ms == 0) {
        throw std::runtime_error("stable sample count and interval must be positive");
    }
    return options;
}

int run_self_test(const Options& options) {
    Observation sample{};
    sample.manager_vtable = 0x00b04524u;
    sample.post_load_flag = 1;
    sample.loaded_rate_hz = 240;
    sample.manager_rate_hz = 240;
    sample.reciprocal = 1.0f / 240.0f;
    sample.rate_over_30 = 8.0f;
    sample.thirty_over_rate = 0.125f;
    sample.vtable_matches = true;
    sample.relationships_valid = true;
    sample.ready = true;
    write_report(
        options, true, "selected-session-rate-observed", {}, 4242,
        kPreferredImageBase, 0x00864000u, L"synthetic/SHIFT.exe",
        sample, sample, options.stable_samples, true);
    return 0;
}

}  // namespace

int wmain(int argc, wchar_t** argv) {
    try {
        const Options options = parse_options(argc, argv);
        if (options.self_test) return run_self_test(options);

        const ULONGLONG deadline = GetTickCount64() + options.timeout_ms;
        DWORD pid = 0;
        std::uintptr_t image_base = 0;
        std::size_t image_size = 0;
        std::wstring image_path;
        HANDLE process = nullptr;
        Observation first_ready{};
        Observation last{};
        unsigned stable_count = 0;
        std::uint16_t stable_rate = 0;

        while (GetTickCount64() <= deadline) {
            if (!pid) pid = find_process_id(options.process_name);
            if (!pid) {
                std::this_thread::sleep_for(std::chrono::milliseconds(50));
                continue;
            }
            if (!image_base && !find_main_module(
                    pid, options.process_name, image_base, image_size, image_path)) {
                pid = 0;
                std::this_thread::sleep_for(std::chrono::milliseconds(50));
                continue;
            }
            if (!process) {
                process = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid);
                if (!process) {
                    image_base = 0;
                    pid = 0;
                    std::this_thread::sleep_for(std::chrono::milliseconds(50));
                    continue;
                }
            }

            last = observe(process, image_base);
            if (last.ready) {
                if (stable_count == 0 || last.loaded_rate_hz != stable_rate) {
                    stable_rate = last.loaded_rate_hz;
                    first_ready = last;
                    stable_count = 1;
                } else {
                    ++stable_count;
                }
                if (stable_count >= options.stable_samples) {
                    CloseHandle(process);
                    write_report(
                        options, true, "selected-session-rate-observed", {},
                        pid, image_base, image_size, image_path,
                        first_ready, last, stable_count, false);
                    return 0;
                }
            } else {
                stable_count = 0;
                stable_rate = 0;
            }
            std::this_thread::sleep_for(
                std::chrono::milliseconds(options.sample_interval_ms));
        }

        if (process) CloseHandle(process);
        write_report(
            options, false, "selected-session-rate-not-observed",
            "timeout before a stable post-PhysicsTweaker-load rate snapshot",
            pid, image_base, image_size, image_path,
            first_ready, last, stable_count, false);
        return 2;
    } catch (const std::exception& exc) {
        std::cerr << "selected-session rate snapshot failed: " << exc.what() << "\n";
        return 1;
    }
}
