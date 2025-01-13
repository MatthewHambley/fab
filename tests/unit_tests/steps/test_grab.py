##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
from pathlib import Path
from types import SimpleNamespace

from pytest import mark
from pytest_subprocess.fake_process import FakeProcess

from fab.steps.grab.fcm import fcm_export
from fab.steps.grab.folder import grab_folder
from fab.tool_box import ToolBox

import pytest


class TestGrabFolder:
    @mark.parametrize(['grab_src', 'expected_grab_src'],
                      [('/grab/source/', '/grab/source/'),
                       ('/grab/source', '/grab/source/')])
    def test_folder_grabber(self, grab_src, expected_grab_src,
                            tmp_path: Path, fake_process: FakeProcess):
        source_root = tmp_path / 'source'
        mock_config = SimpleNamespace(source_root=source_root,
                                      tool_box=ToolBox())

        expected_call = ['rsync', '--times', '--links', '--stats',
                         '-ru', expected_grab_src, str(source_root / 'bar')]
        record = fake_process.register(expected_call)
        with pytest.warns(UserWarning,
                          match="_metric_send_conn not set, cannot send metrics"):
            grab_folder(mock_config, src=grab_src, dst_label='bar')
        assert record.call_count(expected_call) == 1


class TestGrabFcm:

    def test_no_revision(self, fake_process: FakeProcess, tmp_path: Path):
        source_root = tmp_path / 'source'

        mock_config = SimpleNamespace(source_root=source_root,
                                      tool_box=ToolBox())

        expected_call = ['fcm', 'export', '--force',
                         '/www.example.com/bar', str(source_root / 'bar')]
        record = fake_process.register(expected_call)
        with pytest.warns(UserWarning,
                          match="_metric_send_conn not set, cannot send metrics"):
            fcm_export(config=mock_config, src='/www.example.com/bar', dst_label='bar')
        assert record.call_count(expected_call) == 1

    def test_revision(self, fake_process: FakeProcess, tmp_path: Path):
        source_root = tmp_path / 'source'

        mock_config = SimpleNamespace(source_root=source_root,
                                      tool_box=ToolBox())

        expected_call = ['fcm', 'export', '--force',
                         '--revision', '42',
                         '/www.example.com/bar', str(source_root / 'bar')]
        record = fake_process.register(expected_call)
        with pytest.warns(UserWarning,
                          match="_metric_send_conn not set, cannot send metrics"):
            fcm_export(mock_config, src='/www.example.com/bar',
                       dst_label='bar', revision=42)

        assert record.call_count(expected_call) == 1

    # todo: test missing repo
    # def test_missing(self):
    #     assert False
