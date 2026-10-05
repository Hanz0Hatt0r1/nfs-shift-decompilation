# Process 2 Phase 714: consume Process 1 PR #1276's selector-complete BMW
# offset33b family and bind the deterministic Silverstone playable selector to
# one BODY0 -> outer Vehicle-root matrix.  This deliberately stops before the
# independent outer Vehicle-root -> VHF vehicle-root frame join.

target_sources(shift_runtime_physics PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src/bmw_offset33b_native_selector.cpp)

add_executable(shift_runtime_bmw_offset33b_native_selector_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/bmw_offset33b_native_selector_check.cpp)
target_link_libraries(
  shift_runtime_bmw_offset33b_native_selector_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_bmw_offset33b_native_selector_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_bmw_offset33b_native_selector
    COMMAND shift_runtime_bmw_offset33b_native_selector_check)
endif()
