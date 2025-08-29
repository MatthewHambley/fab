##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Tests RSync file tree synchronisation tool.
"""
from pathlib import Path

from pyfakefs.fake_filesystem import FakeFilesystem
from pytest import mark
from pytest_subprocess.fake_process import FakeProcess

from fab.tools.category import Category
from fab.tools.rsync import Rsync

from tests.conftest import call_list, not_found_callback


def test_constructor():
    """
    Tests default constructor
    """
    rsync = Rsync()
    assert rsync.category == Category.RSYNC
    assert rsync.name == "rsync"
    assert rsync.exec_name == "rsync"
    assert rsync.get_flags() == []


@mark.parametrize('available', [True, False])
def test_check_available(available: bool, fs: FakeFilesystem) -> None:
    """
    Tests availability checking functionality.
    """
    if available:
        fs.create_file('/bin/rsync', create_missing_dirs=True, st_mode=0o755)
    else:
        fs.create_dir('/bin')

    rsync = Rsync()
    assert rsync.is_available is available


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
    rsync.execute(src=Path("/src/"), dst=Path("/dst"))

    # Test 2: src without /
    rsync.execute(src=Path("/src"), dst=Path("/dst"))

    assert call_list(fake_process) == [
        with_command, without_command
    ]
