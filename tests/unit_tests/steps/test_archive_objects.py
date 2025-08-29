##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Test for the archive step.
"""
from pathlib import Path

from pyfakefs.fake_filesystem import FakeFilesystem
from pytest import raises, warns
from pytest_subprocess.fake_process import FakeProcess

from tests.conftest import call_list

from fab.artefacts import ArtefactSet
from fab.build_config import BuildConfig
from fab.steps.archive_objects import archive_objects
from fab.tools import Category, ToolRepository


class TestArchiveObjects:
    """
    Test the archive step.
    """
    def test_for_exes(self, stub_tool_box,
                      fake_process: FakeProcess,
                      fs: FakeFilesystem) -> None:
        """
        As used when archiving before linking exes.
        """
        fs.create_file('/bin/ar', create_missing_dirs=True, st_mode=0o755)
        targets = ['prog1', 'prog2']
        commands = []
        for target in targets:
            ar_command = ['ar', 'cr', f'/fab/proj/build_output/{target}.a',
                          f'{target}.o', 'util.o']
            fake_process.register(ar_command)
            commands.append(ar_command)

        config = BuildConfig('proj', stub_tool_box, fab_workspace=Path('/fab'))
        for target in targets:
            config.artefact_store.update_dict(
                ArtefactSet.OBJECT_FILES,
                {f'{target}.o', 'util.o'},
                target
            )

        with warns(UserWarning,
                   match="_metric_send_conn not set, cannot send metrics"):
            archive_objects(config=config)
        assert call_list(fake_process) == commands

        # ensure the correct artefacts were created
        assert config.artefact_store[ArtefactSet.OBJECT_ARCHIVES] == {
            target: {str(config.build_output / f'{target}.a')}
            for target in targets}

    def test_for_library(self, stub_tool_box,
                         fake_process: FakeProcess,
                         fs: FakeFilesystem) -> None:
        """
        As used when building an object archive or archiving before linking
        a shared library.
        """
        # Make sure that ar has not already been tested
        # (in which case the --version call will not be executed)
        fs.create_file('/bin/ar', create_missing_dirs=True, st_mode=0o755)
        ar = ToolRepository().get_tool(Category.AR, "ar")
        ar._is_available = None

        ar_command = ['ar', 'cr', '/fab/proj/build_output/mylib.a',
                      'util1.o', 'util2.o']
        fake_process.register(ar_command)

        config = BuildConfig('proj', stub_tool_box, fab_workspace=Path('/fab'),
                             multiprocessing=False)
        config.artefact_store.update_dict(
            ArtefactSet.OBJECT_FILES, {'util1.o', 'util2.o'}, None
        )

        with warns(UserWarning,
                   match="_metric_send_conn not set, cannot send metrics"):
            archive_objects(config=config,
                            output_fpath=config.build_output / 'mylib.a')

        assert call_list(fake_process) == [ar_command]

        # ensure the correct artefacts were created
        assert config.artefact_store[ArtefactSet.OBJECT_ARCHIVES] == {
            None: {str(config.build_output / 'mylib.a')}}

    def test_incorrect_tool(self, stub_tool_box, monkeypatch):
        """
        Test that an incorrect archive tool is detected.
        """
        config = BuildConfig('proj', stub_tool_box)
        cc = stub_tool_box.get_tool(Category.C_COMPILER, config.mpi,
                                    config.openmp)
        # And set its category to be AR. Use monkeypatch
        # (https://docs.pytest.org/en/6.2.x/monkeypatch.html) since the
        # compiler might come from the ToolRepository (in which case it
        # could be shared with other, parallel running tests).
        monkeypatch.setattr(cc, "_category", Category.AR)
        # Now add this 'ar' tool to the tool box
        stub_tool_box.add_tool(cc)

        with raises(RuntimeError) as err:
            archive_objects(config=config,
                            output_fpath=config.build_output / 'mylib.a')
        assert str(err.value) == ("Unexpected tool 'some C compiler' of type "
                                  "'<class 'fab.tools.compiler.CCompiler'>' "
                                  "instead of Ar")
