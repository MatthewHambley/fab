##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Tests source preprocessors.
"""
from collections import deque
from pathlib import Path

from pytest_subprocess.fake_process import FakeProcess, ProcessRecorder

from fab.category import Category
from fab.tools.preprocessor import Cpp, CppFortran, Fpp, Preprocessor


def test_preprocessor_constructor():
    '''Test the constructor.'''
    tool = Preprocessor("cpp-fortran", "cpp", Category.FORTRAN_PREPROCESSOR)
    assert str(tool) == "Preprocessor - cpp-fortran: cpp"
    assert tool.executable == Path("cpp")
    assert tool.name == "cpp-fortran"
    assert tool.category == Category.FORTRAN_PREPROCESSOR


def test_preprocessor_fpp_is_not_available(fake_process: FakeProcess):
    """
    Tests availability check.
    """
    fpp = Fpp()
    fake_process.register(['fpp', '--version'], returncode=1)
    assert fpp.is_available is False
    assert fake_process.calls == deque([['fpp', '--version']])


def test_fpp_is_available(mock_process: ProcessRecorder):
    test_unit = Fpp()
    assert test_unit.is_available is True
    assert [call.args for call in mock_process.calls] \
           == [['fpp', '--version']]


def test_preprocessor_cpp(mock_process: ProcessRecorder):
    """
    Tests the C preprocessor.
    """
    cpp = Cpp()
    cpp.run("--version")
    assert [call.args for call in mock_process.calls] \
           == [['cpp', '--version']]


def test_cpp_is_not_available(fake_process: FakeProcess):
    test_unit = Cpp()
    fake_process.register(['cpp', '--version'], returncode=1)
    assert test_unit.is_available is False


def test_preprocessor_cppfortran(mock_process: ProcessRecorder):
    """
    Tests using a C preprocessor for Fortran.
    """
    cppf = CppFortran()
    assert cppf.is_available  # Todo: Maybe make the whole test conditional.
    cppf.preprocess(Path("a.in"), Path("a.out"))
    assert [call.args for call in mock_process.calls] \
        == [
            ["cpp", "-traditional-cpp", "-P", '--version'],
            ['cpp', '-traditional-cpp', '-P', 'a.in', 'a.out']
           ]


def test_preprocessor_cppfortran_with_macros(mock_process: ProcessRecorder):
    """
    Tests using a C preprocessor for Fortran with macro definitions.
    """
    cppf = CppFortran()
    assert cppf.is_available  # Todo: Maybe make the whole test conditional.
    cppf.preprocess(Path("a.in"), Path("a.out"), ["-DDO_SOMETHING"])
    assert [call.args for call in mock_process.calls] \
        == [
            ["cpp", "-traditional-cpp", "-P", '--version'],
            ["cpp", "-traditional-cpp", "-P", "-DDO_SOMETHING", "a.in", "a.out"]
           ]
