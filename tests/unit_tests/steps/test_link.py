# ##############################################################################
#  (c) Crown copyright Met Office. All rights reserved.
#  For further details please refer to the file COPYRIGHT
#  which you should have received as part of this distribution
# ##############################################################################
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from pytest_subprocess.fake_process import FakeProcess

from fab.artefacts import ArtefactSet, ArtefactStore
from fab.steps.link import link_exe
from fab.tools.linker import Linker

import pytest


class TestLinkExe:
    def test_run(self, tool_box, monkeypatch, fake_process: FakeProcess):
        # ensure the command is formed correctly, with the flags at the
        # end (why?!)

        config = SimpleNamespace(
            project_workspace=Path('workspace'),
            artefact_store=ArtefactStore(),
            tool_box=tool_box,
            mpi=False,
            openmp=False,
        )
        config.artefact_store[ArtefactSet.OBJECT_FILES] = \
            {'foo': {'foo.o', 'bar.o'}}

        monkeypatch.setenv('LDFLAGS', '-L/foo1/lib -L/foo2/lib')
        fake_process.register(['mock_link.exe',
                               '-L/foo1/lib', '-L/foo2/lib',
                               '--version'], stdout='1.2.3')
        # We need to create a linker here to pick up the env var:
        linker = Linker("mock_link", Path("mock_link.exe"), "mock-vendor")
        # Mark the linker as available to it can be added to the tool box
        tool_box.add_tool(linker, silent_replace=True)

        fake_process.register(['mock_link.exe',
                               '-L/foo1/lib', '-L/foo2/lib',
                               'bar.o', 'foo.o',
                               '-fooflag', '-barflag',
                               '-o', 'workspace/foo'], stdout="abc\ndef")
        with pytest.warns(UserWarning,
                          match="_metric_send_conn not set, cannot send metrics"):
            link_exe(config, flags=['-fooflag', '-barflag'])
