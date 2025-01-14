##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################

'''Tests the ar implementation.
'''
from collections import deque
from pathlib import Path

from pytest_subprocess.fake_process import FakeProcess, ProcessRecorder

from fab.category import Category
from fab.tools.ar import Ar


def test_ar_constructor():
    '''Test the ar constructor.'''
    ar = Ar()
    assert ar.category == Category.AR
    assert ar.name == "ar"
    assert ar.executable == Path("ar")
    assert ar.flags == []


def test_ar_available(mock_process: ProcessRecorder):
    '''Tests the is_available functionality.'''
    ar = Ar()
    assert ar.is_available is True
    assert [call.args for call in mock_process.calls] \
           == [['ar', '--version']]


def test_ar_not_available(fake_process: FakeProcess):
    """
    Tests failing availability check.
    """
    def failure(process):
        process.returncode = 1
        raise FileNotFoundError("Ar tool not found.")

    test_unit = Ar()
    fake_process.register(['ar', '--version'], callback=failure)
    assert test_unit.is_available is False
    assert fake_process.calls == deque([['ar', '--version']])


def test_ar_create(mock_process: ProcessRecorder):
    '''Test creating an archive.'''
    ar = Ar()
    ar.create(Path("out.a"), [Path("a.o"), "b.o"])
    assert [call.args for call in mock_process.calls] \
        == [['ar', 'cr', 'out.a', 'a.o', 'b.o']]
