# Single-process S6 Phase 742: close the primary FUN_00766510 query-response
# application through the already-native FUN_007aefb0 transform and FUN_007baa70
# BODY accumulator primitive. Complete FUN_00766510 remains external.

add_executable(shift_runtime_fun_00766510_primary_response_application_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00766510_primary_response_application_check.cpp)
target_include_directories(
  shift_runtime_fun_00766510_primary_response_application_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_00766510_primary_response_application_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00766510_primary_response_application_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_00766510_primary_response_application
    COMMAND shift_runtime_fun_00766510_primary_response_application_check)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/phase743.cmake)
