from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.scm import Version
from conan.tools.microsoft import is_msvc
import os

required_conan_version = ">=1.53.0"

class MiniscriptConan(ConanFile):
    name = "miniscript"
    description = "modern, elegant, easy to learn, and easy to embed in your own C# or C++ projects."
    license = "MIT"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/JoeStrout/miniscript"
    topics = ("script", "embedded", "programming-language")
    settings = "os", "arch", "compiler", "build_type"
    package_type = "library"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    exports_sources = ["CMakeLists.txt"]

    @property
    def _min_cppstd(self):
        return "11" if Version(self.version) < "1.6.2" else "17"

    @property
    def _compilers_minimum_version(self):
        return {
            "17": {
                "gcc": "8",
                "clang": "7",
                "apple-clang": "12",
                "Visual Studio": "16",
                "msvc": "192",
            },
        }.get(self._min_cppstd, {})

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == 'Windows':
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        # miniscript doesn't declare export symbols with __declspec.
        if is_msvc(self) and self.options.shared:
            raise ConanInvalidConfiguration(
                f"{self.ref} doesn't support msvc shared build.(yet)"
            )

        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, self._min_cppstd)
        minimum_version = self._compilers_minimum_version.get(str(self.settings.compiler), False)
        if minimum_version and Version(self.settings.compiler.version) < minimum_version:
            raise ConanInvalidConfiguration(
                f"{self.ref} requires C++{self._min_cppstd}, which your compiler does not support."
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if Version(self.version) >= "1.6.2":
            tc.variables["CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS"] = True
        else:
            tc.variables["MINISCRIPT_SRC_DIR"] = self.source_folder.replace("\\", "/")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        if Version(self.version) >= "1.6.2":
            cmake.configure()
        else:
            cmake.configure(build_script_folder=os.path.join(self.source_folder, os.pardir))
        cmake.build()

    def package(self):
        copy(self, pattern="LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["miniscript-cpp"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
            self.cpp_info.system_libs.append("pthread")
