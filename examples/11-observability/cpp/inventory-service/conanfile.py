from conan import ConanFile

class CloudNative11InventoryConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    default_options = {"*/*:shared": False}

    def requirements(self):
        self.requires("grpc/1.54.3")
        self.requires("protobuf/3.21.12")
