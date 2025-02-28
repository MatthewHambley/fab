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
from fab.tools import Category, ToolBox


class TestArchiveObjects:
    """
    Tests the archive step.
    """
    def test_for_exes(self, stub_tool_box: ToolBox,
                      fs, fake_process: FakeProcess) -> None:
        """
        Tests prior to linking an executable.
        """
        version_command = ['ar', '--version']
        fake_process.register(version_command)
        command1 = ['ar', 'cr', '/fab/proj/build_output/prog1.a', 'prog1.o', 'util.o']
        fake_process.register(command1)
        command2 = ['ar', 'cr', '/fab/proj/build_output/prog2.a', 'prog2.o', 'util.o']
        fake_process.register(command2)

        targets = ['prog1', 'prog2']

        config = BuildConfig('proj', stub_tool_box, fab_workspace=Path('/fab'))
        for target in targets:
            config.artefact_store.update_dict(
                ArtefactSet.OBJECT_FILES, target,
                {f'{target}.o', 'util.o'}
            )

        with warns(UserWarning,
                   match="_metric_send_conn not set, cannot send metrics"):
            archive_objects(config=config)
        assert [call for call in fake_process.calls] \
               == [version_command, command1, command2]

        # ensure the correct artefacts were created
        assert config.artefact_store[ArtefactSet.OBJECT_ARCHIVES] == {
            target: {str(config.build_output / f'{target}.a')}
            for target in targets
        }

    def test_for_library(self, stub_tool_box: ToolBox,
                         fs, fake_process: FakeProcess) -> None:
        """
        Tests creating an object archiving or prior to a shared library.
        """
        fake_process.register(['ar', '--version'])
        command = ['ar', 'cr', '/fab/proj/build_output/mylib.a',
                   'util1.o', 'util2.o']
        record = fake_process.register(command)

        config = BuildConfig('proj', stub_tool_box, fab_workspace=Path('/fab'))
        config.artefact_store.update_dict(
            ArtefactSet.OBJECT_FILES, None, {'util1.o', 'util2.o'})

        with warns(UserWarning,
                   match="_metric_send_conn not set, cannot send metrics"):
            archive_objects(config=config,
                            output_fpath=config.build_output / 'mylib.a')
        assert [call.args for call in record.calls] == [command]
        assert config.artefact_store[ArtefactSet.OBJECT_ARCHIVES] == {
            None: {str(config.build_output / 'mylib.a')}}

    def test_incorrect_tool(self, stub_tool_box: ToolBox) -> None:
        """
        Tests wrong tool.

        ToDo: Can this ever happen and monkeying with internal state.
        """
        config = BuildConfig('proj', stub_tool_box)
        cc = stub_tool_box.get_tool(Category.C_COMPILER,
                                    config.mpi,
                                    config.openmp)
        # And set its category to be AR
        cc._category = Category.AR
        # Now add this 'ar' tool to the tool box
        stub_tool_box.add_tool(cc)

        with raises(RuntimeError) as err:
            archive_objects(config=config,
                            output_fpath=config.build_output / 'mylib.a')
        assert str(err.value) == \
               "Unexpected tool 'some C compiler' of type '<class " \
               "'fab.tools.compiler.CCompiler'>' instead of Ar"
