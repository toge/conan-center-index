from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.microsoft import is_msvc_static_runtime, is_msvc, visual
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy, rm, rmdir, replace_in_file, rename
from conan.tools.build import check_min_cppstd, cross_building, valid_min_cppstd
from conan.tools.scm import Version
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
import os

required_conan_version = ">=1.52.0"

class GRPCConan(ConanFile):
    name = "grpc"
    description = "Google's RPC (remote procedure call) library and framework."
    license = "Apache-2.0"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/grpc/grpc"
    topics = ("grpc", "rpc")
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "codegen": [True, False],
        "csharp_ext": [True, False],
        "cpp_plugin": [True, False],
        "csharp_plugin": [True, False],
        "node_plugin": [True, False],
        "objective_c_plugin": [True, False],
        "php_plugin": [True, False],
        "python_plugin": [True, False],
        "ruby_plugin": [True, False],
        "secure": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "codegen": True,
        "csharp_ext": False,
        "cpp_plugin": True,
        "csharp_plugin": True,
        "node_plugin": True,
        "objective_c_plugin": True,
        "php_plugin": True,
        "python_plugin": True,
        "ruby_plugin": True,
        "secure": False,
    }
    short_paths = True

    @property
    def _grpc_plugin_template(self):
        return "grpc_plugin_template.cmake.in"

    @property
    def _minimum_cpp_standard(self):
        return 14 if Version(self.version) >= "1.47" else 11

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            try:
                del self.options.fPIC
            except Exception:
                pass
            self.options["protobuf"].shared = True
            self.options["googleapis"].shared = True
            self.options["grpc-proto"].shared = True

    def requirements(self):
        self.requires("abseil/20220623.0")
        self.requires("c-ares/1.18.1")
        self.requires("openssl/1.1.1q")
        self.requires("re2/20220601")
        self.requires("zlib/1.2.12")
        self.requires("protobuf/3.21.4")
        self.requires("googleapis/cci.20220711")
        self.requires("grpc-proto/cci.20220627")

    def validate(self):
        if is_msvc(self):
            if self.info.settings.compiler == "Visual Studio":
                vs_ide_version = self.info.settings.compiler.version
            else:
                vs_ide_version = visual.msvc_version_to_vs_ide_version(self.info.settings.compiler.version)
            if Version(vs_ide_version) < "14":
                raise ConanInvalidConfiguration(f"{self.ref} can only be built with Visual Studio 2015 or higher.")

            if self.options.shared:
                raise ConanInvalidConfiguration(f"{self.ref} shared not supported yet with Visual Studio")

        if Version(self.version) >= "1.47" and self.info.settings.compiler == "gcc" and Version(self.info.settings.compiler.version) < "6":
            raise ConanInvalidConfiguration("GCC older than 6 is not supported")

        if self.info.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, self._minimum_cpp_standard)

        if self.options.shared and (not self.options["protobuf"].shared or not self.options["googleapis"].shared or not self.options["grpc-proto"].shared):
            raise ConanInvalidConfiguration("If built as shared, protobuf, googleapis and grpc-proto must be shared as well. Please, use `protobuf:shared=True` and `googleapis:shared=True` and `grpc-proto:shared=True`")

    def package_id(self):
        del self.info.options.secure
        self.info.requires["protobuf"].full_package_mode()

    def build_requirements(self):
        if hasattr(self, "settings_build"):
            self.tool_requires('protobuf/3.21.4')
            # when cross compiling we need pre compiled grpc plugins for protoc
            if cross_building(self):
                self.build_requires('grpc/{}'.format(self.version))

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
                  destination=self.source_folder, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # This doesn't work yet as one would expect, because the install target builds everything
        # and we need the install target because of the generated CMake files
        #
        #   enable_mobile=False # Enables iOS and Android support
        #
        # cmake.definitions["CONAN_ENABLE_MOBILE"] = "ON" if self.options.csharp_ext else "OFF"

        tc.variables["gRPC_BUILD_CODEGEN"] = self.options.codegen
        tc.variables["gRPC_BUILD_CSHARP_EXT"] = self.options.csharp_ext
        tc.variables["gRPC_BUILD_TESTS"] = False

        # We need the generated cmake/ files (bc they depend on the list of targets, which is dynamic)
        tc.variables["gRPC_INSTALL"] = True
        tc.variables["gRPC_INSTALL_SHAREDIR"] = "res/grpc"

        # tell grpc to use the find_package versions
        tc.variables["gRPC_ZLIB_PROVIDER"] = "package"
        tc.variables["gRPC_CARES_PROVIDER"] = "package"
        tc.variables["gRPC_RE2_PROVIDER"] = "package"
        tc.variables["gRPC_SSL_PROVIDER"] = "package"
        tc.variables["gRPC_PROTOBUF_PROVIDER"] = "package"
        tc.variables["gRPC_ABSL_PROVIDER"] = "package"

        tc.variables["gRPC_BUILD_GRPC_CPP_PLUGIN"] = self.options.cpp_plugin
        tc.variables["gRPC_BUILD_GRPC_CSHARP_PLUGIN"] = self.options.csharp_plugin
        tc.variables["gRPC_BUILD_GRPC_NODE_PLUGIN"] = self.options.node_plugin
        tc.variables["gRPC_BUILD_GRPC_OBJECTIVE_C_PLUGIN"] = self.options.objective_c_plugin
        tc.variables["gRPC_BUILD_GRPC_PHP_PLUGIN"] = self.options.php_plugin
        tc.variables["gRPC_BUILD_GRPC_PYTHON_PLUGIN"] = self.options.python_plugin
        tc.variables["gRPC_BUILD_GRPC_RUBY_PLUGIN"] = self.options.ruby_plugin

        # Consumed targets (abseil) via interface target_compiler_feature can propagate newer standards
        if not valid_min_cppstd(self, self._minimum_cpp_standard):
            tc.variables["CMAKE_CXX_STANDARD"] = self._minimum_cpp_standard

        if cross_building(self):
            # otherwise find_package() can't find config files since
            # conan doesn't populate CMAKE_FIND_ROOT_PATH
            tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"

        if is_apple_os(self):
            # workaround for: install TARGETS given no BUNDLE DESTINATION for MACOSX_BUNDLE executable
            tc.variables["CMAKE_MACOSX_BUNDLE"] = False

        if is_msvc(self) and Version(self.version) >= "1.48":
            tc.variables["CMAKE_SYSTEM_VERSION"] = "10.0.18362.0"
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def _patch_sources(self):
        apply_conandata_patches(self)

        # Clean existing proto files, they will be taken from requirements
        rmdir(self, os.path.join(self.source_folder, "src", "proto", "grpc"))

        if Version(self.version) >= "1.47":
            # Take googleapis from requirement instead of vendored/hardcoded version
            replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                "if (NOT EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/third_party/googleapis)",
                "if (FALSE)  # Do not download, it is provided by Conan"
            )

        # We are fine with protobuf::protoc coming from conan generated Find/config file
        # TODO: to remove when moving to CMakeToolchain (see https://github.com/conan-io/conan/pull/10186)
        replace_in_file(self, os.path.join(self.source_folder, "cmake", "protobuf.cmake"),
            "find_program(_gRPC_PROTOBUF_PROTOC_EXECUTABLE protoc)",
            "set(_gRPC_PROTOBUF_PROTOC_EXECUTABLE $<TARGET_FILE:protobuf::protoc>)"
        )

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, os.pardir))
        cmake.build()

    def package(self):
        self.copy(pattern="LICENSE", dst="licenses", src=self.source_folder)
        cmake = self._configure_cmake()
        cmake.install()

        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

        # Create one custom module file per executable in order to emulate
        # CMake executables imported targets of grpc
        for plugin_option, values in self._grpc_plugins.items():
            if self.options.get_safe(plugin_option):
                target = values["target"]
                executable = values["executable"]
                self._create_executable_module_file(target, executable)

    @property
    def _grpc_plugins(self):
        return {
            "cpp_plugin": {
                "target": "gRPC::grpc_cpp_plugin",
                "executable": "grpc_cpp_plugin",
            },
            "csharp_plugin": {
                "target": "gRPC::grpc_csharp_plugin",
                "executable": "grpc_csharp_plugin",
            },
            "node_plugin": {
                "target": "gRPC::grpc_node_plugin",
                "executable": "grpc_node_plugin",
            },
            "objective_c_plugin": {
                "target": "gRPC::grpc_objective_c_plugin",
                "executable": "grpc_objective_c_plugin",
            },
            "php_plugin": {
                "target": "gRPC::grpc_php_plugin",
                "executable": "grpc_php_plugin",
            },
            "python_plugin": {
                "target": "gRPC::grpc_python_plugin",
                "executable": "grpc_python_plugin",
            },
            "ruby_plugin": {
                "target": "gRPC::grpc_ruby_plugin",
                "executable": "grpc_ruby_plugin",
            },
        }

    def _create_executable_module_file(self, target, executable):
        # Copy our CMake module template file to package folder
        copy(self, self._grpc_plugin_template, dst=self._module_path,
                  src=os.path.join(self.source_folder, "cmake"))

        # Rename it
        dst_file = os.path.join(self.package_folder, self._module_path,
                                "{}.cmake".format(executable))
        rename(self, os.path.join(self.package_folder, self._module_path, self._grpc_plugin_template),
                     dst_file)

        # Replace placeholders
        replace_in_file(self, dst_file, "@target_name@", target)
        replace_in_file(self, dst_file, "@executable_name@", executable)

        find_program_var = "{}_PROGRAM".format(executable.upper())
        replace_in_file(self, dst_file, "@find_program_variable@", find_program_var)

        module_folder_depth = len(os.path.normpath(self._module_path).split(os.path.sep))
        rel_path = "".join(["../"] * module_folder_depth)
        replace_in_file(self, dst_file, "@relative_path@", rel_path)

    @property
    def _module_path(self):
        return os.path.join(self.package_folder, "lib", "cmake", "conan_trick")

    @property
    def _grpc_components(self):
        def libm():
            return ["m"] if self.settings.os in ["Linux", "FreeBSD"] else []

        def pthread():
            return ["pthread"] if self.settings.os in ["Linux", "FreeBSD"] else []

        def crypt32():
            return ["crypt32"] if self.settings.os == "Windows" else []

        def ws2_32():
            return ["ws2_32"] if self.settings.os == "Windows" else []

        def wsock32():
            return ["wsock32"] if self.settings.os == "Windows" else []

        def corefoundation():
            return ["CoreFoundation"] if is_apple_os(self) else []

        components = {
            "address_sorting": {
                "lib": "address_sorting",
                "system_libs": libm() + pthread() + crypt32() + ws2_32() + wsock32(),
            },
            "gpr": {
                "lib": "gpr",
                "requires": [
                    "upb", "abseil::absl_base", "abseil::absl_memory",
                    "abseil::absl_status", "abseil::absl_str_format",
                    "abseil::absl_strings", "abseil::absl_synchronization",
                    "abseil::absl_time", "abseil::absl_optional",
                ],
                "system_libs": libm() + pthread() + crypt32() + ws2_32() + wsock32(),
            },
            "_grpc": {
                "lib": "grpc",
                "requires": [
                    "address_sorting", "gpr", "upb", "abseil::absl_bind_front",
                    "abseil::absl_flat_hash_map", "abseil::absl_inlined_vector",
                    "abseil::absl_statusor", "abseil::absl_random_random",
                    "c-ares::cares", "openssl::crypto",
                    "openssl::ssl", "re2::re2", "zlib::zlib",
                ],
                "system_libs": libm() + pthread() + crypt32() + ws2_32() + wsock32(),
                "frameworks": corefoundation(),
            },
            "grpc++": {
                "lib": "grpc++",
                "requires": ["_grpc", "protobuf::libprotobuf"],
                "system_libs": libm() + pthread() + crypt32() + ws2_32() + wsock32(),
            },
            "grpc++_alts": {
                "lib": "grpc++_alts",
                "requires": ["grpc++", "protobuf::libprotobuf"],
                "system_libs": libm() + pthread() + crypt32() + ws2_32() + wsock32(),
            },
            "grpc++_error_details": {
                "lib": "grpc++_error_details",
                "requires": ["grpc++", "protobuf::libprotobuf"],
                "system_libs": libm() + pthread() + crypt32() + ws2_32() + wsock32(),
            },
            "upb": {
                "lib": "upb",
                "system_libs": libm() + pthread() + crypt32() + ws2_32() + wsock32(),
            },
            "grpc_plugin_support": {
                "lib": "grpc_plugin_support",
                "requires": ["protobuf::libprotoc", "protobuf::libprotobuf"],
                "system_libs": libm() + pthread() + crypt32() + ws2_32() + wsock32(),
            },
        }

        if not self.options.secure:
            components.update({
                "grpc_unsecure": {
                    "lib": "grpc_unsecure",
                    "requires": [
                        "address_sorting", "gpr", "upb", "abseil::absl_flat_hash_map",
                        "abseil::absl_inlined_vector", "abseil::absl_statusor",
                        "c-ares::cares", "re2::re2", "zlib::zlib",
                        "abseil::absl_random_random",
                    ],
                    "system_libs": libm() + pthread() + crypt32() + ws2_32() + wsock32(),
                    "frameworks": corefoundation(),
                },
                "grpc++_unsecure": {
                    "lib": "grpc++_unsecure",
                    "requires": ["grpc_unsecure", "protobuf::libprotobuf"],
                    "system_libs": libm() + pthread() + crypt32() + ws2_32() + wsock32(),
                },
            })

        if self.options.codegen:
            components.update({
                "grpc++_reflection": {
                    "lib": "grpc++_reflection",
                    "requires": ["grpc++", "protobuf::libprotobuf", "grpc-proto::grpc-proto", "googleapis::googleapis"],
                    "system_libs": libm() + pthread() + crypt32() + ws2_32() + wsock32(),
                },
                "grpcpp_channelz": {
                    "lib": "grpcpp_channelz",
                    "requires": ["grpc++", "protobuf::libprotobuf", "grpc-proto::grpc-proto", "googleapis::googleapis"],
                    "system_libs": libm() + pthread() + crypt32() + ws2_32() + wsock32(),
                },
            })

        return components

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "gRPC")
        ssl_roots_file_path = os.path.join(self.package_folder, "res", "grpc", "roots.pem")
        self.runenv_info.define_path("GRPC_DEFAULT_SSL_ROOTS_FILE_PATH", ssl_roots_file_path)
        self.env_info.GRPC_DEFAULT_SSL_ROOTS_FILE_PATH = ssl_roots_file_path # remove in conan v2?

        for component, values in self._grpc_components.items():
            target = values.get("lib")
            lib = values.get("lib")
            self.cpp_info.components[component].set_property("cmake_target_name", "gRPC::{}".format(target))
            # actually only gpr, grpc, grpc_unsecure, grpc++ and grpc++_unsecure should have a .pc file
            self.cpp_info.components[component].set_property("pkg_config_name", target)
            self.cpp_info.components[component].libs = [lib]
            self.cpp_info.components[component].requires = values.get("requires", [])
            self.cpp_info.components[component].system_libs = values.get("system_libs", [])
            self.cpp_info.components[component].frameworks = values.get("frameworks", [])

            # TODO: to remove in conan v2 once cmake_find_package_* generators removed
            self.cpp_info.components[component].names["cmake_find_package"] = target
            self.cpp_info.components[component].names["cmake_find_package_multi"] = target

        # Executable imported targets are added through custom CMake module files,
        # since conan generators don't know how to emulate these kind of targets.
        grpc_modules = []
        for plugin_option, values in self._grpc_plugins.items():
            if self.options.get_safe(plugin_option):
                grpc_module_filename = "{}.cmake".format(values["executable"])
                grpc_modules.append(os.path.join(self._module_path, grpc_module_filename))
        self.cpp_info.set_property("cmake_build_modules", grpc_modules)

        if any(self.options.get_safe(plugin_option) for plugin_option in self._grpc_plugins.keys()):
            bindir = os.path.join(self.package_folder, "bin")
            self.output.info("Appending PATH environment variable: {}".format(bindir))
            self.env_info.PATH.append(bindir)

        # TODO: to remove in conan v2 once cmake_find_package_* generators removed
        self.cpp_info.names["cmake_find_package"] = "gRPC"
        self.cpp_info.names["cmake_find_package_multi"] = "gRPC"
        if grpc_modules:
            self.cpp_info.components["grpc_execs"].build_modules["cmake_find_package"] = grpc_modules
            self.cpp_info.components["grpc_execs"].build_modules["cmake_find_package_multi"] = grpc_modules
