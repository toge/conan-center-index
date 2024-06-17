from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import cmake_layout, CMake
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("boost/1.85.0")
        self.requires("asio/1.30.2")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(bin_path, env="conanrun")
            bin_path = os.path.join(self.cpp.build.bindir, "test_package_asio")
            self.run(bin_path, env="conanrun")
            bin_path = os.path.join(self.cpp.build.bindir, "test_package_boost")
            self.run(bin_path, env="conanrun")
