"""06-stream-processing/cpp/order-service: Conan 2 recipe.

Exact pins from ConanCenter (the only remote); static libraries, built with GCC 15 / C++23.
Kafka is librdkafka's C++ API (rdkafka++).
"""

from conan import ConanFile


class Cndp06OrderServiceConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    default_options = {
        "*/*:shared": False,
        "drogon/*:with_boost": False,
    }

    def requirements(self):
        self.requires("drogon/1.9.13")
        self.requires("librdkafka/2.14.2")
        self.requires("libpq/17.11")
