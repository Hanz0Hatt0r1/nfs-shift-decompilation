#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <algorithm>
#include <cerrno>
#include <chrono>
#include <cctype>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <optional>
#include <sstream>
#include <string>
#include <sys/uio.h>
#include <sys/stat.h>
#include <thread>
#include <unistd.h>
#include <utility>
#include <vector>

struct Mapping {
    uint64_t start = 0, end = 0, offset = 0, inode = 0;
    std::string perms, dev, path;
    uint64_t size() const { return end - start; }
};

struct ReadStats { uint64_t requested=0, read=0, failed=0; };

static std::string hex64(uint64_t v) {
    std::ostringstream o;
    o << std::hex << std::setw(16) << std::setfill('0') << v;
    return o.str();
}

static std::string json_escape(const std::string& s) {
    std::ostringstream o;
    for (unsigned char c : s) {
        switch (c) {
        case '\\\\': o << "\\\\\\\\"; break;
        case '"': o << "\\\""; break;
        case '\\n': o << "\\\\n"; break;
        case '\\r': o << "\\\\r"; break;
        case '\\t': o << "\\\\t"; break;
        default:
            if (c < 0x20) o << "\\\\u" << std::hex << std::setw(4) << std::setfill('0') << (unsigned)c << std::dec;
            else o << (char)c;
        }
    }
    return o.str();
}

static bool parse_hex(const std::string& s, uint64_t& out) {
    char* e = nullptr;
    errno = 0;
    auto v = std::strtoull(s.c_str(), &e, 16);
    if (errno || e == s.c_str() || *e) return false;
    out = (uint64_t)v;
    return true;
}

static std::vector<Mapping> read_maps(pid_t pid, std::string& error) {
    std::ifstream in("/proc/" + std::to_string(pid) + "/maps");
    if (!in) { error = std::strerror(errno); return {}; }
    std::vector<Mapping> out;
    std::string line;
    while (std::getline(in, line)) {
        std::istringstream ss(line);
        std::string range, off;
        Mapping m;
        if (!(ss >> range >> m.perms >> off >> m.dev >> m.inode)) continue;
        auto dash = range.find('-');
        if (dash == std::string::npos) continue;
        if (!parse_hex(range.substr(0, dash), m.start) ||
            !parse_hex(range.substr(dash + 1), m.end) ||
            !parse_hex(off, m.offset)) continue;
        std::getline(ss, m.path);
        auto p = m.path.find_first_not_of(" \\t");
        m.path = (p == std::string::npos) ? "" : m.path.substr(p);
        out.push_back(std::move(m));
    }
    return out;
}

static bool readable(const Mapping& m) { return !m.perms.empty() && m.perms[0] == 'r'; }
static bool writable(const Mapping& m) { return m.perms.size() > 1 && m.perms[1] == 'w'; }
static bool anon(const Mapping& m) { return m.path.empty() || m.path.front() == '['; }
static bool module(const Mapping& m) { return !m.path.empty() && m.path.front() == '/'; }

static bool selected(const Mapping& m, const std::string& mode) {
    if (!readable(m)) return false;
    if (mode == "all") return true;
    if (mode == "heap") return m.path == "[heap]";
    if (mode == "anonymous") return anon(m);
    if (mode == "writable") return writable(m);
    if (mode == "modules") return module(m);
    return false;
}

static std::string safe_name(const Mapping& m, size_t index) {
    if (m.path.empty()) return "anon_" + hex64(m.start) + "_" + std::to_string(index) + ".bin";
    std::string s = m.path;
    for (char& c : s)
        if (!(std::isalnum((unsigned char)c) || c == '.' || c == '_' || c == '-')) c = '_';
    if (s.size() > 96) s.resize(96);
    return s + "__" + hex64(m.start) + ".bin";
}

static bool write_all(int fd, const void* data, size_t len) {
    const char* p = static_cast<const char*>(data);
    while (len) {
        ssize_t n = ::write(fd, p, len);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return false;
        p += n;
        len -= (size_t)n;
    }
    return true;
}

