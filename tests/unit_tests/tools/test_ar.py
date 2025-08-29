##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Tests 'ar' archiver tool.
"""
from pathlib import Path

from pyfakefs.fake_filesystem import FakeFilesystem
from pytest import mark

from fab.tools import Category, Ar

from tests.conftest import ExtendedRecorder


def test_constructor() -> None:
    """
    Tests default constructor.
    """
    ar = Ar()
    assert ar.category == Category.AR
    assert ar.name == "ar"
    assert ar.exec_name == "ar"
    assert ar.get_flags() == []


@mark.parametrize('available', [True, False])
def test_is_available(available: bool, fs: FakeFilesystem) -> None:
    """
    Tests availability functionality.
    """
    if available:
        fs.create_file('/bin/ar', create_missing_dirs=True, st_mode=0o755)
    else:
        fs.create_dir('/bin')
    ar = Ar()
    assert ar.is_available is available


def test_ar_create(subproc_record: ExtendedRecorder) -> None:
    """
    Tests creation of a new archive file.
    """
    ar = Ar()
    ar.create(Path("out.a"), [Path("a.o"), "b.o"])
    assert subproc_record.invocations() \
           == [['ar', 'cr', 'out.a', 'a.o', 'b.o']]
    assert subproc_record.extras() == [{'cwd': None,
                                        'env': None,
                                        'stderr': None,
                                        'stdout': None}]
