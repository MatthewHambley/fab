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

from fab.tools.compiler import CCompiler, FortranCompiler
from fab.tools.linker import Linker
from fab.tools.tool_box import ToolBox


def not_found_callback(process):
    process.returncode = 1
    raise FileNotFoundError("Executable file missing")


def call_list(fake_process: FakeProcess) -> List[List[str]]:
    result: List[List[str]] = []
    for call in fake_process.calls:
        result.append([str(arg) for arg in call])
    return result


def arg_list(record: ProcessRecorder) -> List[Dict[str, str]]:
    result: List[Dict[str, str]] = []
    for call in record.calls:
        if call.kwargs is None:
            args = {}
        else:
            args = {key: str(value) for key, value in call.kwargs.items()}
        result.append(args)
    return result


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


@fixture(scope='function')
def stub_fortran_compiler() -> FortranCompiler:
    compiler = FortranCompiler('some Fortran compiler', 'sfc', 'stub',
                               r'([\d.]+)')
    return compiler


@fixture(scope='function')
def stub_c_compiler() -> CCompiler:
    """
    Provides a minial C compiler.
    """
    compiler = CCompiler("some C compiler", "scc", "stub",
                         version_regex=r"([\d.]+)", openmp_flag='-omp')
    return compiler


@fixture(scope='function')
def stub_linker(stub_c_compiler) -> Linker:
    """
    Provides a minimal linker.
    """
    linker = Linker(stub_c_compiler, 'sln', 'stub')
    return linker


def return_true():
    return True

@fixture(scope='function')
def stub_tool_box(stub_fortran_compiler,
                  stub_c_compiler,
                  stub_linker,
                  monkeypatch) -> ToolBox:
    """
    Provides a minimal toolbox containing just a Fortran compiler and a linker.
    """
    monkeypatch.setattr(stub_fortran_compiler, 'check_available', return_true)
    monkeypatch.setattr(stub_c_compiler, 'check_available', return_true)
    toolbox = ToolBox()
    toolbox.add_tool(stub_fortran_compiler)
    toolbox.add_tool(stub_c_compiler)
    toolbox.add_tool(stub_linker)
    return toolbox
