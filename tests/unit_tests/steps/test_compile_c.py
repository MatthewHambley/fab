# ##############################################################################
#  (c) Crown copyright Met Office. All rights reserved.
#  For further details please refer to the file COPYRIGHT
#  which you should have received as part of this distribution
# ##############################################################################
"""
Tests the C compiler step.
"""
import os
from pathlib import Path
from unittest import mock
from typing import Tuple, Optional, Union, List, Dict

from pytest import fixture, raises, warns
from pytest_subprocess.fake_process import FakeProcess

from fab.artefacts import ArtefactSet
from fab.build_config import AddFlags, BuildConfig
from fab.parse.c import AnalysedC
from fab.steps.compile_c import get_obj_combo_hash, _compile_file, compile_c
from fab.tool_box import ToolBox
from fab.tools import Category, Flags, PathLike
from fab.tools.compiler import CCompiler


class CStub(CCompiler):
    def __init__(self, name='stub c compiler', version="1.2.3", run_fail=False):
        super().__init__(name, 'stubc', 'test')
        self.__version = tuple(version.split('.'))
        self.__run_fail = run_fail

    def get_version(self) -> Tuple[int, ...]:
        return self.__version

    def compile_file(self, input_file: Path,
                     output_file: Path,
                     openmp: bool,
                     add_flags: Union[None, List[str]] = None) -> Optional[str]:
        if self.__run_fail:
            raise RuntimeError("Failed to compile C file")
        else:
            return "line 1\n line 2\n"


@fixture(scope="function")
def environment(tmp_path: Path) -> Tuple[BuildConfig, AnalysedC]:
    """
    Provides a test environment.
    """
    tool_box = ToolBox()
    tool_box.add_tool(CStub())
    config = BuildConfig('proj', tool_box, multiprocessing=False,
                         fab_workspace=tmp_path)

    analysed_file = AnalysedC(fpath=Path(f'{config.source_root}/foo.c'), file_hash=0)
    config.artefact_store[ArtefactSet.BUILD_TREES] = \
        {None: {analysed_file.fpath: analysed_file}}
    return config, analysed_file


# This is more of an integration test than a unit test
class TestCompileC:
    """
    Tests the C compilation step.
    """
    def test_vanilla(self, environment, fake_process: FakeProcess, monkeypatch):
        """
        Ensures the command line is formed correctly.
        """
        config, _ = environment
        compiler = CStub()

        monkeypatch.setenv('CFLAGS', '-Denv_flag')

        with warns(UserWarning,
                   match="_metric_send_conn not set, cannot send metrics"):
            compile_c(config=config,
                      path_flags=[AddFlags(match='$source/*',
                                           flags=['-I', 'foo/include', '-Dhello'])])

        # ensure it created the correct artefact collection
        assert config.artefact_store[ArtefactSet.OBJECT_FILES] == {
            None: {config.prebuild_folder / f'foo.1723febd6.o', }
        }

    def test_exception_handling(self, tmp_path: Path):
        '''Test exception handling if the compiler fails.'''
        tool_box = ToolBox()
        tool_box.add_tool(CStub(run_fail=True))
        config = BuildConfig('proj', tool_box, multiprocessing=False,
                             fab_workspace=tmp_path)
        analysed_file = AnalysedC(fpath=Path(f'{config.source_root}/foo.c'),
                                  file_hash=1234)
        config.artefact_store[ArtefactSet.BUILD_TREES] = \
            {None: {analysed_file.fpath: analysed_file}}
        with raises(RuntimeError):
            compile_c(config=config)


class TestGetObjComboHash:
    '''Tests the object combo hash functionality.'''

    @fixture
    def flags(self):
        '''Returns the flag for these tests.'''
        return Flags(['-Denv_flag', '-I', 'foo/include', '-Dhello'])

    def test_vanilla(self, environment, flags, fake_process: FakeProcess):
        '''Test that we get the expected hashes in this test setup.'''
        command = ['stubc', '--version']
        recorder = fake_process.register(command, stdout='1.2.3')
        config, analysed_file = environment
        compiler = CStub()
        result = get_obj_combo_hash(compiler, analysed_file, flags)
        assert result == 6211759062

    def test_change_file(self, environment, flags):
        '''Check that a change in the file (simulated by changing
        the hash) changes the obj combo hash.'''
        config, analysed_file = environment
        compiler = CStub()
        result1 = get_obj_combo_hash(compiler, analysed_file, flags)
        analysed_file._file_hash += 1  # Todo: Clearly this is wrong.
        result2 = get_obj_combo_hash(compiler, analysed_file, flags)
        assert result1 != result2

    def test_change_flags(self, environment, flags, fake_process: FakeProcess):
        '''Test that changing the flags changes the hash.'''
        config, analysed_file = environment
        compiler = CStub()
        flags1 = Flags(['-Dfoo', '-Dboo=4'])
        result1 = get_obj_combo_hash(compiler, analysed_file, flags1)
        flags2 = Flags(['-Dfoo', '-Dboo=3'])
        result2 = get_obj_combo_hash(compiler, analysed_file, flags2)
        assert result1 != result2

    def test_change_compiler(self, environment, flags):
        """
        Test that a change in the name of the compiler changes the hash.
        """
        config, analysed_file = environment
        compiler1 = CStub(name="first compiler")
        result1 = get_obj_combo_hash(compiler1, analysed_file, flags)
        compiler2 = CStub(name="second compiler")
        result2 = get_obj_combo_hash(compiler2, analysed_file, flags)
        assert result1 != result2

    def test_change_compiler_version(self, environment, flags):
        '''Test that a change in the version number of the compiler
        changes the hash.'''
        config, analysed_file = environment
        compiler1 = CStub(version="4.5.6")
        result1 = get_obj_combo_hash(compiler1, analysed_file, flags)
        compiler2 = CStub(version="7.8.9")
        result2 = get_obj_combo_hash(compiler2, analysed_file, flags)
        assert result1 != result2
