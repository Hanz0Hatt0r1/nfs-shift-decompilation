# Single-process S6 Phase 727: own FUN_007675f0 BODY0 +0x78/+0x88 speed
# inputs from the authoritative persistent BODY buffer at each recovered pass.
# The remaining contact-outer fields stay external and provider count stays seven.

add_executable(shift_runtime_fun_007675f0_body_motion_ownership_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_007675f0_body_motion_ownership_check.cpp)
target_include_directories(
  shift_runtime_fun_007675f0_body_motion_ownership_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_007675f0_body_motion_ownership_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_007675f0_body_motion_ownership_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_007675f0_body_motion_ownership
    COMMAND shift_runtime_fun_007675f0_body_motion_ownership_check)
endif()
