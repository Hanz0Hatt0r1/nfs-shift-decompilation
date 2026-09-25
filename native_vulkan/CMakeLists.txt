cmake_minimum_required(VERSION 3.16)
project(shift_vulkan_probe LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Vulkan QUIET)

if(NOT Vulkan_FOUND)
  message(STATUS "Vulkan SDK not found; shift_vulkan_probe will not be built")
  return()
endif()

add_executable(shift_vulkan_probe src/vulkan_probe.cpp)
target_link_libraries(shift_vulkan_probe PRIVATE Vulkan::Vulkan)
