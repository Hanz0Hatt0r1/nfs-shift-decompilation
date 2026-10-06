#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <tlhelp32.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <cwchar>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>

namespace {

constexpr std::uintptr_t kPreferredImageBase = 0x00400000u;
constexpr std::uint32_t kExpectedPeTimestamp = 0x4af2ddcfu;
constexpr std::uint32_t kExpectedImageSize = 0x00995000u;
constexpr std::uint32_t kExpectedEntryPointRva = 0x0050488au;
constexpr std::uint16_t kExpectedSectionCount = 6u;

constexpr std::uintptr_t kPhysicsManagerRva =
    0x00c104e0u - kPreferredImageBase;
constexpr std::uintptr_t kPhysicsManagerVtableRva =
    0x00b04524u - kPreferredImageBase;
constexpr std::uintptr_t kPhysicsTweakerRva =
    0x00c12c40u - kPreferredImageBase;
constexpr std::uintptr_t kPhysicsTweakerTickRateRva =
    0x00c130d2u - kPreferredImageBase;
constexpr std::uintptr_t kPhysicsTweakerLoadAnchorRva =
    0x00710b06u - kPreferredImageBase;
constexpr std::uintptr_t kLoadedRateApplyAnchorRva =
    0x00710c12u - kPreferredImageBase;
constexpr std::uintptr_t kPostPhysicsTweakerLoadFlagOffset = 0x2abu;
constexpr std::uintptr_t kManagerRateOffset = 0x388u;
constexpr std::uintptr_t kManagerReciprocalOffset = 0x38cu;
constexpr std::uintptr_t kManagerRateOver30Offset = 0x390u;
constexpr std::uintptr_t kManagerThirtyOverRateOffset = 0x394u;

struct Options {
    std::wstring process_name = L"SHIFT.exe";
    DWORD pid = 0;
    std::string output = "selected_session_physics_tweaker_rate.json";
    unsigned long long timeout_ms = 30000;
    unsigned stable_samples = 5;
    unsigned sample_interval_ms = 100;
    bool self_test = false;
};

struct RetailIdentity {
    bool read_ok = false;
    bool pe_headers_match = false;
    bool physics_tweaker_load_anchor_matches = false;
    bool loaded_rate_apply_anchor_matches = false;

    bool ready() const noexcept {
        return read_ok && pe_headers_match &&
            physics_tweaker_load_anchor_matches &&
            loaded_rate_apply_anchor_matches;
    }
};

struct Observation {
    bool read_ok = false;
    std::uint32_t manager_vtable = 0;
    std::uint8_t post_load_flag = 0;
    std::uint16_t loaded_rate_hz = 0;
    std::int32_t manager_rate_hz = 0;
    float reciprocal = 0.0f;
    float rate_over_30 = 0.0f;
    float thirty_over_rate = 0.0f;
    bool vtable_matches = false;
    bool loaded_equals_manager_rate = false;
    bool relationships_valid = false;
    bool loaded_rate_ready = false;
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
                out << "\\u" << std::hex << std::setw(4)
                    << std::setfill('0') << static_cast<unsigned>(ch)
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
        CP_UTF8,
        0,
        value.c_str(),
        static_cast<int>(value.size()),
        nullptr,
        0,
        nullptr,
        nullptr);
    if (size <= 0) return {};
    std::string result(static_cast<std::size_t>(size), '\0');
    WideCharToMultiByte(
        CP_UTF8,
        0,
        value.c_str(),
        static_cast<int>(value.size()),
        result.data(),
        size,
        nullptr,
        nullptr);
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
        TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32,
        pid);
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

template <std::size_t N>
bool read_bytes(
    HANDLE process,
    std::uintptr_t address,
    std::array<std::uint8_t, N>& value) {
    SIZE_T bytes = 0;
    return ReadProcessMemory(
               process,
               reinterpret_cast<const void*>(address),
               value.data(),
               value.size(),
               &bytes) != FALSE &&
           bytes == value.size();
}

