##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################

"""This file contains the base class for any Linker.
"""

import os
from pathlib import Path
from typing import cast, List, Optional

from fab.category import Category
from fab.tools.compiler import Compiler
from fab.tools import CompilerSuiteTool


class Linker(CompilerSuiteTool):
    '''This is the base class for any Linker. If a compiler is specified,
    its name, executable, and compile suite will be used for the linker (if
    not explicitly set in the constructor).

    :param name: the name of the linker.
    :param executable: the name of the executable.
    :param suite: optional, the name of the suite.
    :param compiler: optional, a compiler instance
    :param output_flag: flag to use to specify the output name.
    '''
    def __init__(self, name: Optional[str] = None,
                 executable: Optional[Path] = None,
                 suite: Optional[str] = None,
                 compiler: Optional[Compiler] = None,
                 output_flag: str = "-o"):
        if (not name or not executable or not suite) and not compiler:
            raise RuntimeError("Either specify name, exec name, and suite "
                               "or a compiler when creating Linker.")
        # Make mypy happy, since it can't work out otherwise if these string
        # variables might still be None :(
        compiler = cast(Compiler, compiler)
        if not name:
            name = compiler.name
        if not executable:
            executable = compiler.executable
        if not suite:
            suite = compiler.suite
        self._output_flag = output_flag
        super().__init__(name, executable, suite, Category.LINKER)
        self._compiler = compiler
        self.flags.extend(os.getenv("LDFLAGS", "").split())

    @property
    def mpi(self) -> bool:
        ''':returns: whether the linker supports MPI or not.'''
        return self._compiler.mpi

    @property
    def is_available(self) -> bool:
        '''
        :returns: whether the linker is available or not. We do this
            by requesting the linker version.
        '''
        if self._compiler:
            return self._compiler.is_available

        return super().is_available

    def link(self, input_files: List[Path], output_file: Path,
             openmp: bool,
             add_libs: Optional[List[str]] = None) -> str:
        '''Executes the linker with the specified input files,
        creating `output_file`.

        :param input_files: list of input files to link.
        :param output_file: output file.
        :param openm: whether OpenMP is requested or not.
        :param add_libs: additional linker flags.

        :returns: the stdout of the link command
        '''
        if self._compiler:
            # Create a copy:
            params = self._compiler.flags[:]
            if openmp:
                params.append(self._compiler.openmp_flag)
        else:
            params = []
        # TODO: why are the .o files sorted? That shouldn't matter
        params.extend(sorted(map(str, input_files)))
        if add_libs:
            params += add_libs
        params.extend([self._output_flag, str(output_file)])
        return self.run(params)
