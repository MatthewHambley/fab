##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################

'''Tests the rsync implementation.
'''
from collections import deque
from pathlib import Path

from pytest_subprocess.fake_popen import FakePopen
from pytest_subprocess.fake_process import FakeProcess

from fab.category import Category
from fab.tools.rsync import Rsync


def test_ar_constructor():
    '''Test the rsync constructor.'''
    rsync = Rsync()
    assert rsync.category == Category.RSYNC
    assert rsync.name == "rsync"
    assert rsync.executable == Path("rsync")
    assert rsync.flags == []


def test_rsync_is_available(mock_process):
    '''Tests the is_available functionality.'''
    rsync = Rsync()
    assert rsync.is_available is True
    assert mock_process.calls == deque([['rsync', '--version']])


def test_rsync_is_not_avaiolable(fake_process: FakeProcess):
    """
    Tests that missing executable is correctly reported.
    """
    def missing_exe(process: FakePopen):
        process.returncode = 1
        raise FileNotFoundError()

    test_unit = Rsync()
    fake_process.register(['rsync', '--version'], callback=missing_exe)
    assert test_unit.is_available is False


def test_rsync_create_source_directory(mock_process):
    """
    Tests rsync with source ending with '/'.
    """
    rsync = Rsync()
    rsync.execute(src="/src/", dst="/dst")
    assert mock_process.calls == deque([['rsync', '--times', '--links', '--stats', '-ru', '/src/', '/dst']])


def test_rsync_create_source_file(mock_process):
    """
    Tests rsync when source does not end with '/'.
    """
    test_unit = Rsync()
    test_unit.execute(src="/src", dst="/dst")
    assert mock_process.calls == deque([['rsync', '--times', '--links', '--stats', '-ru', '/src/', '/dst']])
