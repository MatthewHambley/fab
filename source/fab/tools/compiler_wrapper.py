##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################

"""This file contains the base class for any compiler, and derived
classes for gcc, gfortran, icc, ifort
"""

from pathlib import Path
from typing import cast, List, Optional, Tuple, Union

from fab.tools.category import Category
from fab.tools.compiler import Compiler, FortranCompiler
from fab.tools.flags import Flags


class CompilerWrapper(Compiler):
    '''A decorator-based compiler wrapper. It basically uses a different
    executable name when compiling, but otherwise behaves like the wrapped
    compiler. An example of a compiler wrapper is `mpif90` (which can
    internally call e.g. gfortran, icc, ...)

    :param name: name of the wrapper.
    :param exec_name: name of the executable to call.
    :param compiler: the compiler that is decorated.
    :param mpi: whether MPI is supported by this compiler or not.
    '''

    def __init__(self, name: str, exec_name: str,
                 compiler: Compiler,
                 mpi: bool = False):
        self._compiler = compiler
        super().__init__(
            name=name, exec_name=exec_name,
            category=self._compiler.category,
            suite=self._compiler.suite,
            mpi=mpi,
            availablility_option=self._compiler.availablility_option)
        # We need to have the right version to parse the version output
        # So we set this function based on the function that the
        # wrapped compiler uses:
        self.parse_version_output = compiler.parse_version_output

    def __str__(self):
        return f"{type(self).__name__}({self._compiler.name})"

    def get_version(self) -> Tuple[int, ...]:
        """
        :returns: a tuple of at least 2 integers, representing the version
            e.g. (6, 10, 1) for version '6.10.1'.

        :raises RuntimeError: if the compiler was not found, or if it returned
            an unrecognised output from the version command.
        """

        if self._version is not None:
            return self._version

        try:
            compiler_version = self._compiler.get_version()
        except RuntimeError as err:
            raise RuntimeError(f"Cannot get version of wrapped compiler '"
                               f"{self._compiler}") from err

        wrapper_version = super().get_version()
        if compiler_version != wrapper_version:
            compiler_version_string = self._compiler.get_version_string()
            # We cannot call super().get_version_string() calls get_version
            # so we get an infinite recursion
            wrapper_version_string = ".".join(str(x) for x in wrapper_version)
            raise RuntimeError(f"Different version for compiler "
                               f"'{self._compiler}' "
                               f"({compiler_version_string}) and compiler "
                               f"wrapper '{self}' ({wrapper_version_string}).")
        self._version = wrapper_version
        return wrapper_version

    @property
    def is_available(self) -> bool:
        '''Checks if the tool is available or not.

        :returns: whether the tool is available (i.e. installed and
            working).
        '''

        # Rely on `get_version` to do the heavy lifting (e.g. verifying that
        # both the wrapper and the wrapped compiler do report the same
        # version number) - so if we have a valid version, we can be sure
        # the compiler is available, otherwise it is not available or
        # inconsistent, in which case it should not be used.
        if self._is_available is not None:
            return self._is_available
        try:
            # This will raise an exception if the compiler is not available
            self.get_version()
            self._is_available = True
        except RuntimeError:
            self._is_available = False
        return self._is_available

    @property
    def category(self) -> Category:
        ''':returns: the category of this tool.'''
        return self._compiler.category

    @property
    def flags(self) -> Flags:
        ''':returns: the flags to be used with this tool.'''
        return self._compiler.flags

    @property
    def suite(self) -> str:
        ''':returns: the compiler suite of this tool.'''
        return self._compiler.suite

    @property
    def has_syntax_only(self) -> bool:
        ''':returns: whether this compiler supports a syntax-only feature.

        :raises RuntimeError: if this function is called for a non-Fortran
            wrapped compiler.
        '''

        if self._compiler.category == Category.FORTRAN_COMPILER:
            return cast(FortranCompiler, self._compiler).has_syntax_only

        raise RuntimeError(f"Compiler '{self._compiler.name}' has "
                           f"no has_syntax_only.")

    def set_module_output_path(self, path: Path):
        '''Sets the output path for modules.

        :params path: the path to the output directory.

        :raises RuntimeError: if this function is called for a non-Fortran
            wrapped compiler.
        '''

        if self._compiler.category != Category.FORTRAN_COMPILER:
            raise RuntimeError(f"Compiler '{self._compiler.name}' has no "
                               f"'set_module_output_path' function.")
        cast(FortranCompiler, self._compiler).set_module_output_path(path)

    def compile_file(self, input_file: Path,
                     output_file: Path,
                     openmp: bool,
                     add_flags: Union[None, List[str]] = None,
                     syntax_only: Optional[bool] = None):
        # pylint: disable=too-many-arguments
        '''Compiles a file using the wrapper compiler. It will temporarily
        change the name of the wrapped compiler, and then calls the original
        compiler (to get all its parameters)

        :param input_file: the name of the input file.
        :param output_file: the name of the output file.
        :param openmp: if compilation should be done with OpenMP.
        :param add_flags: additional flags for the compiler.
        :param syntax_only: if set, the compiler will only do
            a syntax check
        '''

        orig_compiler_name = self._compiler.exec_name
        self._compiler.change_exec_name(self.exec_name)
        if isinstance(self._compiler, FortranCompiler):
            self._compiler.compile_file(input_file, output_file, openmp=openmp,
                                        add_flags=add_flags,
                                        syntax_only=syntax_only,
                                        )
        else:
            if syntax_only is not None:
                raise RuntimeError(f"Syntax-only cannot be used with compiler "
                                   f"'{self.name}'.")
            self._compiler.compile_file(input_file, output_file, openmp=openmp,
                                        add_flags=add_flags
                                        )
        self._compiler.change_exec_name(orig_compiler_name)


# ============================================================================
class Mpif90(CompilerWrapper):
    '''Class for a simple wrapper for using a compiler driver (like mpif90)
    It will be using the name "mpif90-COMPILER_NAME" and calls `mpif90`.
    All flags from the original compiler will be used when using the wrapper
    as compiler.

    :param compiler: the compiler that the mpif90 wrapper will use.
    '''

    def __init__(self, compiler: Compiler):
        super().__init__(name=f"mpif90-{compiler.name}",
                         exec_name="mpif90", compiler=compiler, mpi=True)


# ============================================================================
class Mpicc(CompilerWrapper):
    '''Class for a simple wrapper for using a compiler driver (like mpicc)
    It will be using the name "mpicc-COMPILER_NAME" and calls `mpicc`.
    All flags from the original compiler will be used when using the wrapper
    as compiler.
s
    :param compiler: the compiler that the mpicc wrapper will use.
    '''

    def __init__(self, compiler: Compiler):
        super().__init__(name=f"mpicc-{compiler.name}",
                         exec_name="mpicc", compiler=compiler, mpi=True)
