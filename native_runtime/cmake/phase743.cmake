# Single-process S6 Phase 743: prove that FUN_00766510 reuses the exact
# HDVehicle+0x38f0 body-rotated scratch already produced by Phase727.

add_executable(shift_runtime_fun_00766510_selected_bmw_application_point_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00766510_selected_bmw_application_point_check.cpp)
target_include_directories(
  shift_runtime_fun_00766510_selected_bmw_application_point_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_00766510_selected_bmw_application_point_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00766510_selected_bmw_application_point_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_00766510_selected_bmw_application_point
    COMMAND shift_runtime_fun_00766510_selected_bmw_application_point_check)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/phase744.cmake)
