# Copyright 2020 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

########################################################################
# Check if there is C++ code at all
########################################################################
if(NOT iridiumtx_sources)
    message(STATUS "No C++ sources... skipping python bindings")
    return()
endif(NOT iridiumtx_sources)

########################################################################
# Check for pygccxml
########################################################################
gr_python_check_module_raw("pygccxml" "import pygccxml" PYGCCXML_FOUND)

include(GrPybind)

########################################################################
# Python Bindings
########################################################################
list(APPEND iridiumtx_python_files
    add_usrp_tags_python.cc
    insert_delay_python.cc
    freq_shift_python.cc python_bindings.cc)

gr_pybind_make_oot(iridiumtx ../../.. gr::iridiumtx "${iridiumtx_python_files}")

# copy bindings extension for use in QA test module
add_custom_command(
    TARGET iridiumtx_python
    POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:iridiumtx_python>
            ${PROJECT_BINARY_DIR}/test_modules/gnuradio/iridiumtx/)

install(
    TARGETS iridiumtx_python
    DESTINATION ${GR_PYTHON_DIR}/gnuradio/iridiumtx
    COMPONENT pythonapi)