static ReadStats read_region(pid_t pid, int proc_mem, const Mapping& m, int out_fd, size_t chunk, bool use_vm) {
    ReadStats st;
    std::vector<unsigned char> buf(chunk);
    for (uint64_t addr = m.start; addr < m.end; addr += std::min<uint64_t>(chunk, m.end - addr)) {
        size_t want = (size_t)std::min<uint64_t>(chunk, m.end - addr);
        st.requested += want;

        ssize_t n = -1;
        if (use_vm) {
            iovec local{buf.data(), want}, remote{reinterpret_cast<void*>(addr), want};
            do { n = process_vm_readv(pid, &local, 1, &remote, 1, 0); } while (n < 0 && errno == EINTR);
        }
        if (n != (ssize_t)want && proc_mem >= 0) {
            do { n = pread(proc_mem, buf.data(), want, (off_t)addr); } while (n < 0 && errno == EINTR);
        }
        if (n < 0) n = 0;

        size_t got = std::min<size_t>((size_t)n, want);
        if (got < want) std::fill(buf.begin() + got, buf.begin() + want, 0);
        if (!write_all(out_fd, buf.data(), want)) break;
        st.read += got;
        st.failed += want - got;
    }
    return st;
}

static int snapshot(pid_t pid, const std::string& dir, const std::string& mode,
                    size_t chunk, const std::string& backend) {
    if (kill(pid, 0) != 0) { std::cerr << "pid access failed: " << std::strerror(errno) << '\\n'; return 2; }

    std::string error;
    auto maps = read_maps(pid, error);
    if (!error.empty()) { std::cerr << error << '\\n'; return 2; }

    std::error_code ec;
    std::filesystem::remove_all(dir + "/regions", ec);
    std::filesystem::create_directories(dir + "/regions", ec);
    if (ec) { std::cerr << "cannot create output: " << ec.message() << '\\n'; return 2; }

    bool vm = backend != "proc";
    int mem = -1;
    if (backend == "proc" || backend == "auto")
        mem = open(("/proc/" + std::to_string(pid) + "/mem").c_str(), O_RDONLY | O_CLOEXEC);
    if (backend == "proc" && mem < 0) {
        std::cerr << "cannot open /proc/PID/mem: " << std::strerror(errno) << '\\n';
        return 2;
    }

    std::vector<std::pair<Mapping,std::string>> dumped;
    ReadStats total;
    size_t index = 0;
    for (const auto& m : maps) {
        if (!selected(m, mode)) continue;
        std::string name = safe_name(m, index++);
        int fd = open((dir + "/regions/" + name).c_str(), O_CREAT | O_TRUNC | O_WRONLY | O_CLOEXEC, 0644);
        if (fd < 0) { std::cerr << "cannot create region file\\n"; if (mem >= 0) close(mem); return 2; }
        auto st = read_region(pid, mem, m, fd, chunk, vm);
        close(fd);
        total.requested += st.requested; total.read += st.read; total.failed += st.failed;
        dumped.emplace_back(m, name);
    }
    if (mem >= 0) close(mem);

    {
        std::ofstream out(dir + "/maps.txt");
        for (const auto& m : maps) {
            out << std::hex << m.start << '-' << m.end << ' ' << m.perms << ' ' << m.offset
                << ' ' << m.dev << ' ' << std::dec << m.inode;
            if (!m.path.empty()) out << ' ' << m.path;
            out << '\\n';
        }
    }
    {
        std::ofstream out(dir + "/manifest.json");
        out << "{\\n"
               "  \\\"format\\\": \\\"SHIFT-LIVE-MEMORY-SNAPSHOT/1\\\",\\n"
            << "  \\\"pid\\\": " << pid << ",\\n"
            << "  \\\"mode\\\": \\\"" << json_escape(mode) << "\\\",\\n"
            << "  \\\"page_size\\\": " << sysconf(_SC_PAGESIZE) << ",\\n"
            << "  \\\"backend\\\": \\\"" << (vm ? (mem >= 0 ? "process_vm_readv+proc-fallback" : "process_vm_readv") : "proc") << "\\\",\\n"
            << "  \\\"maps_count\\\": " << maps.size() << ",\\n"
            << "  \\\"selected_count\\\": " << dumped.size() << ",\\n"
            << "  \\\"bytes_requested\\\": " << total.requested << ",\\n"
            << "  \\\"bytes_read\\\": " << total.read << ",\\n"
            << "  \\\"bytes_failed\\\": " << total.failed << ",\\n"
               "  \\\"regions\\\": [\\n";
        for (size_t i = 0; i < dumped.size(); ++i) {
            const auto& m = dumped[i].first;
            out << "    {\\\"start\\\": " << m.start
                << ", \\\"end\\\": " << m.end
                << ", \\\"size\\\": " << m.size()
                << ", \\\"perms\\\": \\\"" << json_escape(m.perms)
                << "\\\", \\\"path\\\": \\\"" << json_escape(m.path)
                << "\\\", \\\"file\\\": \\\"regions/" << dumped[i].second << "\\\"}"
                << (i + 1 == dumped.size() ? "" : ",") << '\\n';
        }
        out << "  ]\\n}\\n";
    }

    std::cout << "snapshot: " << dir << "\\n"
              << "regions:  " << dumped.size() << "\\n"
              << "read:     " << total.read << " / " << total.requested << " bytes\\n"
              << "failed:   " << total.failed << " bytes\\n";
    return 0;
}