std::uint32_t load_u32(const std::uint8_t* bytes) {
    std::uint32_t value = 0;
    std::memcpy(&value, bytes, sizeof(value));
    return value;
}

RetailIdentity inspect_retail_identity(
    HANDLE process,
    std::uintptr_t image_base,
    std::size_t module_size) {
    RetailIdentity result{};

    IMAGE_DOS_HEADER dos{};
    if (!read_value(process, image_base, dos) ||
        dos.e_magic != IMAGE_DOS_SIGNATURE || dos.e_lfanew <= 0) {
        return result;
    }

    IMAGE_NT_HEADERS32 nt{};
    if (!read_value(
            process,
            image_base + static_cast<std::uintptr_t>(dos.e_lfanew),
            nt)) {
        return result;
    }

    result.read_ok = true;
    result.pe_headers_match =
        nt.Signature == IMAGE_NT_SIGNATURE &&
        nt.FileHeader.Machine == IMAGE_FILE_MACHINE_I386 &&
        nt.FileHeader.NumberOfSections == kExpectedSectionCount &&
        nt.FileHeader.TimeDateStamp == kExpectedPeTimestamp &&
        nt.OptionalHeader.Magic == IMAGE_NT_OPTIONAL_HDR32_MAGIC &&
        nt.OptionalHeader.ImageBase == kPreferredImageBase &&
        nt.OptionalHeader.SizeOfImage == kExpectedImageSize &&
        nt.OptionalHeader.AddressOfEntryPoint == kExpectedEntryPointRva &&
        module_size == kExpectedImageSize;
    if (!result.pe_headers_match) return result;

    std::array<std::uint8_t, 10> load_anchor{};
    if (read_bytes(
            process,
            image_base + kPhysicsTweakerLoadAnchorRva,
            load_anchor)) {
        const auto expected_tweaker = static_cast<std::uint32_t>(
            image_base + kPhysicsTweakerRva);
        result.physics_tweaker_load_anchor_matches =
            load_anchor[0] == 0xb9 &&
            load_u32(load_anchor.data() + 1) == expected_tweaker &&
            load_anchor[5] == 0xe8 &&
            load_anchor[6] == 0xf0 &&
            load_anchor[7] == 0xc8 &&
            load_anchor[8] == 0x03 &&
            load_anchor[9] == 0x00;
    }

    std::array<std::uint8_t, 15> apply_anchor{};
    if (read_bytes(
            process,
            image_base + kLoadedRateApplyAnchorRva,
            apply_anchor)) {
        const auto expected_rate_global = static_cast<std::uint32_t>(
            image_base + kPhysicsTweakerTickRateRva);
        result.loaded_rate_apply_anchor_matches =
            apply_anchor[0] == 0x0f &&
            apply_anchor[1] == 0xb7 &&
            apply_anchor[2] == 0x05 &&
            load_u32(apply_anchor.data() + 3) == expected_rate_global &&
            apply_anchor[7] == 0x50 &&
            apply_anchor[8] == 0x8b &&
            apply_anchor[9] == 0xce &&
            apply_anchor[10] == 0xe8 &&
            apply_anchor[11] == 0x4f &&
            apply_anchor[12] == 0xe5 &&
            apply_anchor[13] == 0xff &&
            apply_anchor[14] == 0xff;
    }

    return result;
}

bool close_float(float actual, double expected) {
    if (!std::isfinite(actual) || !std::isfinite(expected)) return false;
    const double delta = std::fabs(static_cast<double>(actual) - expected);
    const double scale = std::max(1.0, std::fabs(expected));
    return delta <= 1.0e-6 * scale;
}

