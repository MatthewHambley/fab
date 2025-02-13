##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Common fixtures for PyTest.
"""
from typing import Dict, List, Optional

from pytest import fixture
from pytest_subprocess.fake_process import FakeProcess, ProcessRecorder

from fab.tools.tool_box import ToolBox


def not_found_callback(process):
    process.returncode = 1
    raise FileNotFoundError("Executable file missing")


def call_list(mock: FakeProcess) -> List[List[str]]:
    formed: List[List[str]] = []
    for call in mock.calls:
        formed.append([str(arg) for arg in call])
    return formed


class ExtendedRecorder:
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
        args: List[Dict[str, Optional[str]]] = []
        for call in self.recorder.calls:
            things: Dict[str, Optional[str]] = {}
            if call.kwargs is None:
                continue
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


@fixture(scope='function')
def subproc_record(fake_process: FakeProcess) -> ExtendedRecorder:
    """
    Mocks the 'subprocess' module and returns a recorder of commands issued.
    """
    fake_process.keep_last_process(True)
    return ExtendedRecorder(fake_process.register([FakeProcess.any()]))


@fixture(name="tool_box")
def fixture_tool_box(stub_c_compiler, mock_fortran_compiler, mock_linker):
    """Provides a tool box with a mock Fortran and a mock C compiler."""
    tool_box = ToolBox()
    tool_box.add_tool(stub_c_compiler)
    tool_box.add_tool(mock_fortran_compiler)
    tool_box.add_tool(mock_linker)
    return tool_box


@fixture(name="psyclone_lfric_api")
def fixture_psyclone_lfric_api():
    """A simple fixture to provide the name of the LFRic API for
    PSyclone."""
    return "dynamo0.3"
