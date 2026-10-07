# Single-process S6 Phase 741: bind the selected BMW M3 E36 FUN_00765c40
# +0x38e8 query fallback to the exact FUN_00756bb0/FWMaxHeight setup value.

add_executable(shift_runtime_fun_00765c40_selected_bmw_query_fallback_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00765c40_selected_bmw_query_fallback_check.cpp)
target_include_directories(
  shift_runtime_fun_00765c40_selected_bmw_query_fallback_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_00765c40_selected_bmw_query_fallback_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00765c40_selected_bmw_query_fallback_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_00765c40_selected_bmw_query_fallback
    COMMAND shift_runtime_fun_00765c40_selected_bmw_query_fallback_check)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/phase742.cmake)
