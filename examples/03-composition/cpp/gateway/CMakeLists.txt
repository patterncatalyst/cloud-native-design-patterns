cmake_minimum_required(VERSION 3.25)
project(gateway CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

set(CMAKE_CXX_LINK_EXECUTABLE
    "<CMAKE_CXX_COMPILER> <FLAGS> <CMAKE_CXX_LINK_FLAGS> <LINK_FLAGS> <OBJECTS> -o <TARGET> -Wl,--start-group <LINK_LIBRARIES> -Wl,--end-group")

find_package(Drogon CONFIG REQUIRED)
find_package(gRPC CONFIG REQUIRED)
find_package(protobuf CONFIG REQUIRED)
find_package(Threads REQUIRED)

set(PROTO_SRC "${CMAKE_SOURCE_DIR}/../proto/inventory.proto")
set(PROTO_OUT "${CMAKE_BINARY_DIR}/gen")
file(MAKE_DIRECTORY ${PROTO_OUT})

add_custom_command(
    OUTPUT ${PROTO_OUT}/inventory.pb.cc ${PROTO_OUT}/inventory.pb.h
           ${PROTO_OUT}/inventory.grpc.pb.cc ${PROTO_OUT}/inventory.grpc.pb.h
    COMMAND protobuf::protoc
        --proto_path=${CMAKE_SOURCE_DIR}/../proto
        --cpp_out=${PROTO_OUT}
        --grpc_out=${PROTO_OUT}
        --plugin=protoc-gen-grpc=$<TARGET_FILE:gRPC::grpc_cpp_plugin>
        ${PROTO_SRC}
    DEPENDS ${PROTO_SRC} protobuf::protoc gRPC::grpc_cpp_plugin
)

add_executable(gateway
    src/main.cpp
    ${PROTO_OUT}/inventory.pb.cc
    ${PROTO_OUT}/inventory.grpc.pb.cc)

target_include_directories(gateway PRIVATE ${PROTO_OUT})
target_link_libraries(gateway PRIVATE
    Drogon::Drogon
    gRPC::grpc++
    protobuf::protobuf
    Threads::Threads)
