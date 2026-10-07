# Single-process S6 Phase 724: bind the already-selected native Player
# Difficulty to the retail RaceModeInfo+0x6c -> DAT_00c128cc consumer and remove
# the final late FUN_007682c0 raw-input provider boundary.

add_executable(shift_runtime_bmw_native_session_player_difficulty_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/bmw_native_session_player_difficulty_check.cpp)
target_include_directories(
  shift_runtime_bmw_native_session_player_difficulty_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_link_libraries(
  shift_runtime_bmw_native_session_player_difficulty_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_bmw_native_session_player_difficulty_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_bmw_native_session_player_difficulty
    COMMAND shift_runtime_bmw_native_session_player_difficulty_check)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/phase725.cmake)
