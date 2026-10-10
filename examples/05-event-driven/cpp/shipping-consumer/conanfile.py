"""05-event-driven/cpp/shipping-consumer: Conan 2 recipe.

Exact pins from ConanCenter (the only remote); static libraries, built with GCC 15 / C++23.
"""

from conan import ConanFile


class Cndp05EventDrivenCppShippingConsumerConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    default_options = {
        "*/*:shared": False,
    }

    def requirements(self):
        self.requires("libpq/17.11")
        self.requires("librdkafka/2.14.2")
        self.requires("jsoncpp/1.9.8")
