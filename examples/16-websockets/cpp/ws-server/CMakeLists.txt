cmake_minimum_required(VERSION 3.25)
project(ws-server CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

set(CMAKE_CXX_LINK_EXECUTABLE
    "<CMAKE_CXX_COMPILER> <FLAGS> <CMAKE_CXX_LINK_FLAGS> <LINK_FLAGS> \
     <OBJECTS> -o <TARGET> -Wl,--start-group <LINK_LIBRARIES> -Wl,--end-group")

find_package(Drogon CONFIG REQUIRED)
find_package(hiredis CONFIG REQUIRED)
find_package(Threads REQUIRED)

add_executable(ws-server src/main.cpp)

find_library(REDIS_PLUS_PLUS_LIB NAMES redis++_static redis++ REQUIRED)
find_path(REDIS_PLUS_PLUS_INCLUDE_DIR sw/redis++/redis++.h REQUIRED)

target_include_directories(ws-server PRIVATE ${REDIS_PLUS_PLUS_INCLUDE_DIR})
target_link_libraries(ws-server PRIVATE
    Drogon::Drogon ${REDIS_PLUS_PLUS_LIB} hiredis::hiredis Threads::Threads)
