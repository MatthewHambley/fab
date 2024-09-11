##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################

'''Tests the linker implementation.
'''

from pathlib import Path
from unittest import mock
import warnings

import pytest

from fab.tools import (Category, Linker)


def test_linker(mock_c_compiler, mock_fortran_compiler):
    '''Test the linker constructor.'''

    linker = Linker(name="my_linker", exec_name="my_linker.exe", suite="suite")
    assert linker.category == Category.LINKER
    assert linker.name == "my_linker"
    assert linker.exec_name == "my_linker.exe"
    assert linker.suite == "suite"
    assert linker.flags == []

    linker = Linker(name="my_linker", compiler=mock_c_compiler)
    assert linker.category == Category.LINKER
    assert linker.name == "my_linker"
    assert linker.exec_name == mock_c_compiler.exec_name
    assert linker.suite == mock_c_compiler.suite
    assert linker.flags == []

    linker = Linker(compiler=mock_c_compiler)
    assert linker.category == Category.LINKER
    assert linker.name == mock_c_compiler.name
    assert linker.exec_name == mock_c_compiler.exec_name
    assert linker.suite == mock_c_compiler.suite
    assert linker.flags == []

    linker = Linker(compiler=mock_fortran_compiler)
    assert linker.category == Category.LINKER
    assert linker.name == mock_fortran_compiler.name
    assert linker.exec_name == mock_fortran_compiler.exec_name
    assert linker.flags == []

    with pytest.raises(RuntimeError) as err:
        linker = Linker(name="no-exec-given")
    assert ("Either specify name, exec name, and suite or a compiler when "
            "creating Linker." in str(err.value))


def test_linker_gets_ldflags(mock_c_compiler):
    """Tests that the linker retrieves env.LDFLAGS"""
    with mock.patch.dict("os.environ", {"LDFLAGS": "-lm"}):
        linker = Linker(compiler=mock_c_compiler)
    assert "-lm" in linker.flags


def test_linker_check_available(mock_c_compiler):
    '''Tests the is_available functionality.'''

    # First test if a compiler is given. The linker will call the
    # corresponding function in the compiler:
    linker = Linker(compiler=mock_c_compiler)
    with mock.patch.object(mock_c_compiler, "check_available",
                           return_value=True) as comp_run:
        assert linker.check_available()
    # It should be called once without any parameter
    comp_run.assert_called_once_with()

    # Second test, no compiler is given. Mock Tool.run to
    # return a success:
    linker = Linker("ld", "ld", suite="gnu")
    mock_result = mock.Mock(returncode=0)
    with mock.patch('fab.tools.tool.subprocess.run',
                    return_value=mock_result) as tool_run:
        linker.check_available()
    tool_run.assert_called_once_with(
        ["ld", "--version"], capture_output=True, env=None,
        cwd=None, check=False)

    # Third test: assume the tool does not exist, check_available
    # will return False (and not raise  an exception)
    linker._is_available = None
    with mock.patch("fab.tools.tool.Tool.run",
                    side_effect=RuntimeError("")) as tool_run:
        assert linker.check_available() is False


# ====================
# Managing lib flags:
# ====================
def test_linker_get_lib_flags(mock_c_compiler):
    """Linker should provide a map of library names, each leading to a list of
    linker flags
    """
    linker = Linker(compiler=mock_c_compiler)
    # netcdf is built in to the linker, since it is reasonable portable
    result = linker.get_lib_flags("netcdf")
    assert result == ["$(nf-config --flibs)", "($nc-config --libs)"]


def test_linker_get_lib_flags_unknown(mock_c_compiler):
    """Linker should raise an error if flags are requested for a library that is
    unknown
    """
    linker = Linker(compiler=mock_c_compiler)
    with pytest.raises(RuntimeError) as err:
        linker.get_lib_flags("unknown")
    assert "Unknown library name: 'unknown'" in str(err.value)


def test_linker_add_lib_flags(mock_c_compiler):
    """Linker should provide a way to add a new set of flags for a library"""
    linker = Linker(compiler=mock_c_compiler)
    linker.add_lib_flags("xios", ["-L", "xios/lib", "-I", "xios/inc"])

    # Make sure we can get it back. The order should be maintained.
    result = linker.get_lib_flags("xios")
    assert result == ["-L", "xios/lib", "-I", "xios/inc"]


