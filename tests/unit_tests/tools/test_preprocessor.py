##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Tests source preprocessor tools.
"""
from logging import Logger
from pathlib import Path

from pyfakefs.fake_filesystem import FakeFilesystem

from tests.conftest import ExtendedRecorder

from pytest import mark
from pytest_subprocess.fake_process import FakeProcess

from tests.conftest import call_list

from fab.tools.category import Category
from fab.tools.preprocessor import Cpp, CppFortran, Fpp, Preprocessor


def test_constructor() -> None:
    """
    Tests construction from argument list.
    """
    tool = Preprocessor("some preproc", "spp", Category.FORTRAN_PREPROCESSOR)
    assert str(tool) == "Preprocessor - some preproc: spp"
    assert tool.exec_name == "spp"
    assert tool.name == "some preproc"
    assert tool.category == Category.FORTRAN_PREPROCESSOR
    assert isinstance(tool.logger, Logger)


@mark.parametrize('available', [True, False])
def test_fpp_is_available(available: bool, fs: FakeFilesystem) -> None:
    """
    Tests availability check for Intel's "fpp" tool.
    """
    if available:
        fs.create_file('/bin/fpp', create_missing_dirs=True, st_mode=0o755)
    else:
        fs.create_dir('/bin')
    fpp = Fpp()
    assert fpp.is_available is available


class TestCpp:
    def test_cpp(self, subproc_record: ExtendedRecorder) -> None:
        """
        Tests the CPP tool.
        """
        cpp = Cpp()
        cpp.run("--version")
        assert subproc_record.invocations() == [['cpp', '--version']]

    @mark.parametrize('available', [True, False])
    def test_is_available(self, available: bool, fs: FakeFilesystem) -> None:
        if available:
            fs.create_file('/bin/cpp', create_missing_dirs=True, st_mode=0o755)
        else:
            fs.create_dir('/bin')
        cpp = Cpp()
        assert cpp.is_available is available


class TestCppTraditional:
    @mark.parametrize('available', [True, False])
    def test_is_available(self, available: bool, fs: FakeFilesystem) -> None:
        """
        Tests CPP in "traditional" mode.
        """
        if available:
            fs.create_file('/bin/cpp', create_missing_dirs=True, st_mode=0o755)
        else:
            fs.create_dir('/bin')
        cppf = CppFortran()
        assert cppf.is_available is available

    def test_preprocess(self, subproc_record: ExtendedRecorder) -> None:
        cppf = CppFortran()
        cppf.preprocess(Path("a.in"), Path("a.out"))
        cppf.preprocess(Path("a.in"), Path("a.out"), ["-DDO_SOMETHING"])
        assert subproc_record.invocations() == [
            ["cpp", "-traditional-cpp", "-P", "a.in", "a.out"],
            ["cpp", "-traditional-cpp", "-P", "-DDO_SOMETHING", "a.in", "a.out"]
        ]
