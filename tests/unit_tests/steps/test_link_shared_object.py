# ##############################################################################
#  (c) Crown copyright Met Office. All rights reserved.
#  For further details please refer to the file COPYRIGHT
#  which you should have received as part of this distribution
# ##############################################################################

'''Tests linking a shared library.
'''

from pathlib import Path
from types import SimpleNamespace

from pytest_subprocess.fake_process import FakeProcess

from fab.artefacts import ArtefactSet, ArtefactStore
from fab.steps.link import link_shared_object
from fab.tools.linker import Linker

import pytest


def test_run(tool_box, monkeypatch, fake_process: FakeProcess):
    '''Ensure the command is formed correctly, with the flags at the
    end since they are typically libraries.'''

    config = SimpleNamespace(
        project_workspace=Path('workspace'),
        build_output=Path("workspace"),
        artefact_store=ArtefactStore(),
        openmp=False,
        tool_box=tool_box
    )
    config.artefact_store[ArtefactSet.OBJECT_FILES] = \
        {None: {'foo.o', 'bar.o'}}

    monkeypatch.setenv('LDFLAGS', '-L/foo1/lib -L/foo2/lib')
    fake_process.register(['mock_link.exe',
                           '-L/foo1/lib', '-L/foo2/lib',
                           '--version'], stdout='1.2.3')
    capture = fake_process.register(['mock_link.exe',
                                     '-L/foo1/lib', '-L/foo2/lib',
                                     'bar.o', 'foo.o',
                                     '-fooflag', '-barflag',
                                     '-fPIC', '-shared',
                                     '-o', '/tmp/lib_my.so'], stdout='abc\ndef')
    # We need to create a linker here to pick up the env var:
    linker = Linker("mock_link", Path("mock_link.exe"), "vendor")
    # Mark the linker as available so it can added to the tool box:
    tool_box.add_tool(linker, silent_replace=True)
    with pytest.warns(UserWarning,
                      match="_metric_send_conn not set, cannot send metrics"):
        link_shared_object(config, "/tmp/lib_my.so",
                           flags=['-fooflag', '-barflag'])
    assert [call.args for call in capture.calls] \
        == [['mock_link.exe', '-L/foo1/lib', '-L/foo2/lib', 'bar.o', 'foo.o',
             '-fooflag', '-barflag', '-fPIC', '-shared', '-o', '/tmp/lib_my.so']]
