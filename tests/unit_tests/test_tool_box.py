##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################

'''This module tests the TooBox class.
'''
from unittest import mock
import warnings

from pytest import raises, warns
from pytest_subprocess.fake_process import FakeProcess, ProcessRecorder

from fab.category import Category
from fab.tools.compiler import CCompiler, Gfortran
from fab.tool_box import ToolBox
from fab.tool_repository import ToolRepository

from ..conftest import StubC


def test_tool_box_constructor():
    '''Tests the ToolBox constructor.'''
    tb = ToolBox()
    assert isinstance(tb._all_tools, dict)


def test_tool_box_get_tool():
    '''Tests get_tool.'''
    tb = ToolBox()
    # No tool is defined, so the default Fortran compiler must be returned:
    default_compiler = tb.get_tool(Category.FORTRAN_COMPILER,
                                   mpi=False, openmp=False)
    tr = ToolRepository()
    assert default_compiler is tr.get_default(Category.FORTRAN_COMPILER,
                                              mpi=False, openmp=False)
    # Check that dictionary-like access works as expected:
    assert tb[Category.FORTRAN_COMPILER] == default_compiler

    # Now add gfortran as Fortran compiler to the tool box
    tr_gfortran = tr.get_tool(Category.FORTRAN_COMPILER, "gfortran")
    tb.add_tool(tr_gfortran, silent_replace=True)
    gfortran = tb.get_tool(Category.FORTRAN_COMPILER)
    assert gfortran is tr_gfortran


def test_tool_box_add_tool_replacement(fake_process: FakeProcess):
    '''Test that replacing a tool raises a warning, and that this
    warning can be disabled.'''
    fake_process.register(['mock_exec1', '--version'], stdout='1.2.3')
    fake_process.register(['mock_exec2', '--version'], stdout='4.5.6')
    tb = ToolBox()
    mock_compiler1 = StubC("mock_c_compiler1", "mock_exec1", "suite")
    mock_compiler2 = StubC("mock_c_compiler2", "mock_exec2", "suite")
    tb.add_tool(mock_compiler1)

    warn_message = (f"Replacing existing tool '{mock_compiler1}' with "
                    f"'{mock_compiler2}'.")
    with warns(UserWarning, match=warn_message):
        tb.add_tool(mock_compiler2)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        tb.add_tool(mock_compiler1, silent_replace=True)


def test_tool_box_add_tool_not_avail(fake_process):
    '''Test that tools that are not available cannot be added to
    a tool box.'''
    fake_process.register(['gfortran', '--version'], returncode=1)
    tb = ToolBox()
    gfortran = Gfortran()
    with raises(RuntimeError) as err:
        tb.add_tool(gfortran)
    assert str(err.value) == f"Tool '{gfortran}' is not available."
