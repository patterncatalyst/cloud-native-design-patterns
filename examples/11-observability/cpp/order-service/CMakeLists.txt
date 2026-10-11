cmake_minimum_required(VERSION 3.31)
project(order-service LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_compile_options(-Wall -Wextra)
# gcc-toolset-15's libstdc++ is newer than the one in ubi-minimal: link it statically.
add_link_options(-static-libstdc++ -static-libgcc)

# Static archives that depend on each other (Drogon, gRPC, librdkafka, OpenTelemetry):
# let the linker rescan the group.
set(CMAKE_CXX_LINK_EXECUTABLE
    "<CMAKE_CXX_COMPILER> <FLAGS> <CMAKE_CXX_LINK_FLAGS> <LINK_FLAGS> \
     <OBJECTS> -o <TARGET> -Wl,--start-group <LINK_LIBRARIES> -Wl,--end-group")

find_package(Drogon CONFIG REQUIRED)
find_package(gRPC CONFIG REQUIRED)
find_package(protobuf CONFIG REQUIRED)
find_package(RdKafka CONFIG REQUIRED)
find_package(PostgreSQL REQUIRED)
find_package(spdlog CONFIG REQUIRED)
find_package(opentelemetry-cpp CONFIG REQUIRED)
find_package(Threads REQUIRED)

set(PROTO_FILE ${CMAKE_CURRENT_SOURCE_DIR}/proto/inventory.proto)
set(PROTO_OUT ${CMAKE_CURRENT_BINARY_DIR}/proto)
file(MAKE_DIRECTORY ${PROTO_OUT})

add_custom_command(
    OUTPUT ${PROTO_OUT}/inventory.pb.cc ${PROTO_OUT}/inventory.pb.h
           ${PROTO_OUT}/inventory.grpc.pb.cc ${PROTO_OUT}/inventory.grpc.pb.h
    COMMAND protobuf::protoc
        --proto_path=${CMAKE_CURRENT_SOURCE_DIR}/proto
        --cpp_out=${PROTO_OUT}
        --grpc_out=${PROTO_OUT}
        --plugin=protoc-gen-grpc=$<TARGET_FILE:gRPC::grpc_cpp_plugin>
        ${PROTO_FILE}
    DEPENDS ${PROTO_FILE} protobuf::protoc gRPC::grpc_cpp_plugin
)

add_executable(order-service
    src/main.cpp
    ${PROTO_OUT}/inventory.pb.cc
    ${PROTO_OUT}/inventory.grpc.pb.cc)
target_include_directories(order-service PRIVATE src ${PROTO_OUT})
target_link_libraries(order-service PRIVATE
    Drogon::Drogon gRPC::grpc++ protobuf::protobuf RdKafka::rdkafka++
    PostgreSQL::PostgreSQL spdlog::spdlog opentelemetry-cpp::opentelemetry-cpp Threads::Threads)
