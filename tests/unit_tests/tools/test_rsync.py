##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Tests RSync file tree synchronisation tool.
"""
from fab.tools.category import Category
from fab.tools.rsync import Rsync

from pytest_subprocess.fake_process import FakeProcess


def test_constructor():
    """
    Tests default constructor
    """
    rsync = Rsync()
    assert rsync.category == Category.RSYNC
    assert rsync.name == "rsync"
    assert rsync.exec_name == "rsync"
    assert rsync.flags == []


def test_check_available(fake_process: FakeProcess) -> None:
    """
    Tests availability checking functionality.
    """
    def not_found(process):
        process.returncode = 1
        raise FileNotFoundError("RSync executable missing")

    fake_process.register(['rsync', '--version'], stdout='1.2.3')
    fake_process.register(['rsync', '--version'], callback=not_found)

    rsync = Rsync()
    assert rsync.check_available()

    # Test behaviour if a runtime error happens:
    assert not rsync.check_available()

    assert [call for call in fake_process.calls] == [
        ['rsync', '--version'],
        ['rsync', '--version']
    ]


def test_rsync_create(fake_process: FakeProcess) -> None:
    """
    Tests performing a sync. Ensure source always ends with a '/'.
    """
    with_command = ['rsync', '--times', '--links', '--stats', '-ru', '/src/', '/dst']
    fake_process.register(with_command)
    without_command = ['rsync', '--times', '--links', '--stats', '-ru', '/src/', '/dst']
    fake_process.register(without_command)

    rsync = Rsync()

    # Test 1: src with /
    rsync.execute(src="/src/", dst="/dst")

    # Test 2: src without /
    rsync.execute(src="/src", dst="/dst")

    assert [call for call in fake_process.calls] == [
        with_command, without_command
    ]