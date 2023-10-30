from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import cmake_layout, CMake
from conan.tools.scm import Version
import os
import re
import platform

class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    @property
    def _sufficient_linux_kernel_version(self):
        # FIXME: use kernel version of build/host machine. kernel version should be encoded in profile
        linux_kernel_version = re.match("([0-9.]+)", platform.release()).group(1)
        return Version(linux_kernel_version) >= "5.1"

    def test(self):
        if can_run(self) and self._sufficient_linux_kernel_version:
            bin_path = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(bin_path, env="conanrun")
