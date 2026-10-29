#pragma once

#include <cstddef>
#include <cstdint>
#include <unordered_map>
#include <utility>
#include <vector>

namespace shift::xbox::plugin {

struct R8UploadScratchKey {
  size_t draw_slot = 0;
  uint32_t fetch_constant_index = 0;
  uint32_t width = 0;
  uint32_t height = 0;

  bool operator==(const R8UploadScratchKey& other) const {
    return draw_slot == other.draw_slot &&
           fetch_constant_index == other.fetch_constant_index &&
           width == other.width && height == other.height;
  }
};

struct R8UploadScratchKeyHash {
  size_t operator()(const R8UploadScratchKey& key) const {
    size_t hash = key.draw_slot;
    hash = hash * 16777619u ^ key.fetch_constant_index;
    hash = hash * 16777619u ^ key.width;
    return hash * 16777619u ^ key.height;
  }
};

// Reuses the CPU-side linear payload vectors for recurring captured R8 planes.
// The ring worker is the sole caller; the renderer copies these bytes into its
// own upload buffers before returning, so payloads can then be recycled.
class R8UploadScratchCache {
 public:
  struct Stats {
    size_t entries = 0;
    size_t reserved_bytes = 0;
    size_t hits = 0;
    size_t misses = 0;
    size_t bypasses = 0;
  };

  explicit R8UploadScratchCache(size_t budget_bytes = 16u * 1024u * 1024u)
      : budget_bytes_(budget_bytes) {}

  bool acquire(const R8UploadScratchKey& key,
               std::vector<uint8_t>* payload) {
    if (!payload || key.width == 0 || key.height == 0) return false;
    const uint64_t required = uint64_t{key.width} * key.height;
    if (required > static_cast<uint64_t>(static_cast<size_t>(-1))) return false;

    const auto found = entries_.find(key);
    if (found != entries_.end()) {
      if (found->second.leased) {
        ++bypasses_;
        return false;
      }
      found->second.leased = true;
      *payload = std::move(found->second.payload);
      ++hits_;
      return true;
    }

    ++misses_;
    const size_t required_bytes = static_cast<size_t>(required);
    if (required_bytes > budget_bytes_ - reserved_bytes_) {
      ++bypasses_;
      return false;
    }
    Entry entry{};
    entry.reserved_bytes = required_bytes;
    entry.leased = true;
    entries_.emplace(key, std::move(entry));
    reserved_bytes_ += required_bytes;
    return true;
  }

  void release(const R8UploadScratchKey& key,
               std::vector<uint8_t>* payload) {
    if (!payload) return;
    const auto found = entries_.find(key);
    if (found == entries_.end() || !found->second.leased) return;

    const size_t capacity = payload->capacity();
    if (capacity > found->second.reserved_bytes) {
      const size_t extra = capacity - found->second.reserved_bytes;
      if (extra > budget_bytes_ - reserved_bytes_) {
        reserved_bytes_ -= found->second.reserved_bytes;
        entries_.erase(found);
        return;
      }
      reserved_bytes_ += extra;
      found->second.reserved_bytes = capacity;
    }
    found->second.payload = std::move(*payload);
    found->second.leased = false;
  }

  Stats stats() const {
    return {entries_.size(), reserved_bytes_, hits_, misses_, bypasses_};
  }

  void clear() {
    entries_.clear();
    reserved_bytes_ = 0;
    hits_ = 0;
    misses_ = 0;
    bypasses_ = 0;
  }

 private:
  struct Entry {
    std::vector<uint8_t> payload;
    size_t reserved_bytes = 0;
    bool leased = false;
  };

  const size_t budget_bytes_;
  size_t reserved_bytes_ = 0;
  size_t hits_ = 0;
  size_t misses_ = 0;
  size_t bypasses_ = 0;
  std::unordered_map<R8UploadScratchKey, Entry, R8UploadScratchKeyHash> entries_;
};

}  // namespace shift::xbox::plugin
