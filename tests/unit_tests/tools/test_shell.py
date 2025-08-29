##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Tests Shell tools.
"""
from pyfakefs.fake_filesystem import FakeFilesystem
from pytest import mark
from pytest_subprocess.fake_process import FakeProcess

from fab.tools.category import Category
from fab.tools.shell import Shell

from tests.conftest import ExtendedRecorder, call_list, not_found_callback


def test_constructor() -> None:
    """
    Tests construction from an argument list.
    """
    bash = Shell("nish")
    assert bash.category == Category.SHELL
    assert bash.name == "nish"
    assert bash.exec_name == "nish"


@mark.parametrize('available', [True, False])
def test_check_available(available: bool, fs: FakeFilesystem) -> None:
    """
    Tests availability functionality.
    """
    if available:
        fs.create_file('/bin/nish', create_missing_dirs=True, st_mode=0o755)
    else:
        fs.create_dir('/bin')
    shell = Shell("nish")
    assert shell.is_available is available


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
