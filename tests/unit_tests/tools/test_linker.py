##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Object linker tests.
"""
from collections import deque
from pathlib import Path

from pytest import raises
from pytest_subprocess.fake_process import FakeProcess, ProcessRecorder

from fab.category import Category
from fab.tools.linker import Linker


def test_constructor_exe():
    """
    Tests construction with a linker executable.
    """
    linker = Linker(name="my_linker", executable="my_linker.exe",
                    suite="suite")
    assert linker.category == Category.LINKER
    assert linker.name == "my_linker"
    assert linker.executable == Path("my_linker.exe")
    assert linker.suite == "suite"
    assert linker.flags == []


def test_constructor_c_compiler_named(stub_c_compiler):
    """
    Tests construction with a C compiler and a name.
    """
    linker = Linker(name="my_linker", compiler=stub_c_compiler)
    assert linker.category == Category.LINKER
    assert linker.name == "my_linker"
    assert linker.executable == stub_c_compiler.executable
    assert linker.suite == stub_c_compiler.suite
    assert linker.flags == []


def test_constructor_c_compiler(stub_c_compiler):
    linker = Linker(compiler=stub_c_compiler)
    assert linker.category == Category.LINKER
    assert linker.name == stub_c_compiler.name
    assert linker.executable == stub_c_compiler.executable
    assert linker.suite == stub_c_compiler.suite
    assert linker.flags == []


def test_constructor_fortran_compiler(mock_fortran_compiler):
    linker = Linker(compiler=mock_fortran_compiler)
    assert linker.category == Category.LINKER
    assert linker.name == mock_fortran_compiler.name
    assert linker.executable == mock_fortran_compiler.executable
    assert linker.flags == []


def test_costructor_missing():
    with raises(RuntimeError) as err:
        linker = Linker(name="no-exec-given")
    assert str(err.value) == \
           "Either specify name, exec name, and suite or a compiler when " \
            "creating Linker."


def test_is_available_compiler(stub_c_compiler,
                               fake_process: FakeProcess):
    """
    Tests availability against a compiler.
    """
    recorder = fake_process.register(['stubc', '--version'],
                                     stdout='1.2.3')
    linker = Linker(compiler=stub_c_compiler)
    assert linker.is_available is True


def test_is_available_executable(mock_process: ProcessRecorder):
    """
    Tests availability against executable.
    """
    linker = Linker("ld", Path("ld"), suite="gnu")
    assert linker.is_available is True
    assert [call.args for call in mock_process.calls] \
           == [['ld', '--version']]


def test_is_not_available(fake_process: FakeProcess):
    """
    Test availability when executable not found.
    """
    test_unit = Linker('ld', Path('ld'), 'foo')
    fake_process.register(['ld', '--version'], returncode=1)
    assert test_unit.is_available is False
    assert fake_process.calls == deque([['ld', '--version']])


def test_linker_c(stub_c_compiler, mock_process: ProcessRecorder):
    '''Test the link command line when no additional libraries are
    specified.'''
    linker = Linker(compiler=stub_c_compiler)
    linker.link([Path("a.o")], Path("a.out"), openmp=False)
    assert [call.args for call in mock_process.calls] \
        == [["stubc", 'a.o', '-o', 'a.out']]


def test_linker_c_with_libraries(stub_c_compiler,
                                 mock_process: ProcessRecorder):
    '''Test the link command line when additional libraries are specified.'''
    linker = Linker(compiler=stub_c_compiler)
    linker.link([Path("a.o")], Path("a.out"), add_libs=["-L", "/tmp"],
                openmp=True)
    assert [call.args for call in mock_process.calls] \
        == [['stubc', '-openmpme', 'a.o', '-L', '/tmp', '-o', 'a.out']]


def test_compiler_linker_add_compiler_flag(stub_c_compiler,
                                           mock_process: ProcessRecorder):
    '''Test that a flag added to the compiler will be automatically
    added to the link line (even if the flags are modified after
    creating the linker ... in case that the user specifies additional
    flags after creating the linker).'''

    linker = Linker(compiler=stub_c_compiler)
    stub_c_compiler.flags.append("-my-flag")
    linker.link([Path("a.o")], Path("a.out"), openmp=False)
    assert [call.args for call in mock_process.calls] \
        == [['stubc', '-my-flag', 'a.o', '-o', 'a.out']]


def test_linker_add_compiler_flag(mock_process: ProcessRecorder):
    """
    Ensure linker works when compiler is not specified.
    """
    linker = Linker("no-compiler", "no-compiler.exe", "suite")
    linker.flags.append("-some-other-flag")
    linker.link([Path("a.o")], Path("a.out"), openmp=False)
    assert [call.args for call in mock_process.calls] \
        == [['no-compiler.exe', '-some-other-flag', 'a.o', '-o', 'a.out']]