static std::map<uint64_t,std::pair<uint64_t,std::string>> manifest_regions(const std::string& dir) {
    std::ifstream in(dir + "/manifest.json");
    std::string s((std::istreambuf_iterator<char>(in)), {});
    std::map<uint64_t,std::pair<uint64_t,std::string>> r;
    size_t p = 0;
    while ((p = s.find("\\\"start\\\":", p)) != std::string::npos) {
        p += 8; while (p < s.size() && !std::isdigit((unsigned char)s[p])) ++p;
        size_t e = p; while (e < s.size() && std::isdigit((unsigned char)s[e])) ++e;
        uint64_t start = std::strtoull(s.substr(p,e-p).c_str(), nullptr, 10);
        size_t z = s.find("\\\"size\\\":", e), f = s.find("\\\"file\\\": \\\"regions/", e);
        if (z == std::string::npos || f == std::string::npos) break;
        z += 7; while (z < s.size() && !std::isdigit((unsigned char)s[z])) ++z;
        size_t ze = z; while (ze < s.size() && std::isdigit((unsigned char)s[ze])) ++ze;
        uint64_t size = std::strtoull(s.substr(z,ze-z).c_str(), nullptr, 10);
        f += std::strlen("\\\"file\\\": \\\"regions/");
        size_t fe = s.find('"', f);
        if (fe == std::string::npos) break;
        r[start] = {size, s.substr(f,fe-f)};
        p = fe + 1;
    }
    return r;
}

static int diff_snapshots(const std::string& a, const std::string& b, const std::string& out, size_t block) {
    std::error_code ec;
    std::filesystem::create_directories(out, ec);
    if (ec) { std::cerr << ec.message() << '\\n'; return 2; }
    auto ra = manifest_regions(a), rb = manifest_regions(b);
    if (ra.empty() || rb.empty()) { std::cerr << "missing or empty manifest\\n"; return 2; }

    std::ofstream report(out + "/diff.json");
    report << "{\\n  \\\"format\\\": \\\"SHIFT-LIVE-MEMORY-DIFF/1\\\",\\n"
           << "  \\\"block_size\\\": " << block << ",\\n  \\\"regions\\\": [\\n";
    bool first = true; uint64_t total_changed = 0; size_t changed_regions = 0;

    for (const auto& [start, meta] : ra) {
        auto it = rb.find(start);
        if (it == rb.end() || it->second.first != meta.first) continue;
        std::ifstream fa(a + "/regions/" + meta.second, std::ios::binary);
        std::ifstream fb(b + "/regions/" + it->second.second, std::ios::binary);
        if (!fa || !fb) continue;
        std::vector<unsigned char> xa(block), xb(block);
        std::vector<uint64_t> changed;
        uint64_t offset = 0;
        while (fa || fb) {
            fa.read((char*)xa.data(), block); auto na = fa.gcount();
            fb.read((char*)xb.data(), block); auto nb = fb.gcount();
            if (!na && !nb) break;
            size_t n = (size_t)std::max(na, nb);
            bool different = na != nb || std::memcmp(xa.data(), xb.data(), std::min(na, nb)) != 0;
            if (different) { changed.push_back(offset); ++total_changed; }
            offset += n;
        }
        if (!changed.empty()) {
            ++changed_regions;
            if (!first) report << ",\\n";
            first = false;
            report << "    {\\\"start\\\": " << start << ", \\\"size\\\": " << meta.first
                   << ", \\\"changed_blocks\\\": " << changed.size() << ", \\\"blocks\\\": [";
            for (size_t i=0;i<changed.size();++i) { if (i) report << ','; report << changed[i]; }
            report << "]}";
        }
    }
    report << "\\n  ]\\n}\\n";
    std::cout << "changed_regions: " << changed_regions << "\\nchanged_blocks:  " << total_changed
              << "\\nreport:          " << out << "/diff.json\\n";
    return 0;
}