void evaluate_observation(
    Observation& value,
    std::uint32_t expected_vtable,
    bool retail_identity_ready) {
    value.vtable_matches =
        value.read_ok && value.manager_vtable == expected_vtable;
    value.loaded_equals_manager_rate =
        value.read_ok && value.loaded_rate_hz > 0 &&
        value.manager_rate_hz > 0 &&
        static_cast<std::int32_t>(value.loaded_rate_hz) ==
            value.manager_rate_hz;

    if (value.read_ok && value.manager_rate_hz > 0) {
        const double rate = static_cast<double>(value.manager_rate_hz);
        value.relationships_valid =
            close_float(value.reciprocal, 1.0 / rate) &&
            close_float(value.rate_over_30, rate / 30.0) &&
            close_float(value.thirty_over_rate, 30.0 / rate);
    } else {
        value.relationships_valid = false;
    }

    // Selected-session loaded-rate admission is intentionally independent of
    // the *current* +0x388 value. FUN_007117e0 can adapt +0x388 later, so
    // equality is an observation that chooses the next blocker, not a
    // prerequisite for proving what PhysicsTweaker.xml loaded.
    value.loaded_rate_ready =
        retail_identity_ready && value.read_ok && value.vtable_matches &&
        value.post_load_flag == 1 && value.loaded_rate_hz > 0;
}

Observation observe(
    HANDLE process,
    std::uintptr_t image_base,
    const RetailIdentity& identity) {
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
        process,
        manager + kManagerRateOffset,
        value.manager_rate_hz);
    ok = ok && read_value(
        process,
        manager + kManagerReciprocalOffset,
        value.reciprocal);
    ok = ok && read_value(
        process,
        manager + kManagerRateOver30Offset,
        value.rate_over_30);
    ok = ok && read_value(
        process,
        manager + kManagerThirtyOverRateOffset,
        value.thirty_over_rate);
    value.read_ok = ok;

    evaluate_observation(value, expected_vtable, identity.ready());
    return value;
}

