# Copyright (C) 2020 Google LLC
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
cmake_minimum_required (VERSION 3.0)
project ("binja-hexagon" C CXX ASM)
set(CMAKE_CXX_STANDARD 11)

# Set default build type.
if(NOT CMAKE_BUILD_TYPE)
  message(STATUS "Setting build type to 'Release' as none was specified.")
  set(CMAKE_BUILD_TYPE "Release" CACHE STRING
      "Choose the type of build, options are: Debug Release RelWithDebInfo MinSizeRel."
      FORCE)
endif()

SET( CMAKE_EXPORT_COMPILE_COMMANDS ON )

add_custom_target(
    copy-compile-commands ALL
    ${CMAKE_COMMAND} -E copy_if_different
        ${CMAKE_CURRENT_BINARY_DIR}/compile_commands.json
        ${CMAKE_SOURCE_DIR}/compile_commands.json
)

# Binary Ninja plugins require "-fPIC".
set(CMAKE_POSITION_INDEPENDENT_CODE TRUE)

# Optional Qualcomm Hexagon SDK, available at:
# https://developer.qualcomm.com/software/hexagon-dsp-sdk/tools
set(HEXAGON_SDK_TOOLS_DIR
  "$ENV{HOME}/Qualcomm/Hexagon_SDK/3.5.2/tools/HEXAGON_Tools/8.3.07"
  CACHE STRING "Hexagon SDK root directory"
)
get_filename_component(HEXAGON_SDK_TOOLS_DIR ${HEXAGON_SDK_TOOLS_DIR} ABSOLUTE)
set(HEXAGON_CLANG_C "${HEXAGON_SDK_TOOLS_DIR}/Tools/bin/hexagon-clang")
set(HEXAGON_CLANG_CXX "${HEXAGON_SDK_TOOLS_DIR}/Tools/bin/hexagon-clang++")
set(HEXAGON_OBJDUMP "${HEXAGON_SDK_TOOLS_DIR}/Tools/bin/hexagon-llvm-objdump")
set(HEXAGON_READELF "${HEXAGON_SDK_TOOLS_DIR}/Tools/bin/hexagon-llvm-readelf")
set(HEXAGON_STRIP "${HEXAGON_SDK_TOOLS_DIR}/Tools/bin/hexagon-strip")

# Enable testing.
enable_testing()
add_custom_target(check COMMAND ${CMAKE_CTEST_COMMAND})

#
# Build gflags at configure time.
#
configure_file(third_party/gflags_CMakeLists.txt.in
               gflags-build/CMakeLists.txt)
execute_process(COMMAND ${CMAKE_COMMAND} -G "${CMAKE_GENERATOR}" .
  WORKING_DIRECTORY ${CMAKE_BINARY_DIR}/gflags-build )
execute_process(COMMAND ${CMAKE_COMMAND} --build . --target all
  WORKING_DIRECTORY ${CMAKE_BINARY_DIR}/gflags-build )

list(APPEND CMAKE_MODULE_PATH ${PROJECT_SOURCE_DIR}/cmake)
find_package(gflags REQUIRED)

#
# third_party dependencies.
#
option(BUILD_TESTING OFF)
option(WITH_UNWIND OFF)
option(BENCHMARK_ENABLE_TESTING OFF)
option(ABSL_USE_EXTERNAL_GOOGLETEST ON)
add_subdirectory(third_party/glog EXCLUDE_FROM_ALL)
add_subdirectory(third_party/googletest EXCLUDE_FROM_ALL)
add_subdirectory(third_party/abseil-cpp EXCLUDE_FROM_ALL)
add_subdirectory(third_party/chromium EXCLUDE_FROM_ALL)
add_subdirectory(third_party/binaryninja-api EXCLUDE_FROM_ALL)

#
# Plugin project.
#
include_directories(${CMAKE_SOURCE_DIR})
add_subdirectory(scripts)
add_subdirectory(test_binaries)
add_subdirectory(third_party/qemu-hexagon)
add_subdirectory(plugin)
