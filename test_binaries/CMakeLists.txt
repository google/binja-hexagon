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

if(NOT USE_DOCKER_BUILD)
  message(STATUS "USE_DOCKER_BUILD is not set. Skipping build process, and using prebuilt binaries instead.")

  add_test(NAME bn_llil_test
    COMMAND python3 bn_llil_test.py
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  )
  set_tests_properties(bn_llil_test PROPERTIES
    ENVIRONMENT "PYTHONPATH=${BN_INSTALL_DIR}/python;TEST_TARGET_FILE=${CMAKE_CURRENT_SOURCE_DIR}/prebuilt/bn_llil_test_app"
  )

  add_test(NAME bn_hlil_test
    COMMAND python3 bn_hlil_test.py
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  )
  set_tests_properties(bn_hlil_test PROPERTIES
    ENVIRONMENT "PYTHONPATH=${BN_INSTALL_DIR}/python;TEST_TARGET_FILE=${CMAKE_CURRENT_SOURCE_DIR}/prebuilt/bn_hlil_test_app"
  )
else()
  # bn_llil_test
  set(BN_LLIL_TEST_BIN ${CMAKE_CURRENT_BINARY_DIR}/bn_llil_test)
  add_custom_command(
    OUTPUT ${BN_LLIL_TEST_BIN}
    COMMAND docker rm tmp-hexagon-llil-container 2>/dev/null || (exit 0)
    COMMAND docker build -t tmp-hexagon-llil-image -f build_llil_test.dockerfile .
    COMMAND docker run --name tmp-hexagon-llil-container tmp-hexagon-llil-image /bin/true
    COMMAND docker cp tmp-hexagon-llil-container:/build/bn_llil_test ${BN_LLIL_TEST_BIN}
    COMMAND docker rm tmp-hexagon-llil-container 2>/dev/null || (exit 0)
    COMMAND touch ${BN_LLIL_TEST_BIN}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    DEPENDS first.s bn_llil_test_app.s build_llil_test.dockerfile build_llil_test.makefile
  )
  add_custom_target(bn_llil_test_app ALL
    DEPENDS ${BN_LLIL_TEST_BIN}
  )

  add_test(NAME bn_llil_test
    COMMAND python3 bn_llil_test.py
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  )
  set_tests_properties(bn_llil_test PROPERTIES
    DEPENDS bn_llil_test_app
  )
  set_tests_properties(bn_llil_test PROPERTIES
    ENVIRONMENT "PYTHONPATH=${BN_INSTALL_DIR}/python;TEST_TARGET_FILE=${BN_LLIL_TEST_BIN}"
  )

  # bn_hlil_test
  set(BN_HLIL_TEST_BIN ${CMAKE_CURRENT_BINARY_DIR}/bn_hlil_test)
  add_custom_command(
    OUTPUT ${BN_HLIL_TEST_BIN}
    COMMAND docker rm tmp-hexagon-hlil-container 2>/dev/null || (exit 0)
    COMMAND docker build -t tmp-hexagon-hlil-image -f build_hlil_test.dockerfile .
    COMMAND docker run --name tmp-hexagon-hlil-container tmp-hexagon-hlil-image /bin/true
    COMMAND docker cp tmp-hexagon-hlil-container:/build/bn_hlil_test ${BN_HLIL_TEST_BIN}
    COMMAND docker rm tmp-hexagon-hlil-container 2>/dev/null || (exit 0)
    COMMAND touch ${BN_HLIL_TEST_BIN}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    DEPENDS bn_hlil_test_app.c build_hlil_test.dockerfile build_hlil_test.makefile
  )
  add_custom_target(bn_hlil_test_app ALL
    DEPENDS ${BN_HLIL_TEST_BIN}
  )

  add_test(NAME bn_hlil_test
    COMMAND python3 bn_hlil_test.py
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  )
  set_tests_properties(bn_hlil_test PROPERTIES
    DEPENDS bn_hlil_test_app
  )
  set_tests_properties(bn_hlil_test PROPERTIES
    ENVIRONMENT "PYTHONPATH=${BN_INSTALL_DIR}/python;TEST_TARGET_FILE=${BN_HLIL_TEST_BIN}"
  )

endif()
