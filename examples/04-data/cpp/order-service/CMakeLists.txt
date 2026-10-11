cmake_minimum_required(VERSION 3.31)
project(order-service CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_compile_options(-Wall -Wextra)
# gcc-toolset-15's libstdc++ is newer than the one in ubi-minimal: link it statically.
add_link_options(-static-libstdc++ -static-libgcc)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

find_package(Drogon CONFIG REQUIRED)
find_package(PostgreSQL REQUIRED)

add_executable(order-service src/main.cpp)
target_link_libraries(order-service PRIVATE Drogon::Drogon PostgreSQL::PostgreSQL)
