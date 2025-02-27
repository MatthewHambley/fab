# ##############################################################################
#  (c) Crown copyright Met Office. All rights reserved.
#  For further details please refer to the file COPYRIGHT
#  which you should have received as part of this distribution
# ##############################################################################
"""
Tests linking a shared library.
"""
from pathlib import Path
from types import SimpleNamespace

from pytest import warns
from pytest_subprocess.fake_process import FakeProcess

from tests.conftest import call_list

from fab.artefacts import ArtefactSet, ArtefactStore
from fab.steps.link import link_shared_object
from fab.tools.compiler import FortranCompiler
from fab.tools.linker import Linker
from fab.tools.tool_box import ToolBox


def test_run(fake_process: FakeProcess, monkeypatch) -> None:
    """
    Tests the construction of the command.
    """
    monkeypatch.setenv('FFLAGS', '-L/foo1/lib -L/foo2/lib')

    version_command = ['sfc', '-L/foo1/lib', '-L/foo2/lib', '--version']
    fake_process.register(version_command, stdout='1.2.3')
    link_command = ['sfc', '-L/foo1/lib', '-L/foo2/lib', 'bar.o', 'foo.o',
                    '-fooflag', '-barflag', '-fPIC', '-shared',
                    '-o', '/tmp/lib_my.so']
    fake_process.register(link_command, stdout='abc\ndef')

    compiler = FortranCompiler("some Fortran compiler", 'sfc', 'some',
                               r'([\d.]+)')
    linker = Linker(compiler=compiler)

    tool_box = ToolBox()
    config = SimpleNamespace(
        project_workspace=Path('workspace'),
        build_output=Path("workspace"),
        artefact_store=ArtefactStore(),
        openmp=False,
        tool_box=tool_box
    )
    tool_box.add_tool(linker)

    config.artefact_store[ArtefactSet.OBJECT_FILES] = \
        {None: {'foo.o', 'bar.o'}}

    with warns(UserWarning, match="_metric_send_conn not set, "
                                    "cannot send metrics"):
        link_shared_object(config, "/tmp/lib_my.so",
                           flags=['-fooflag', '-barflag'])
    assert call_list(fake_process) == [
        version_command, link_command
    ]