def test_linker_add_lib_flags_overwrite_defaults(mock_c_compiler):
    """Linker should provide a way to replace the default flags for a library"""
    linker = Linker(compiler=mock_c_compiler)

    # Initially we have the default netcdf flags
    result = linker.get_lib_flags("netcdf")
    assert result == ["$(nf-config --flibs)", "($nc-config --libs)"]

    # Replace them with another set of flags.
    warn_message = 'Replacing existing flags for library netcdf'
    with pytest.warns(UserWarning, match=warn_message):
        linker.add_lib_flags("netcdf", ["-L", "netcdf/lib", "-I", "netcdf/inc"])

    # Test that we can see our custom flags
    result = linker.get_lib_flags("netcdf")
    assert result == ["-L", "netcdf/lib", "-I", "netcdf/inc"]


def test_linker_add_lib_flags_overwrite_silent(mock_c_compiler):
    """Linker should provide the option to replace flags for a library without
    generating a warning
    """
    linker = Linker(compiler=mock_c_compiler)

    # Initially we have the default netcdf flags
    linker.add_lib_flags("customlib", ["-q", "/tmp", "-j"])
    assert linker.get_lib_flags("customlib") == ["-q", "/tmp", "-j"]

    # Replace them with another set of flags.
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        linker.add_lib_flags("customlib", ["-t", "-b"], silent_replace=True)

    # Test that we can see our custom flags
    result = linker.get_lib_flags("customlib")
    assert result == ["-t", "-b"]


def test_linker_remove_lib_flags(mock_c_compiler):
    """Linker should provide a way to remove the flags for a library"""
    linker = Linker(compiler=mock_c_compiler)
    linker.remove_lib_flags("netcdf")

    with pytest.raises(RuntimeError) as err:
        linker.get_lib_flags("netcdf")
    assert "Unknown library name: 'netcdf'" in str(err.value)


def test_linker_remove_lib_flags_unknown(mock_c_compiler):
    """Linker should silently allow removing flags for unknown library"""
    linker = Linker(compiler=mock_c_compiler)
    linker.remove_lib_flags("unkown")


# ====================
# Linking:
# ====================
def test_linker_c(mock_c_compiler):
    '''Test the link command line when no additional libraries are specified.'''
    linker = Linker(compiler=mock_c_compiler)
    mock_result = mock.Mock(returncode=0)
    with mock.patch('fab.tools.tool.subprocess.run',
                    return_value=mock_result) as tool_run:
        linker.link([Path("a.o")], Path("a.out"), openmp=False)
    tool_run.assert_called_with(
        ["mock_c_compiler.exe", "a.o", "-o", "a.out"],
        capture_output=True, env=None, cwd=None, check=False)


def test_linker_c_with_libraries(mock_c_compiler):
    """Test the link command line when additional libraries are specified."""
    linker = Linker(compiler=mock_c_compiler)
    with mock.patch.object(linker, "run") as link_run:
        linker.link([Path("a.o")], Path("a.out"), libs=["netcdf"], openmp=True)
    link_run.assert_called_with(
        ["-fopenmp", "a.o",
         "$(nf-config --flibs)", "($nc-config --libs)",
         "-o", "a.out"])


def test_linker_c_with_libraries_and_post_flags(mock_c_compiler):
    """Test the link command line when a library and additional flags are
    specified."""
    linker = Linker(compiler=mock_c_compiler)
    with mock.patch.object(linker, "run") as link_run:
        linker.link(
            [Path("a.o")], Path("a.out"),
            libs=["netcdf"], post_lib_flags=["-extra-flag"],
            openmp=False,
        )
    link_run.assert_called_with([
        "a.o",
        "$(nf-config --flibs)", "($nc-config --libs)", "-extra-flag",
        "-o", "a.out",
    ])


def test_linker_c_with_libraries_and_pre_flags(mock_c_compiler):
    """Test the link command line when a library and additional flags are
    specified."""
    linker = Linker(compiler=mock_c_compiler)
    with mock.patch.object(linker, "run") as link_run:
        linker.link(
            [Path("a.o")], Path("a.out"),
            pre_lib_flags=["-extra-flag"], libs=["netcdf"],
            openmp=False,
        )
    link_run.assert_called_with([
        "a.o",
        "-extra-flag", "$(nf-config --flibs)", "($nc-config --libs)",
        "-o", "a.out",
    ])


