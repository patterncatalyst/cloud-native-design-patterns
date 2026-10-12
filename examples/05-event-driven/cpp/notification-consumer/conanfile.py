"""05-event-driven/cpp/notification-consumer: Conan 2 recipe.

Exact pins from ConanCenter (the only remote); static libraries, built with GCC 15 / C++23.
"""

from conan import ConanFile


class Cndp05EventDrivenCppNotificationConsumerConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    default_options = {
        "*/*:shared": False,
    }

    def requirements(self):
        self.requires("libpq/17.11")
        self.requires("librdkafka/2.14.2")
        self.requires("jsoncpp/1.9.8")
        self.requires("opentelemetry-cpp/1.26.0")
        self.requires("spdlog/1.17.0")
        # opentelemetry-cpp pins nlohmann_json 3.11.3; take the newest release.
        self.requires("nlohmann_json/3.12.0", override=True)
        self.requires("lz4/1.10.0", override=True)  # librdkafka and libpq pin lz4 1.9.4
        self.requires("fmt/12.2.0", override=True)  # spdlog pins fmt 12.1.0
