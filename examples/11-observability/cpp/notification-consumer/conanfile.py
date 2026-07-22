from conan import ConanFile

class CloudNative11NotificationConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    default_options = {"*/*:shared": False}

    def requirements(self):
        self.requires("modern-cpp-kafka/2024.07.03")
