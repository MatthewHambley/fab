##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Test for the archive step.
"""
from pathlib import Path

from pytest import raises, warns
from pytest_subprocess.fake_process import FakeProcess

from fab.artefacts import ArtefactSet
from fab.build_config import BuildConfig
from fab.steps.archive_objects import archive_objects
from fab.category import Category
from fab.tool_box import ToolBox


class TestArchiveObjects:
    """
    Test the achive step.
    """
    def test_for_executables(self, tmp_path: Path, fake_process: FakeProcess):
        """
        As used when archiving before linking executables.
        """
        targets = ['prog1', 'prog2']

        config = BuildConfig('proj', ToolBox(),
                             fab_workspace=tmp_path)
        for target in targets:
            config.artefact_store.update_dict(
                ArtefactSet.OBJECT_FILES, target,
                {target + '.o', 'util.o'})

        command1 = ['ar', 'cr', str(config.build_output / 'prog1.a'),
                    'prog1.o', 'util.o']
        recorder1 = fake_process.register(command1, stdout='Archiving prog1')
        command2 = ['ar', 'cr', str(config.build_output / 'prog2.a'),
                    'prog2.o', 'util.o']
        recorder2 = fake_process.register(command2, stdout='Archiving prog2')
        with warns(UserWarning, match="_metric_send_conn not set, "
                                      "cannot send metrics"):
            archive_objects(config=config)
        assert recorder1.call_count(command1) == 1
        assert recorder2.call_count(command2) == 1

        # ensure the correct artefacts were created
        assert config.artefact_store[ArtefactSet.OBJECT_ARCHIVES] \
            == {target: {str(config.build_output / (target + '.a'))}
                for target in targets}

    def test_for_library(self, tmp_path: Path, fake_process: FakeProcess):
        """
        As used when building an object archive or archiving before linking
        a shared library.
        """
        config = BuildConfig('proj', ToolBox(),
                             fab_workspace=tmp_path)
        config.artefact_store.update_dict(
            ArtefactSet.OBJECT_FILES, None, {'util1.o', 'util2.o'})

        command1 = ['ar', 'cr', str(config.build_output / 'mylib.a'),
                    'util1.o', 'util2.o']
        recorder = fake_process.register(command1, stdout="Archiving")
        with warns(UserWarning, match="_metric_send_conn not set, "
                                      "cannot send metrics"):
            archive_objects(config=config,
                            output_fpath=config.build_output / 'mylib.a')
        assert recorder.call_count(command1) == 1

        # ensure the correct artefacts were created
        assert config.artefact_store[ArtefactSet.OBJECT_ARCHIVES] == {
            None: {str(config.build_output / 'mylib.a')}}
