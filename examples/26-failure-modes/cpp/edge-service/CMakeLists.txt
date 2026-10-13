cmake_minimum_required(VERSION 3.31)
project(cndp-26-edge-service LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_compile_options(-Wall -Wextra)
# gcc-toolset-15's libstdc++ is newer than the one in ubi-minimal: link it statically.
add_link_options(-static-libstdc++ -static-libgcc)

set(CMAKE_INTERPROCEDURAL_OPTIMIZATION ON)

set(CMAKE_CXX_LINK_EXECUTABLE
    "<CMAKE_CXX_COMPILER> <FLAGS> <CMAKE_CXX_LINK_FLAGS> <LINK_FLAGS> \
     <OBJECTS> -o <TARGET> -Wl,--start-group <LINK_LIBRARIES> -Wl,--end-group")

find_package(Drogon CONFIG REQUIRED)
find_package(Threads REQUIRED)

add_executable(edge-service src/main.cpp)
target_link_libraries(edge-service PRIVATE
    Drogon::Drogon Threads::Threads)
