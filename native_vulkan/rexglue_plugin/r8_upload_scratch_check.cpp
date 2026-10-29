#include "shift_native_r8_upload_scratch.hpp"

#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <vector>

namespace {

void require(bool condition, const char* message) {
  if (!condition) {
    std::cerr << message << '\n';
    std::exit(1);
  }
}

}  // namespace

int main() {
  using shift::xbox::plugin::R8UploadScratchCache;
  using shift::xbox::plugin::R8UploadScratchKey;

  R8UploadScratchCache cache(32);
  const R8UploadScratchKey luma{7, 0, 4, 4};
  std::vector<uint8_t> payload;
  require(cache.acquire(luma, &payload), "first captured R8 slot was not admitted");
  std::vector<uint8_t> duplicate_lease;
  require(!cache.acquire(luma, &duplicate_lease),
          "the same in-use plane storage was leased twice");
  payload.resize(16);
  for (size_t i = 0; i < payload.size(); ++i) {
    payload[i] = static_cast<uint8_t>(i * 7u + 3u);
  }
  const std::vector<uint8_t> first_frame = payload;
  const size_t first_capacity = payload.capacity();
  cache.release(luma, &payload);
  require(payload.empty(), "released payload storage was not moved to the cache");

  require(cache.acquire(luma, &payload), "recurring captured R8 slot missed");
  require(payload.capacity() == first_capacity,
          "recurring plane did not reuse its allocated CPU storage");
  std::fill(payload.begin(), payload.end(), 0xA5);
  require(payload != first_frame, "reused plane did not accept new frame bytes");
  const std::vector<uint8_t> second_frame = payload;
  cache.release(luma, &payload);
  require(cache.acquire(luma, &payload), "second recurring R8 slot missed");
  require(payload == second_frame,
          "cached plane bytes changed while released and reacquired");
  cache.release(luma, &payload);

  const R8UploadScratchKey chroma{7, 1, 8, 2};
  std::vector<uint8_t> other;
  require(cache.acquire(chroma, &other), "second captured plane was not admitted");
  other.resize(16);
  cache.release(chroma, &other);

  const R8UploadScratchKey over_budget{8, 0, 8, 1};
  std::vector<uint8_t> uncached;
  require(!cache.acquire(over_budget, &uncached),
          "scratch cache exceeded its configured byte budget");

  const auto stats = cache.stats();
  require(stats.entries == 2 && stats.reserved_bytes == 32,
          "scratch cache retained the wrong bounded payload set");
  require(stats.hits == 2 && stats.misses == 3 && stats.bypasses == 2,
          "scratch cache hit, miss, or budget-bypass accounting is wrong");
  std::cout << "captured R8 upload scratch reuse check passed\n";
  return 0;
}
