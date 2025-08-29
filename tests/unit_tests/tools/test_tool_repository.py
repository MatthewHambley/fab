##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Tests ToolBox class.
"""
from pathlib import Path
from typing import Type

from pyfakefs.fake_filesystem import FakeFilesystem
from pytest import mark, raises

from fab.tools.ar import Ar
from fab.tools.category import Category
from fab.tools.compiler import FortranCompiler, Gcc, Gfortran, Ifort
from fab.tools.compiler_wrapper import Mpif90
from fab.tools.tool import Tool
from fab.tools.tool_repository import ToolRepository


def test_tool_repository_get_singleton_new():
    """
    Tests the singleton behaviour.
    """
    ToolRepository._singleton = None
    tr1 = ToolRepository()
    tr2 = ToolRepository()
    assert tr1 == tr2
    ToolRepository._singleton = None
    tr3 = ToolRepository()
    assert tr1 is not tr3


def test_tool_repository_constructor():
    """
    Tests the ToolRepository constructor.
    """
    tr = ToolRepository()
    assert Category.C_COMPILER in tr
    assert Category.FORTRAN_COMPILER in tr


@mark.parametrize('fortran, expected', [
    ('gfortran', Gfortran),
    ('ifort', Ifort)
])
def test_tool_repository_get_tool(fortran: str, expected: Type, fs: FakeFilesystem):
    """
    Checks basic "get tool" behaviour.
    """
    fs.create_file('/bin/' + fortran, create_missing_dirs=True, st_mode=0o755)
    ToolRepository._singleton = None
    tr = ToolRepository()
    gfortran = tr.get_tool(Category.FORTRAN_COMPILER, fortran)
    assert isinstance(gfortran, expected)


def test_tool_repository_get_tool_with_exec_name(stub_fortran_compiler,
                                                 fs: FakeFilesystem) -> None:
    """
    Checks tool retrieval using executable name.

    As opposed to Fab identifier (e.g. mpif90-gfortran).

    Todo: Messing with private state is bad.
    """
    ToolRepository._singleton = None
    tr = ToolRepository()

    # First add just one unavailable Fortran compiler and an mpif90 wrapper:
    tr[Category.FORTRAN_COMPILER] = []
    tr.add_tool(stub_fortran_compiler)
    mpif90 = Mpif90(stub_fortran_compiler)
    tr.add_tool(mpif90)

    # If mpif90 is not available, an error is raised:
    try:
        tr.get_tool(Category.FORTRAN_COMPILER, "mpif90")
    except KeyError as err:
        assert "Unknown tool 'mpif90' in category" in str(err)

    # When using the exec name, the compiler must be available:
    fs.create_file('/bin/mpif90', create_missing_dirs=True, st_mode=0o755)
    mpif90._is_available = None
    f90 = tr.get_tool(Category.FORTRAN_COMPILER, "mpif90")
    assert f90 is mpif90

    # Now add a different, available,  mpif90 and make mpif90-stub-fortran
    # unavailable. We need to make sure we then get mpif90-gfortran:
    fs.remove('/bin/sfc')
    stub_fortran_compiler._is_available = None
    fs.create_file('/bin/tfc', create_missing_dirs=True, st_mode=0o755)
    fc_new = FortranCompiler("Test Fortran", 'tfc', 'test',
                             version_regex=r'([\d.]+)')
    tr.add_tool(fc_new)
    mpif90_new = Mpif90(fc_new)
    tr.add_tool(mpif90_new)
    f90 = tr.get_tool(Category.FORTRAN_COMPILER, "mpif90")
    assert f90 is mpif90_new

    # Then verify using the full path
    fs.remove('/bin/mpif90')
    fs.create_file('/some/where/mpif90', create_missing_dirs=True, st_mode=0o755)
    f90 = tr.get_tool(Category.FORTRAN_COMPILER, "/some/where/mpif90")
    assert f90 is mpif90_new
    assert f90.executable == Path("/some/where/mpif90")
    # Reset the repository, since this test messed up the compilers.
    ToolRepository._singleton = None


def test_get_tool_error(fs: FakeFilesystem):
    """
    Checks tool getting error handling.
    """
    fs.create_dir('/bin')
    ToolRepository._singleton = None
    tr = ToolRepository()
    with raises(KeyError) as err:
        tr.get_tool("unknown-category", "something")
    assert "Unknown category 'unknown-category'" in str(err.value)

    with raises(KeyError) as err:
        tr.get_tool(Category.C_COMPILER, "something")
    assert ("Unknown tool 'something' in category 'C_COMPILER'"
            in str(err.value))


def test_get_default(fs: FakeFilesystem) -> None:
    """
    Checks default compilers.
    """
    fs.create_file('/bin/gfortran', create_missing_dirs=True, st_mode=0o755)
    fs.create_file('/bin/gcc', create_missing_dirs=True, st_mode=0o755)
    fs.create_file('/bin/ar', create_missing_dirs=True, st_mode=0o755)
    ToolRepository._singleton = None
    tr = ToolRepository()
    gfortran = tr.get_default(Category.FORTRAN_COMPILER, mpi=False,
                              openmp=False)
    assert isinstance(gfortran, Gfortran)

    gcc = tr.get_default(Category.C_COMPILER, mpi=False, openmp=False)
    assert isinstance(gcc, Gcc)

    # Test a non-compiler
    ar = tr.get_default(Category.AR)
    assert isinstance(ar, Ar)


def test_get_default_error_invalid_category() -> None:
    """
    Tests error handling in get_default, the category must be a Category,
    not e.g. a string.
    """
    tr = ToolRepository()
    with raises(RuntimeError) as err:
        tr.get_default("unknown-category-type")  # type: ignore[arg-type]
    assert "Invalid category type 'str'." in str(err.value)


def test_get_default_error_missing_mpi() -> None:
    """
    Tests error handling in get_default when the optional MPI
    parameter is missing (which is required for a compiler).
    """
    tr = ToolRepository()
    with raises(RuntimeError) as err:
        tr.get_default(Category.FORTRAN_COMPILER, openmp=True)
    assert str(err.value) == ("Invalid or missing mpi specification "
                              "for 'FORTRAN_COMPILER'.")

    with raises(RuntimeError) as err:
        tr.get_default(Category.FORTRAN_COMPILER, mpi=True)
    assert str(err.value) == ("Invalid or missing openmp specification "
                              "for 'FORTRAN_COMPILER'.")


def test_get_default_error_missing_openmp() -> None:
    """
    Tests error handling in get_default when the optional openmp
    parameter is missing (which is required for a compiler).
    """
    tr = ToolRepository()

    with raises(RuntimeError) as err:
        tr.get_default(Category.FORTRAN_COMPILER, mpi=True)
    assert ("Invalid or missing openmp specification for 'FORTRAN_COMPILER'"
            in str(err.value))
    with raises(RuntimeError) as err:
        tr.get_default(Category.FORTRAN_COMPILER, mpi=True,
                       openmp='123')  # type: ignore[arg-type]
    assert str(err.value) == ("Invalid or missing openmp specification "
                              "for 'FORTRAN_COMPILER'.")


@mark.parametrize("mpi, openmp, message",
                  [(False, False, "any 'FORTRAN_COMPILER'."),
                   (False, True,
                    "'FORTRAN_COMPILER' that supports OpenMP."),
                   (True, False,
                    "'FORTRAN_COMPILER' that supports MPI."),
                   (True, True, "'FORTRAN_COMPILER' that supports MPI "
                    "and OpenMP.")])
def test_get_default_error_missing_compiler(mpi, openmp, message,
                                            monkeypatch) -> None:
    """
    Tests error handling in get_default when there is no compiler
    that fulfils the requirements with regards to OpenMP and MPI.
    """
    tr = ToolRepository()
    monkeypatch.setitem(tr, Category.FORTRAN_COMPILER, [])

    with raises(RuntimeError) as err:
        tr.get_default(Category.FORTRAN_COMPILER, mpi=mpi, openmp=openmp)
    assert str(err.value) == f"Could not find {message}"


def test_get_default_error_missing_openmp_compiler(monkeypatch) -> None:
    """
    Tests error handling in get_default when there is a compiler, but it
    does not support OpenMP (which triggers additional tests in the
    ToolRepository.

    Todo: Monkeying with internal state is bad.
    """
    fc = FortranCompiler("Simply Fortran", 'sfc', 'simply', openmp_flag=None,
                         module_folder_flag="-mods", version_regex=r'([\d.]+]')

    tr = ToolRepository()
    monkeypatch.setitem(tr, Category.FORTRAN_COMPILER, [fc])

    with raises(RuntimeError) as err:
        tr.get_default(Category.FORTRAN_COMPILER, mpi=False, openmp=True)
    assert (str(err.value) == "Could not find 'FORTRAN_COMPILER' that "
                              "supports OpenMP.")


@mark.parametrize('category', [Category.C_COMPILER,
                               Category.FORTRAN_COMPILER,
                               Category.LINKER])
def test_default_gcc_suite(category, fs: FakeFilesystem) -> None:
    """
    Tests setting default suite to "GCC" produces correct tools.
    """
    fs.create_file('/bin/gcc', create_missing_dirs=True, st_mode=0o755)
    fs.create_file('/bin/gfortran', create_missing_dirs=True, st_mode=0o755)
    ToolRepository._singleton = None
    tr = ToolRepository()
    tr.set_default_compiler_suite('gnu')
    def_tool = tr.get_default(category, mpi=False, openmp=False)
    assert def_tool.suite == 'gnu'


@mark.parametrize('category', [Category.C_COMPILER,
                               Category.FORTRAN_COMPILER,
                               Category.LINKER])
def test_default_intel_suite(category, fs: FakeFilesystem) -> None:
    """
    Tests setting default suite to "classic-intel" produces correct tools.
    """
    fs.create_file('/bin/icc', create_missing_dirs=True, st_mode=0o755)
    fs.create_file('/bin/ifort', create_missing_dirs=True, st_mode=0o755)
    ToolRepository._singleton = None
    tr = ToolRepository()
    tr.set_default_compiler_suite('intel-classic')
    def_tool = tr.get_default(category, mpi=False, openmp=False)
    assert def_tool.suite == 'intel-classic'


def test_default_suite_unknown() -> None:
    """
    Tests handling if a compiler suite is selected that does not exist.
    """
    ToolRepository._singleton = None
    repo = ToolRepository()
    with raises(RuntimeError) as err:
        repo.set_default_compiler_suite("does-not-exist")
    assert str(err.value) == ("Cannot find 'FORTRAN_COMPILER' in "
                              "the suite 'does-not-exist'.")


def test_no_tool_available(fs: FakeFilesystem) -> None:
    """
    Tests error handling if no tool is available.
    """
    ToolRepository._singleton = None
    tr = ToolRepository()
    tr.set_default_compiler_suite("gnu")

    with raises(RuntimeError) as err:
        tr.get_default(Category.SHELL)
    assert (str(err.value) == "Can't find available 'SHELL' tool. Tools are "
                              "'sh'.")


def test_tool_repository_full_path(fs: FakeFilesystem) -> None:
    """
    Checks full path request.

    The appropriate tool should be returned with updated executable path.
    """
    fs.create_file('/opt/test/bin/ttool', create_missing_dirs=True, st_mode=0o755)
    ToolRepository._singleton = None
    tr = ToolRepository()
    tr.add_tool(Tool("Test tool", 'ttool', category=Category.MISC))
    tool = tr.get_tool(Category.MISC, '/opt/test/bin/ttool')
    assert isinstance(tool, Tool)
    assert tool.name == "Test tool"
    assert tool.exec_name == "ttool"
    assert tool.executable == Path("/opt/test/bin/ttool")