def test_linker_c_with_custom_libraries(mock_c_compiler):
    """Test the link command line when additional libraries are specified."""
    linker = Linker(compiler=mock_c_compiler)
    linker.add_lib_flags("customlib", ["-q", "/tmp", "-j"])
    with mock.patch.object(linker, "run") as link_run:
        linker.link([Path("a.o")], Path("a.out"),
                    libs=["customlib", "netcdf"], openmp=True)
    # The order of the 'libs' list should be maintained
    link_run.assert_called_with(
        ["-fopenmp", "a.o",
         "-q", "/tmp", "-j",
         "$(nf-config --flibs)", "($nc-config --libs)",
         "-o", "a.out"])


def test_linker_c_with_unknown_library(mock_c_compiler):
    """Test the link command raises an error when unknow libraries are
    specified.
    """
    linker = Linker(compiler=mock_c_compiler)\

    with pytest.raises(RuntimeError) as err:
        # Try to use "customlib" when we haven't added it to the linker
        linker.link([Path("a.o")], Path("a.out"),
                    libs=["netcdf", "customlib"], openmp=True)

    assert "Unknown library name: 'customlib'" in str(err.value)


def test_compiler_linker_add_compiler_flag(mock_c_compiler):
    '''Test that a flag added to the compiler will be automatically
    added to the link line (even if the flags are modified after creating the
    linker ... in case that the user specifies additional flags after creating
    the linker).'''

    linker = Linker(compiler=mock_c_compiler)
    mock_c_compiler.flags.append("-my-flag")
    mock_result = mock.Mock(returncode=0)
    with mock.patch('fab.tools.tool.subprocess.run',
                    return_value=mock_result) as tool_run:
        linker.link([Path("a.o")], Path("a.out"), openmp=False)
    tool_run.assert_called_with(
        ['mock_c_compiler.exe', '-my-flag', 'a.o', '-o', 'a.out'],
        capture_output=True, env=None, cwd=None, check=False)


def test_linker_add_compiler_flag():
    '''Make sure ad-hoc linker flags work if a linker is created without a
    compiler:
    '''
    linker = Linker("no-compiler", "no-compiler.exe", "suite")
    linker.flags.append("-some-other-flag")
    mock_result = mock.Mock(returncode=0)
    with mock.patch('fab.tools.tool.subprocess.run',
                    return_value=mock_result) as tool_run:
        linker.link([Path("a.o")], Path("a.out"), openmp=False)
    tool_run.assert_called_with(
        ['no-compiler.exe', '-some-other-flag', 'a.o', '-o', 'a.out'],
        capture_output=True, env=None, cwd=None, check=False)


def test_linker_all_flag_types(mock_c_compiler):
    """Make sure all possible sources of linker flags are used in the right
    order"""
    with mock.patch.dict("os.environ", {"LDFLAGS": "-ldflag"}):
        linker = Linker(compiler=mock_c_compiler)

    mock_c_compiler.flags.extend(["-compiler-flag1", "-compiler-flag2"])
    linker.flags.extend(["-linker-flag1", "-linker-flag2"])
    linker.add_lib_flags("customlib", ["-libflag1", "libflag2"])

    mock_result = mock.Mock(returncode=0)
    with mock.patch("fab.tools.tool.subprocess.run",
                    return_value=mock_result) as tool_run:
        linker.link([
            Path("a.o")], Path("a.out"),
            pre_lib_flags=["-prelibflag1", "-prelibflag2"],
            libs=["customlib", "netcdf"],
            post_lib_flags=["-postlibflag1", "-postlibflag2"],
            openmp=True)

    tool_run.assert_called_with([
        "mock_c_compiler.exe",
        # Note: compiler flags and linker flags will be switched when the Linker
        # becomes a CompilerWrapper in a following PR
        "-ldflag", "-linker-flag1", "-linker-flag2",
        "-compiler-flag1", "-compiler-flag2",
        "-fopenmp",
        "a.o",
        "-prelibflag1", "-prelibflag2",
        "-libflag1", "libflag2",
        "$(nf-config --flibs)", "($nc-config --libs)",
        "-postlibflag1", "-postlibflag2",
        "-o", "a.out"],
        capture_output=True, env=None, cwd=None, check=False)