void write_report(
    const Options& options,
    bool admission_eligible,
    const std::string& status,
    const std::string& error,
    DWORD pid,
    std::uintptr_t image_base,
    std::size_t image_size,
    const std::wstring& image_path,
    const RetailIdentity& identity,
    const Observation& first,
    const Observation& last,
    unsigned stable_count,
    bool self_test) {
    std::ofstream output(
        options.output,
        std::ios::binary | std::ios::trunc);
    if (!output) {
        throw std::runtime_error(
            "cannot open output JSON: " + options.output);
    }

    const bool stable_loaded_rate =
        stable_count >= options.stable_samples &&
        first.loaded_rate_hz == last.loaded_rate_hz;

    output << std::setprecision(17);
    output << "{\n"
           << "  \"format\": \"SHIFT.SelectedSessionPhysicsTweakerRateSnapshot/1\",\n"
           << "  \"status\": " << json_quote(status) << ",\n"
           << "  \"ready\": "
           << (admission_eligible ? "true" : "false") << ",\n"
           << "  \"admission_eligible\": "
           << (admission_eligible ? "true" : "false") << ",\n"
           << "  \"self_test\": "
           << (self_test ? "true" : "false") << ",\n"
           << "  \"error\": "
           << (error.empty() ? "null" : json_quote(error)) << ",\n"
           << "  \"process\": {\n"
           << "    \"pid\": " << pid << ",\n"
           << "    \"image_base\": \"0x"
           << std::hex << image_base << std::dec << "\",\n"
           << "    \"image_size\": " << image_size << ",\n"
           << "    \"image_path\": "
           << json_quote(narrow(image_path)) << "\n"
           << "  },\n"
           << "  \"retail_identity\": {\n"
           << "    \"pe_timestamp\": \"0x4af2ddcf\",\n"
           << "    \"expected_image_size\": \"0x00995000\",\n"
           << "    \"pinned_pe_sha256\": \"eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1\",\n"
           << "    \"cryptographic_hash_recomputed_at_runtime\": false,\n"
           << "    \"pe_headers_match\": "
           << (identity.pe_headers_match ? "true" : "false") << ",\n"
           << "    \"physics_tweaker_load_anchor_matches\": "
           << (identity.physics_tweaker_load_anchor_matches
                   ? "true" : "false")
           << ",\n"
           << "    \"loaded_rate_apply_anchor_matches\": "
           << (identity.loaded_rate_apply_anchor_matches
                   ? "true" : "false")
           << ",\n"
           << "    \"identity_ready\": "
           << (identity.ready() ? "true" : "false") << "\n"
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
           << "    \"loaded_tick_rate_hz\": "
           << last.loaded_rate_hz << ",\n"
           << "    \"post_load_flag\": "
           << static_cast<unsigned>(last.post_load_flag) << ",\n"
           << "    \"source_backed_manager_vtable_matches\": "
           << (last.vtable_matches ? "true" : "false") << ",\n"
           << "    \"stable_sample_count\": "
           << stable_count << ",\n"
           << "    \"stable_loaded_rate\": "
           << (stable_loaded_rate ? "true" : "false") << "\n"
           << "  },\n"
           << "  \"current_manager\": {\n"
           << "    \"rate_hz\": " << last.manager_rate_hz << ",\n"
           << "    \"reciprocal_seconds\": "
           << last.reciprocal << ",\n"
           << "    \"rate_over_30\": "
           << last.rate_over_30 << ",\n"
           << "    \"thirty_over_rate\": "
           << last.thirty_over_rate << ",\n"
           << "    \"relationships_valid\": "
           << (last.relationships_valid ? "true" : "false") << ",\n"
           << "    \"equals_loaded_tick_rate\": "
           << (last.loaded_equals_manager_rate ? "true" : "false")
           << "\n"
           << "  },\n"
           << "  \"adjudication\": {\n"
           << "    \"physics_tweaker_xml_load_completed_before_observation\": "
           << ((identity.physics_tweaker_load_anchor_matches &&
                last.post_load_flag == 1)
                   ? "true" : "false")
           << ",\n"
           << "    \"loaded_global_applied_to_cphysics_manager_at_initialization\": "
           << (identity.loaded_rate_apply_anchor_matches
                   ? "true" : "false")
           << ",\n"
           << "    \"selected_session_loaded_rate_observed_after_PhysicsTweaker_load\": "
           << (admission_eligible ? "true" : "false") << ",\n"
           << "    \"current_manager_rate_matches_loaded_at_observation\": "
           << (last.loaded_equals_manager_rate ? "true" : "false")
           << ",\n"
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
                throw std::runtime_error(
                    "missing value for " + narrow(std::wstring(name)));
            }
            return argv[++index];
        };

        if (arg == L"--process-name") {
            options.process_name = require_value(L"--process-name");
        } else if (arg == L"--pid") {
            options.pid = static_cast<DWORD>(
                std::stoul(require_value(L"--pid")));
        } else if (arg == L"--output") {
            options.output = narrow(require_value(L"--output"));
        } else if (arg == L"--timeout-ms") {
            options.timeout_ms = std::stoull(
                require_value(L"--timeout-ms"));
        } else if (arg == L"--stable-samples") {
            options.stable_samples = static_cast<unsigned>(
                std::stoul(require_value(L"--stable-samples")));
        } else if (arg == L"--sample-interval-ms") {
            options.sample_interval_ms = static_cast<unsigned>(
                std::stoul(require_value(L"--sample-interval-ms")));
        } else if (arg == L"--self-test") {
            options.self_test = true;
        } else {
            throw std::runtime_error(
                "unknown argument: " + narrow(arg));
        }
    }

    if (options.stable_samples == 0 ||
        options.sample_interval_ms == 0) {
        throw std::runtime_error(
            "stable sample count and interval must be positive");
    }
    return options;
}

