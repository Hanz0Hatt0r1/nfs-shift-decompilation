# Single-process S6 Phase 722: prove the four FUN_007682c0 load terms are
# per-pass outputs of the still-external FUN_00765c40 wheel job boundary and
# remove them from the later motion-read raw-input provider.

add_executable(shift_runtime_fun_00765c40_load_term_ownership_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00765c40_load_term_ownership_check.cpp)
target_include_directories(
  shift_runtime_fun_00765c40_load_term_ownership_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_link_libraries(
  shift_runtime_fun_00765c40_load_term_ownership_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00765c40_load_term_ownership_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_00765c40_load_term_ownership
    COMMAND shift_runtime_fun_00765c40_load_term_ownership_check)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/phase723.cmake)
