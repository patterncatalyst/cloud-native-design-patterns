cmake_minimum_required(VERSION 3.25)
project(saga-orchestrator CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

find_package(Drogon CONFIG REQUIRED)

add_executable(saga-orchestrator src/main.cpp)
target_link_libraries(saga-orchestrator PRIVATE Drogon::Drogon pq)
