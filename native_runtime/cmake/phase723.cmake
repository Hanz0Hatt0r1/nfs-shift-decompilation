# Single-process S6 Phase 723: bind PC DAT_00c128cc angle-mode semantics to
# the already explicit Silverstone+BMW_M3_E36 native session Player Difficulty
# selection. This does not infer a retail live-session default.

add_executable(shift_runtime_selected_session_angle_mode_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/selected_session_angle_mode_check.cpp)
target_include_directories(
  shift_runtime_selected_session_angle_mode_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_link_libraries(
  shift_runtime_selected_session_angle_mode_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_selected_session_angle_mode_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_selected_session_angle_mode
    COMMAND shift_runtime_selected_session_angle_mode_check)
endif()
