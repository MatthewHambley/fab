# ##############################################################################
#  (c) Crown copyright Met Office. All rights reserved.
#  For further details please refer to the file COPYRIGHT
#  which you should have received as part of this distribution
# ##############################################################################
"""
Common PyTest fixtures.
"""
from pathlib import Path
from typing import Optional
from unittest import mock

from pytest import fixture
from pytest_subprocess.fake_process import FakeProcess, ProcessRecorder

from fab.tool_box import ToolBox
from fab.tools import Category
from fab.tools.compiler import CCompiler, FortranCompiler
from fab.tools.linker import Linker


@fixture(scope='function')
def mock_process(fake_process: FakeProcess) -> ProcessRecorder:
    """
    Overrides subprocess.POpen with a version which always succeedes and logs
    commands for inspection.
    """
    fake_process.keep_last_process(True)
    return fake_process.register([fake_process.any()])


class StubC(CCompiler):
    """
    Null C compiler which does not shell out to an actual compiler.
    """
    def __init__(self, name='stub_c_compiler',
                 exe=Path('stubc'),
                 suite='stubs',
                 openmp_arg='-openmpme',
                 special_version: Optional[str] = None,
                 special_present: Optional[bool] = None):
        super().__init__(name, exe, suite,
                         openmp_flag=openmp_arg)
        self.__special_version = special_version
        self.__special_present = special_present

    @property
    def is_available(self) -> bool:
        if self.__special_present:
            return self.__special_present
        else:
            return super().is_available

    def run_version_command(
            self,
            version_command: Optional[str] = '--version') -> str:
        if self.__special_version:
            return self.__special_version
        else:
            return super().run_version_command(version_command)

    def parse_version_output(self, category: Category,
                             version_output: str) -> str:
        return version_output


@fixture(scope="function")
def stub_c_compiler():
    """
    Provides a stubbed-out C compiler which does not shell out to a compiler.
    """
    return StubC()


@fixture(name="mock_fortran_compiler")
def fixture_mock_fortran_compiler():
    '''Provides a mock Fortran-compiler.'''
    mock_compiler = FortranCompiler("mock_fortran_compiler", "mock_exec",
                                    "suite", module_folder_flag="",
                                    syntax_only_flag=None, compile_flag=None,
                                    output_flag=None, openmp_flag=None)
    mock_compiler.run = mock.Mock()
    mock_compiler.__name = "mock_fortran_compiler"
    mock_compiler.__executable = "mock_fortran_compiler.exe"
    mock_compiler._version = (1, 2, 3)
    return mock_compiler


class StubLinker(Linker):
    def __init__(self,
                 name='stub_linker',
                 exe=Path('stubld'),
                 suite='stub',
                 special_present: Optional[bool] = None):
        super().__init__(name, exe, suite)
        self.__special_present = special_present

    @property
    def is_available(self) -> bool:
        if self.__special_present:
            return self.__special_present
        else:
            return super().is_available


# @fixture(name="mock_linker")
# def fixture_mock_linker():
#     '''Provides a mock linker.'''
#     mock_linker = Linker("mock_linker", "mock_linker.exe",
#                          Category.FORTRAN_COMPILER)
#     mock_linker.run = mock.Mock()
#     mock_linker._version = (1, 2, 3)
#     return mock_linker


@fixture(name="tool_box")
def fixture_tool_box(mock_fortran_compiler):
    '''Provides a tool box with a mock Fortran and a mock C compiler.'''
    tool_box = ToolBox()
    tool_box.add_tool(StubC(special_present=True))
    tool_box.add_tool(mock_fortran_compiler)
    tool_box.add_tool(StubLinker(special_present=True))
    return tool_box