static void usage() {
    std::cerr << R"(Usage:
  shift-live-dump maps PID
  shift-live-dump snapshot PID OUTDIR [--regions all|heap|anonymous|writable|modules] [--backend auto|vm|proc] [--chunk-kib N]
  shift-live-dump watch PID OUTDIR [--count N] [--interval-ms N] [snapshot options]
  shift-live-dump diff SNAPSHOT_A SNAPSHOT_B OUTDIR [--block-size-kib N]

The snapshot command uses process_vm_readv(2) without ptrace-attach/SIGSTOP.
)"; 
}

int main(int argc, char** argv) {
    try {
        if (argc < 2) { usage(); return 1; }
        std::string cmd = argv[1];

        if (cmd == "maps") {
            if (argc != 3) { usage(); return 1; }
            std::string e; auto maps = read_maps((pid_t)std::stol(argv[2]), e);
            if (!e.empty()) { std::cerr << e << '\\n'; return 2; }
            for (const auto& m : maps) {
                std::cout << std::hex << m.start << '-' << m.end << std::dec << ' '
                          << m.perms << ' ' << std::hex << m.offset << std::dec << ' '
                          << m.dev << ' ' << m.inode << (m.path.empty() ? "" : " " + m.path) << '\\n';
            }
            return 0;
        }

        if (cmd == "snapshot") {
            if (argc < 4) { usage(); return 1; }
            std::string mode="writable", backend="auto"; size_t chunk=1024*1024;
            for (int i=4;i<argc;++i) {
                std::string a=argv[i];
                auto need=[&](const char* n)->std::string{ if(i+1>=argc) throw std::runtime_error(std::string(n)+" requires a value"); return argv[++i]; };
                if(a=="--regions") mode=need("--regions");
                else if(a=="--backend") backend=need("--backend");
                else if(a=="--chunk-kib") chunk=std::stoull(need("--chunk-kib"))*1024;
                else throw std::runtime_error("unknown option: "+a);
            }
            if (chunk == 0 || chunk > (64ull<<20)) throw std::runtime_error("invalid chunk size");
            return snapshot((pid_t)std::stol(argv[2]), argv[3], mode, chunk, backend);
        }

        if (cmd == "watch") {
            if (argc < 4) { usage(); return 1; }
            std::string mode="writable", backend="auto"; size_t chunk=1024*1024;
            uint64_t count=0, interval=1000;
            for (int i=4;i<argc;++i) {
                std::string a=argv[i];
                auto need=[&](const char* n)->std::string{ if(i+1>=argc) throw std::runtime_error(std::string(n)+" requires a value"); return argv[++i]; };
                if(a=="--count") count=std::stoull(need("--count"));
                else if(a=="--interval-ms") interval=std::stoull(need("--interval-ms"));
                else if(a=="--regions") mode=need("--regions");
                else if(a=="--backend") backend=need("--backend");
                else if(a=="--chunk-kib") chunk=std::stoull(need("--chunk-kib"))*1024;
                else throw std::runtime_error("unknown option: "+a);
            }
            if (chunk == 0 || chunk > (64ull<<20)) throw std::runtime_error("invalid chunk size");
            for (uint64_t i=0; count==0 || i<count; ++i) {
                std::ostringstream d; d << argv[3] << "/snapshot-" << std::setw(6) << std::setfill('0') << i;
                int rc=snapshot((pid_t)std::stol(argv[2]), d.str(), mode, chunk, backend);
                if(rc) return rc;
                if(count==0 || i+1<count) std::this_thread::sleep_for(std::chrono::milliseconds(interval));
            }
            return 0;
        }

        if (cmd == "diff") {
            if (argc < 5) { usage(); return 1; }
            size_t block=4096;
            for(int i=5;i<argc;++i) {
                if(std::string(argv[i])=="--block-size-kib" && i+1<argc) block=std::stoull(argv[++i])*1024;
                else { usage(); return 1; }
            }
            return diff_snapshots(argv[2], argv[3], argv[4], block);
        }

        usage(); return 1;
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << '\\n';
        return 1;
    }
}
