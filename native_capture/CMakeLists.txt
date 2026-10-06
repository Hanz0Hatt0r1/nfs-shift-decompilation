cmake_minimum_required(VERSION 3.16)
project(shift_d3d9_capture LANGUAGES CXX)

if(NOT WIN32)
  message(STATUS "shift_d3d9_capture is Windows-only; no target will be built on this host")
  return()
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(shift_d3d9_capture SHARED
  shift_d3d9_capture.cpp
  capture_helpers.cpp
  d3d9_proxy.def
)
target_compile_definitions(shift_d3d9_capture PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX)
set_target_properties(shift_d3d9_capture PROPERTIES OUTPUT_NAME "d3d9" PREFIX "")

add_executable(shift_d3d9_proxy_smoke proxy_smoke.cpp)
target_compile_definitions(shift_d3d9_proxy_smoke PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX)

add_executable(shift_selected_session_rate_snapshot selected_session_rate_snapshot.cpp)
target_compile_definitions(
  shift_selected_session_rate_snapshot PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX)

if (MSVC)
  set_property(TARGET shift_d3d9_capture PROPERTY
    MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
  set_property(TARGET shift_d3d9_proxy_smoke PROPERTY
    MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
  set_property(TARGET shift_selected_session_rate_snapshot PROPERTY
    MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
  target_compile_options(shift_d3d9_capture PRIVATE /FI"${CMAKE_CURRENT_SOURCE_DIR}/capture_helpers.h")
elseif (CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
  # Avoid requiring MinGW runtime DLLs next to the retail game executable.\n  # Arch/MinGW may leave libwinpthread as a transitive DLL dependency even\n  # with -static-libgcc/-static-libstdc++. Use full static runtime linking.
  target_link_options(shift_d3d9_capture PRIVATE
    -static
    -static-libgcc
    -static-libstdc++
  )
  target_link_options(shift_selected_session_rate_snapshot PRIVATE
    -static
    -static-libgcc
    -static-libstdc++
  )
endif()
