##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Tests Shell tools.
"""
from fab.tools.category import Category
from fab.tools.shell import Shell

from tests.conftest import ExtendedRecorder

from pytest_subprocess.fake_process import FakeProcess


def test_constructor() -> None:
    """
    Tests construction from an argument list.
    """
    bash = Shell("nish")
    assert bash.category == Category.SHELL
    assert bash.name == "nish"
    assert bash.exec_name == "nish"


def test_check_available(fake_process: FakeProcess) -> None:
    """
    Tests availability functionality.
    """
    def not_found(process):
        process.returncode = 1
        raise FileNotFoundError("Shell executable missing")

    fake_process.register(["nish", "-c", "echo hello"])
    fake_process.register(["nish", "-c", "echo hello"], callback=not_found)

    shell = Shell("nish")
    assert shell.check_available()

    # Test behaviour if a runtime error happens:
    assert not shell.check_available()

    assert [call for call in fake_process.calls] == [
        ['nish', '-c', 'echo hello'],
        ['nish', '-c', 'echo hello']
    ]


def test_exec_single_arg(subproc_record: ExtendedRecorder) -> None:
    """
    Tests shell script without additional parameters.
    """
    ksh = Shell("ksh")
    ksh.exec("echo")
    assert subproc_record.invocations() == [
        ['ksh', '-c', 'echo']
    ]


def test_shell_exec_multiple_args(subproc_record: ExtendedRecorder) -> None:
    """
    Tests shell script with parameters.
    """
    csh = Shell("csh")
    csh.exec(["some", "shell", "function"])
    assert subproc_record.invocations() == [
        ['csh', '-c', 'some', 'shell', 'function']
    ]
