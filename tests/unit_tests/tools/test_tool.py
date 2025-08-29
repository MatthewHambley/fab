##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Tests tooling base classes.
"""
import logging
from pathlib import Path
from typing import List

from pyfakefs.fake_filesystem import FakeFilesystem
from pytest import mark, raises
from pytest_subprocess.fake_process import FakeProcess

from fab.tools.category import Category
from fab.tools.flags import ProfileFlags
from fab.tools.tool import CompilerSuiteTool, Tool

from tests.conftest import ExtendedRecorder, call_list


def test_constructor() -> None:
    """
    Tests construction from argument list.
    """
    tool = Tool("gnu", "gfortran", Category.FORTRAN_COMPILER)
    assert str(tool) == "Tool - gnu: gfortran"
    assert tool.exec_name == "gfortran"
    assert tool.executable == Path("gfortran")
    assert tool.name == "gnu"
    assert tool.category == Category.FORTRAN_COMPILER
    assert isinstance(tool.logger, logging.Logger)
    assert tool.is_compiler

    linker = Tool("gnu", "gfortran", Category.LINKER)
    assert str(linker) == "Tool - gnu: gfortran"
    assert linker.exec_name == "gfortran"
    assert linker.name == "gnu"
    assert linker.category == Category.LINKER
    assert isinstance(linker.logger, logging.Logger)
    assert not linker.is_compiler

    # Check that a path is accepted
    mytool = Tool("MyTool", Path("/bin/mytool"))
    assert mytool.name == "MyTool"
    # A path should be converted to a string, since this
    # is later passed to the subprocess command
    assert mytool.executable == Path("/bin/mytool")
    assert mytool.category == Category.MISC

    # Check that if we specify no category, we get the default:
    misc = Tool("misc", "misc")
    assert misc.exec_name == "misc"
    assert misc.name == "misc"
    assert misc.category == Category.MISC


def test_tool_set_path() -> None:
    '''Test that we can add an absolute path for a tool,
    e.g. in cases that a known compiler is not in the user's path.
    '''
    gfortran = Tool("gfortran", "gfortran", Category.FORTRAN_COMPILER)
    gfortran.set_full_path(Path("/usr/bin/gfortran1.2.3"))
    # Exec name should now return the full path
    assert gfortran.executable == Path("/usr/bin/gfortran1.2.3")
    # Path the name of the compiler is unchanged
    assert gfortran.name == "gfortran"


@mark.parametrize('available', [True, False])
def test_is_available(available: bool, fs: FakeFilesystem) -> None:
    """
    Checks ability to detect tool availability.
    """
    if available:
        fs.create_file('/bin/test', create_missing_dirs=True, st_mode=0o755)
    else:
        fs.create_dir('/bin')
    tool = Tool('test', 'test', Category.MISC)
    assert tool.is_available is available


def test_tool_flags_no_profile() -> None:
    """
    Test that flags without using a profile work as expected.
    """
    tool = Tool("some tool", "stool", Category.MISC)
    assert tool.get_flags() == []
    tool.add_flags("-a")
    assert tool.get_flags() == ["-a"]
    tool.add_flags(["-b", "-c"])
    assert tool.get_flags() == ["-a", "-b", "-c"]


def test_tool_profiles() -> None:
    '''Test that profiles work as expected. These tests use internal
    implementation details of ProfileFlags, but we need to test that the
    exposed flag-related API works as expected

    '''
    tool = Tool("gfortran", "gfortran", Category.FORTRAN_COMPILER)
    # Make sure by default we get ProfileFlags
    assert isinstance(tool._flags, ProfileFlags)
    assert tool.get_flags() == []

    # Define a profile with no inheritance
    tool.define_profile("mode1")
    assert tool.get_flags("mode1") == []
    tool.add_flags("-flag1", "mode1")
    assert tool.get_flags("mode1") == ["-flag1"]

    # Define a profile with inheritance
    tool.define_profile("mode2", "mode1")
    assert tool.get_flags("mode2") == ["-flag1"]
    tool.add_flags("-flag2", "mode2")
    assert tool.get_flags("mode2") == ["-flag1", "-flag2"]


class TestToolRun:
    """
    Tests tool run method.
    """
    @mark.parametrize('capture', [True, False])
    def test_capture(self, capture: bool,
                     fs: FakeFilesystem,
                     fake_process: FakeProcess) -> None:
        """
        Checks output capture.
        """
        fs.create_file('/bin/stool', create_missing_dirs=True, st_mode=0o755)
        fake_process.register(['stool'], stdout="123")
        tool = Tool("some tool", "stool", Category.MISC)
        if capture:
            assert tool.run(capture_output=True) == "123"
        else:
            assert tool.run(capture_output=False) == ""
        assert call_list(fake_process) == [['stool']]

    @mark.parametrize('args', [
        [],
        ['a'],
        ['b', 'c']
    ])
    def test_run_with_single_args(self,
                                  args: List[str],
                                  fs: FakeFilesystem,
                                  subproc_record: ExtendedRecorder) -> None:
        """
        Checks argument passing.
        """
        fs.create_file('/bin/stool', create_missing_dirs=True, st_mode=0o755)
        tool = Tool("some tool", "stool", Category.MISC)
        tool.run(args)
        expected = ['stool']
        expected.extend(args)
        assert subproc_record.invocations() == [expected]

    def test_error(self, fs: FakeFilesystem, fake_process: FakeProcess) -> None:
        """
        Tests running a failing tool.
        """
        fs.create_file('/bin/tool', create_missing_dirs=True, st_mode=0o755)
        fake_process.register(['tool'], returncode=1, stdout="Beef.")
        tool = Tool("some tool", "tool", Category.MISC)
        with raises(RuntimeError) as err:
            tool.run()
        assert str(err.value) == ("Command failed with return code 1:\n"
                                  "['tool']\nBeef.")
        assert call_list(fake_process) == [['tool']]

    def test_error_tool_not_found(self, fs: FakeFilesystem) -> None:
        """
        Tests running a missing tool.
        """
        fs.create_dir('/bin')
        tool = Tool('some tool', 'tool', Category.MISC)
        with raises(RuntimeError) as err:
            tool.run()
        assert str(err.value) == "Tool 'some tool' is not available to run ['tool']"


def test_suite_tool() -> None:
    '''Test the constructor.'''
    tool = CompilerSuiteTool("gnu", "gfortran", "gnu",
                             Category.FORTRAN_COMPILER)
    assert str(tool) == "CompilerSuiteTool - gnu: gfortran"
    assert tool.exec_name == "gfortran"
    assert tool.name == "gnu"
    assert tool.suite == "gnu"
    assert tool.category == Category.FORTRAN_COMPILER
    assert isinstance(tool.logger, logging.Logger)
