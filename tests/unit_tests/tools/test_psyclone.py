##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Tests calling the PSyclone tool.
"""
from collections import deque
from pathlib import Path
from unittest.mock import Mock

from pytest import fixture

from fab.category import Category
from fab.tool_box import ToolBox
from fab.tools.psyclone import Psyclone


def test_psyclone_constructor():
    """
    Tests the default constructor.
    """
    psyclone = Psyclone()
    assert psyclone.category == Category.PSYCLONE
    assert psyclone.name == "psyclone"
    assert psyclone.executable == Path("psyclone")
    assert psyclone.flags == []
    assert psyclone._api is None

    psyclone = Psyclone(api="gocean1.0")
    assert psyclone.category == Category.PSYCLONE
    assert psyclone.name == "psyclone"
    assert psyclone.executable == Path("psyclone")
    assert psyclone.flags == []
    assert psyclone._api == "gocean1.0"


def test_psyclone_is_available(mock_process):
    """
    Tests tool availability.
    """
    psyclone = Psyclone()
    assert psyclone.is_available is True
    assert mock_process.calls == deque([['psyclone', '--version']])


def test_psyclone_is_not_available(fake_process):
    """
    Tests tool invailability.
    """
    test_unit = Psyclone()
    fake_process.register(['psyclone', '--version'], returncode=1)
    assert test_unit.is_available is False
    assert fake_process.calls == deque([['psyclone', '--version']])


def _dummy_transform(algorithm_file: Path, configuration):
    return Path('dummy_script')


def test_psyclone_process_with_api(mock_process):
    """
    Tests invoking PSyclone with an API specified.
    """
    psyclone = Psyclone()
    psyclone.process(config=Mock(),
                     api='lfric',
                     x90_file="x90_file",
                     psy_file="psy_file",
                     alg_file="alg_file",
                     transformation_script=_dummy_transform,
                     kernel_roots=["root1", "root2"],
                     additional_parameters=["-c", "psyclone.cfg"])
    assert mock_process.calls == deque(
        [
            ['psyclone', '-api', 'lfric', '-l', 'all', '-opsy', 'psy_file',
             '-oalg', 'alg_file', '-s', 'dummy_script', '-c', 'psyclone.cfg',
             '-d', 'root1', '-d', 'root2', 'x90_file']
        ]
    )


def test_psyclone_process_without_api(mock_process):
    """
    Tests invoking PSyclone with no API specified.
    """
    test_unit = Psyclone()
    test_unit.process(config=Mock(),
                      x90_file="x90_file",
                      psy_file="psy_file",
                      alg_file="alg_file",
                      transformation_script=_dummy_transform,
                      kernel_roots=["root1", "root2"],
                      additional_parameters=["-c", "psyclone.cfg"])
    assert mock_process.calls == deque(
        [
            ['psyclone', '-l', 'all', '-opsy', 'psy_file', '-oalg', 'alg_file',
             '-s', 'dummy_script', '-c', 'psyclone.cfg', '-d', 'root1',
             '-d', 'root2', 'x90_file']
        ]
    )


def test_psyclone_process_default_api(mock_process):
    """
    Tests invoking PSyclone with no API specify a default.
    """
    test_unit = Psyclone(api="gocean1.0")
    test_unit.process(config=Mock(),
                      x90_file="x90_file",
                      psy_file="psy_file",
                       alg_file="alg_file",
                      transformation_script=_dummy_transform,
                      kernel_roots=["root1", "root2"],
                      additional_parameters=["-c", "psyclone.cfg"])
    assert mock_process.calls == deque(
        [
            ['psyclone', '-api', 'gocean1.0', '-l', 'all', '-opsy', 'psy_file',
             '-oalg', 'alg_file', '-s', 'script_called', '-c',
              'psyclone.cfg', '-d', 'root1', '-d', 'root2', 'x90_file']
        ]
    )


def test_psyclone_process_default_api(mock_process):
    """
    Tests invoking PSyclone with both specified and default API.
    """
    test_unit = Psyclone(api="gocean1.0")
    test_unit.process(config=Mock(),
                      x90_file="x90_file",
                      psy_file="psy_file",
                      alg_file="alg_file",
                      api='lfric',
                      transformation_script=_dummy_transform,
                      kernel_roots=["root1", "root2"],
                      additional_parameters=["-c", "psyclone.cfg"])
    assert mock_process.calls == deque(
        [
            ['psyclone', '-api', 'lfric', '-l', 'all', '-opsy', 'psy_file',
             '-oalg', 'alg_file', '-s', 'dummy_script', '-c', 'psyclone.cfg',
             '-d', 'root1', '-d', 'root2', 'x90_file']
        ]
    )
