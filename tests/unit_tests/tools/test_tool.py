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

from pytest import raises
from pytest_subprocess.fake_process import FakeProcess

from tests.conftest import ExtendedRecorder, call_list, not_found_callback

from fab.tools.category import Category
from fab.tools.tool import Tool


def test_constructor() -> None:
    """
    Tests comstruction from argument list.
    """
    tool = Tool("gnu", "gfortran", Category.FORTRAN_COMPILER)
    assert str(tool) == "Tool - gnu: gfortran"
    assert tool.exec_name == "gfortran"
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
    assert mytool.exec_name == "/bin/mytool"
    assert mytool.category == Category.MISC

    # Check that if we specify no category, we get the default:
    misc = Tool("misc", "misc")
    assert misc.exec_name == "misc"
    assert misc.name == "misc"
    assert misc.category == Category.MISC


def test_chance_exec_name() -> None:
    """
    Tests changing the executable.

    ToDo: Shouldn't the executable be inviolable?
    """
    tool = Tool("gfortran", "gfortran", Category.FORTRAN_COMPILER)
    assert tool.exec_name == "gfortran"
    tool.change_exec_name("start_me_instead")
    assert tool.exec_name == "start_me_instead"


def test_is_available(fake_process: FakeProcess) -> None:
    """
    Tests tool availability checking.
    """
    fake_process.register(['gfortran', '--version'], stdout="1.2.3")
    tool = Tool("gfortran", "gfortran", Category.FORTRAN_COMPILER)
    assert tool.is_available


def test_availability_argument() -> None:
    """
    Tests setting the argument used to detect availability.
    """
    tool = Tool("ftool", "ftool", Category.FORTRAN_COMPILER,
                availability_option="am_i_here")
    assert tool.availability_option == "am_i_here"


def test_run_missing(fake_process: FakeProcess) -> None:
    """
    Tests attempting to run an missing tool.
    """
    fake_process.register(['stool', '--ops'], callback=not_found_callback)
    tool = Tool("some tool", "stool", Category.MISC)
    with raises(RuntimeError) as err:
        tool.run("--ops")
    assert str(err.value).startswith(
        "Unable to execute command: ['stool', '--ops']"
    )


def test_arguments():
    """
    Tests tool arguments.
    """
    tool = Tool("some tool", "stool", Category.MISC)
    assert tool.flags == []
    tool.add_flags("-a")
    assert tool.flags == ["-a"]
    tool.add_flags(["-b", "-c"])
    assert tool.flags == ["-a", "-b", "-c"]


class TestToolRun:
    """
    Tests tool run method.
    """
    def test_no_error_no_args(self, fake_process: FakeProcess) -> None:
        """
        Tests run with no aruments.
        """
        fake_process.register(['stool'], stdout="123")
        fake_process.register(['stool'], stdout="123")
        tool = Tool("some tool", "stool", Category.MISC)
        assert tool.run(capture_output=True) == "123"
        assert tool.run(capture_output=False) == ""
        assert call_list(fake_process) == [['stool'], ['stool']]

    def test_run_with_single_args(self,
                                  subproc_record: ExtendedRecorder) -> None:
        """
        Tets run with single argument.
        """
        tool = Tool("some tool", "tool", Category.MISC)
        tool.run("a")
        assert subproc_record.invocations() == [['tool', 'a']]

    def test_run_with_multiple_args(self,
                                    subproc_record: ExtendedRecorder) -> None:
        """
        Tests run with multiple arguments.
        """
        tool = Tool("some tool", "tool", Category.MISC)
        tool.run(["a", "b"])
        assert subproc_record.invocations() == [['tool', 'a', 'b']]

    def test_error(self, fake_process: FakeProcess) -> None:
        """
        Tests running a failing tool.
        """
        fake_process.register(['tool'], returncode=1)
        tool = Tool("some tool", "tool", Category.MISC)
        with raises(RuntimeError) as err:
            tool.run()
        assert str(err.value).startswith("Command failed with return code 1")
        assert call_list(fake_process) == [['tool']]

    def test_error_file_not_found(self, fake_process: FakeProcess) -> None:
        """
        Tests running a missing tool.
        """
        fake_process.register(['tool'], callback=not_found_callback)
        tool = Tool('some tool', 'tool', Category.MISC)
        with raises(RuntimeError) as err:
            tool.run()
        assert str(err.value) == "Unable to execute command: ['tool']"
        assert call_list(fake_process) == [['tool']]
