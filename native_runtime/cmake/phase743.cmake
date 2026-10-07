# Single-process S6 Phase 743: close the PC FUN_00753650 cross and the exact
# FUN_00766510 caller/auxiliary accumulator updates immediately after Phase742.

add_executable(shift_runtime_fun_00766510_primary_response_post_application_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00766510_primary_response_post_application_check.cpp)
target_include_directories(
  shift_runtime_fun_00766510_primary_response_post_application_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_00766510_primary_response_post_application_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00766510_primary_response_post_application_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_00766510_primary_response_post_application
    COMMAND shift_runtime_fun_00766510_primary_response_post_application_check)
endif()
