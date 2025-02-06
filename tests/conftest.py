##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Common fixtures for PyTest.
"""
from typing import Dict, List, Optional
from unittest import mock

import pytest
from pytest_subprocess.fake_process import FakeProcess, ProcessRecorder

from fab.tools import CCompiler, FortranCompiler, Linker, ToolBox


class ExtendedRecorder():
    """
    Adds convenience functionality to ProcessRecorder.
    """
    def __init__(self, recorder: ProcessRecorder):
        self.recorder = recorder

    def invocations(self) -> List[List[str]]:
        """
        Lists invocations as simple string lists.
        """
        calls = []
        for call in self.recorder.calls:
            calls.append([str(arg) for arg in call.args])
        return calls

    def extras(self) -> List[Dict[str, Optional[str]]]:
        args = []
        for call in self.recorder.calls:
            things = {}
            for key, value in call.kwargs.items():
                if value is None:
                    things[key] = None
                else:
                    if key in ('stdout', 'stderr') and value == -1:
                        things[key] = None
                    else:
                        things[key] = str(value)
            args.append(things)
        return args


@pytest.fixture(scope='function')
def subproc_record(fake_process: FakeProcess) -> ExtendedRecorder:
    """
    Mocks the 'subprocess' module and returns a recorder of commands issued.
    """
    fake_process.keep_last_process(True)
    return ExtendedRecorder(fake_process.register([FakeProcess.any()]))


# This avoids pylint warnings about Redefining names from outer scope
@pytest.fixture(name="mock_c_compiler")
def fixture_mock_c_compiler():
    """Provides a mock C-compiler."""
    mock_compiler = CCompiler("mock_c_compiler", "mock_exec", "suite",
                              version_regex="something")
    mock_compiler.run = mock.Mock()
    mock_compiler._version = (1, 2, 3)
    mock_compiler._name = "mock_c_compiler"
    mock_compiler._exec_name = "mock_c_compiler.exe"
    mock_compiler._openmp_flag = "-fopenmp"
    return mock_compiler


@pytest.fixture(name="mock_fortran_compiler")
def fixture_mock_fortran_compiler():
    """Provides a mock Fortran-compiler."""
    mock_compiler = FortranCompiler("mock_fortran_compiler", "mock_exec",
                                    "suite", module_folder_flag="",
                                    version_regex="something",
                                    syntax_only_flag=None, compile_flag=None,
                                    output_flag=None, openmp_flag=None)
    mock_compiler.run = mock.Mock()
    mock_compiler._name = "mock_fortran_compiler"
    mock_compiler._exec_name = "mock_fortran_compiler.exe"
    mock_compiler._version = (1, 2, 3)
    return mock_compiler


@pytest.fixture(name="mock_linker")
def fixture_mock_linker(mock_fortran_compiler):
    """Provides a mock linker."""
    mock_linker = Linker(mock_fortran_compiler)
    mock_linker.run = mock.Mock()
    mock_linker._version = (1, 2, 3)
    mock_linker.add_lib_flags("netcdf", ["-lnetcdff", "-lnetcdf"])
    return mock_linker


@pytest.fixture(name="tool_box")
def fixture_tool_box(mock_c_compiler, mock_fortran_compiler, mock_linker):
    """Provides a tool box with a mock Fortran and a mock C compiler."""
    tool_box = ToolBox()
    tool_box.add_tool(mock_c_compiler)
    tool_box.add_tool(mock_fortran_compiler)
    tool_box.add_tool(mock_linker)
    return tool_box


@pytest.fixture(name="psyclone_lfric_api")
def fixture_psyclone_lfric_api():
    """A simple fixture to provide the name of the LFRic API for
    PSyclone."""
    return "dynamo0.3"
