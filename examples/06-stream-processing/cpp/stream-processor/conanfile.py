"""06-stream-processing/cpp/stream-processor: Conan 2 recipe.

Exact pins from ConanCenter (the only remote); static libraries, built with GCC 15 / C++23.
Kafka is librdkafka's C++ API (rdkafka++); there is no Kafka Streams in the C++ stack, so
the windowed aggregation is written explicitly (see README).
"""

from conan import ConanFile


class Cndp06StreamProcessorConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    default_options = {
        "*/*:shared": False,
        "drogon/*:with_boost": False,
    }

    def requirements(self):
        self.requires("librdkafka/2.14.2")
        self.requires("nlohmann_json/3.12.0")
        self.requires("spdlog/1.17.0")