int run_self_test(const Options& options) {
    RetailIdentity identity{};
    identity.read_ok = true;
    identity.pe_headers_match = true;
    identity.physics_tweaker_load_anchor_matches = true;
    identity.loaded_rate_apply_anchor_matches = true;

    Observation sample{};
    sample.read_ok = true;
    sample.manager_vtable = 0x00b04524u;
    sample.post_load_flag = 1;
    sample.loaded_rate_hz = 240;
    // Deliberately diverge from the loaded value. This locks the central
    // boundary: selected-session load admission must not silently prove the
    // later adaptive +0x388 manager-rate policy.
    sample.manager_rate_hz = 210;
    sample.reciprocal = 1.0f / 210.0f;
    sample.rate_over_30 = 7.0f;
    sample.thirty_over_rate = 30.0f / 210.0f;
    evaluate_observation(
        sample,
        sample.manager_vtable,
        identity.ready());

    const bool passed =
        sample.loaded_rate_ready &&
        sample.relationships_valid &&
        !sample.loaded_equals_manager_rate;
    write_report(
        options,
        passed,
        passed ? "self-test-passed" : "self-test-failed",
        passed ? std::string{} : "synthetic separation contract failed",
        4242,
        kPreferredImageBase,
        kExpectedImageSize,
        L"synthetic/SHIFT.exe",
        identity,
        sample,
        sample,
        options.stable_samples,
        true);
    return passed ? 0 : 1;
}

}  // namespace

int wmain(int argc, wchar_t** argv) {
    try {
        const Options options = parse_options(argc, argv);
        if (options.self_test) return run_self_test(options);

        const ULONGLONG deadline = GetTickCount64() + options.timeout_ms;
        DWORD pid = options.pid;
        std::uintptr_t image_base = 0;
        std::size_t image_size = 0;
        std::wstring image_path;
        HANDLE process = nullptr;
        RetailIdentity identity{};
        Observation first_ready{};
        Observation last{};
        unsigned stable_count = 0;
        std::uint16_t stable_rate = 0;

        while (GetTickCount64() <= deadline) {
            if (!pid) pid = find_process_id(options.process_name);
            if (!pid) {
                std::this_thread::sleep_for(
                    std::chrono::milliseconds(50));
                continue;
            }

            if (!image_base && !find_main_module(
                    pid,
                    options.process_name,
                    image_base,
                    image_size,
                    image_path)) {
                if (!options.pid) pid = 0;
                std::this_thread::sleep_for(
                    std::chrono::milliseconds(50));
                continue;
            }

            if (!process) {
                process = OpenProcess(
                    PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
                    FALSE,
                    pid);
                if (!process) {
                    image_base = 0;
                    if (!options.pid) pid = 0;
                    std::this_thread::sleep_for(
                        std::chrono::milliseconds(50));
                    continue;
                }
                identity = inspect_retail_identity(
                    process,
                    image_base,
                    image_size);
            }

            last = observe(process, image_base, identity);
            if (last.loaded_rate_ready) {
                if (stable_count == 0 ||
                    last.loaded_rate_hz != stable_rate) {
                    stable_rate = last.loaded_rate_hz;
                    first_ready = last;
                    stable_count = 1;
                } else {
                    ++stable_count;
                }

                if (stable_count >= options.stable_samples) {
                    CloseHandle(process);
                    write_report(
                        options,
                        true,
                        "selected-session-rate-observed",
                        {},
                        pid,
                        image_base,
                        image_size,
                        image_path,
                        identity,
                        first_ready,
                        last,
                        stable_count,
                        false);
                    return 0;
                }
            } else {
                stable_count = 0;
                stable_rate = 0;
            }

            std::this_thread::sleep_for(
                std::chrono::milliseconds(
                    options.sample_interval_ms));
        }

        if (process) CloseHandle(process);
        write_report(
            options,
            false,
            "selected-session-rate-not-observed",
            "timeout before a stable post-PhysicsTweaker-load rate snapshot",
            pid,
            image_base,
            image_size,
            image_path,
            identity,
            first_ready,
            last,
            stable_count,
            false);
        return 2;
    } catch (const std::exception& exc) {
        std::cerr
            << "selected-session rate snapshot failed: "
            << exc.what() << "\n";
        return 1;
    }
}
