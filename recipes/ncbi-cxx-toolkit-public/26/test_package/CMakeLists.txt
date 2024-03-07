cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(ncbi-cxx-toolkit-public REQUIRED CONFIG)

NCBI_begin_app(test_package)
  NCBI_sources(test_package)
  NCBI_uses_toolkit_libraries(xncbi)
NCBI_end_app()

add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE ncbi-cxx-toolkit-public::xncbi)
