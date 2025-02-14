##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Tests the repository of all tools.
"""
from pytest import mark, raises
from pytest_subprocess.fake_process import FakeProcess

from tests.conftest import not_found_callback

from fab.tools.ar import Ar
from fab.tools.category import Category
from fab.tools.compiler import CCompiler, FortranCompiler, Gcc, Gfortran, Ifort
from fab.tools.tool_repository import ToolRepository


def test_get_singleton() -> None:
    """
    Tests object singleton behaviour.
    """
    tr1 = ToolRepository()
    tr2 = ToolRepository()
    assert tr1 is tr2


def test_constructor() -> None:
    """
    Tests default constructor.
    """
    tr = ToolRepository()
    assert Category.C_COMPILER in tr
    assert Category.FORTRAN_COMPILER in tr


def test_get_tool() -> None:
    """
    Tests tool retrieval.
    """
    tr = ToolRepository()
    gfortran = tr.get_tool(Category.FORTRAN_COMPILER, "gfortran")
    assert isinstance(gfortran, Gfortran)

    ifort = tr.get_tool(Category.FORTRAN_COMPILER, "ifort")
    assert isinstance(ifort, Ifort)


def test_get_tool_error() -> None:
    """
    Tests retrieval failure.
    """
    tr = ToolRepository()
    with raises(KeyError) as err:
        # We have to disable type checking for this line as it intentially
        # passes the wrong type.
        #
        tr.get_tool("unknown-category", "something")  # type:ignore
    assert str(err.value).startswith('"Unknown category \'unknown-category\'')

    with raises(KeyError) as err:
        tr.get_tool(Category.C_COMPILER, "something")
    assert str(err.value).startswith(
        '"Unknown tool \'something\' in category \'C_COMPILER\''
    )


def test_get_default():
    """
    Tests getting a default tool.
    """
    tr = ToolRepository()
    tr.set_default_compiler_suite('gnu')
    gfortran = tr.get_default(Category.FORTRAN_COMPILER, mpi=False,
                              openmp=False)
    assert isinstance(gfortran, Gfortran)

    gcc = tr.get_default(Category.C_COMPILER, mpi=False, openmp=False)
    assert isinstance(gcc, Gcc)

    # Test a non-compiler
    ar = tr.get_default(Category.AR)
    assert isinstance(ar, Ar)


def test_get_default_error_invalid_category():
    """
    Tests attempt to get a default using something other than a category.
    """
    tr = ToolRepository()
    with raises(RuntimeError) as err:
        tr.get_default("unknown-category-type")
    assert str(err.value) == "Invalid category type 'str'."


def test_get_default_error_missing_mpi():
    """
    Tests attempt to get a default compiler without specifying MPI.
    """
    tr = ToolRepository()
    with raises(RuntimeError) as err:
        tr.get_default(Category.FORTRAN_COMPILER, openmp=True)
    assert str(err.value) \
        == "Invalid or missing mpi specification for 'FORTRAN_COMPILER'."
    with raises(RuntimeError) as err:
        tr.get_default(Category.FORTRAN_COMPILER, mpi="123")
    assert str(err.value) \
        == "Invalid or missing mpi specification for 'FORTRAN_COMPILER'."


def test_get_default_error_missing_openmp():
    """
    Tests attempt to get a default compiler without specifying OpenMP.
    """
    tr = ToolRepository()
    with raises(RuntimeError) as err:
        tr.get_default(Category.FORTRAN_COMPILER, mpi=True)
    assert str(err.value) \
        == "Invalid or missing openmp specification for 'FORTRAN_COMPILER'."
    with raises(RuntimeError) as err:
        tr.get_default(Category.FORTRAN_COMPILER, mpi=True, openmp="123")
    assert str(err.value) \
        == "Invalid or missing openmp specification for 'FORTRAN_COMPILER'."


@mark.parametrize("mpi, openmp, message",
                  [(False, False, "any 'FORTRAN_COMPILER'"),
                   (False, True,
                    "'FORTRAN_COMPILER' that supports OpenMP"),
                   (True, False,
                    "'FORTRAN_COMPILER' that supports MPI"),
                   (True, True, "'FORTRAN_COMPILER' that supports MPI "
                                "and OpenMP")])
def test_get_default_error_missing_compiler(mpi: bool,
                                            openmp: bool,
                                            message: str,
                                            monkeypatch) -> None:
    """
    Tests attempts to get a default where nothing satisfies requirements.
    """
    tr = ToolRepository()
    monkeypatch.setitem(tr, Category.FORTRAN_COMPILER, [])
    with raises(RuntimeError) as err:
        tr.get_default(Category.FORTRAN_COMPILER, mpi=mpi, openmp=openmp)
    assert str(err.value) == f"Could not find {message}."


def test_get_default_compiler_missing_openmp(fake_process: FakeProcess,
                                             monkeypatch) -> None:
    """
    Tests default compiler which exists but does not support OpenMP.
    """
    fake_process.register(['sfc', '--version'], stdout='2.3.4')
    fake_process.register(['scc', '--version'], stdout='2.3.4')

    tr = ToolRepository()
    monkeypatch.setitem(tr, Category.C_COMPILER, [])
    fc = FortranCompiler("some fortran", "sfc", "some",
                         openmp_flag=None, module_folder_flag="-mod",
                         version_regex=r'([\d.]+)')
    tr.add_tool(fc)

    monkeypatch.setitem(tr, Category.FORTRAN_COMPILER, [])
    cc = CCompiler('some c', 'scc', 'some',
                   openmp_flag=None, version_regex=r'([\d.]+)')
    tr.add_tool(cc)

    tr.set_default_compiler_suite('some')

    with raises(RuntimeError) as err:
        _ = tr.get_default(Category.FORTRAN_COMPILER, mpi=False, openmp=True)
    assert str(err.value) \
        == "Could not find 'FORTRAN_COMPILER' that supports OpenMP."

    with raises(RuntimeError) as err:
        _ = tr.get_default(Category.C_COMPILER, mpi=False, openmp=True)
    assert str(err.value) \
        == "Could not find 'C_COMPILER' that supports OpenMP."


@mark.parametrize('suite', ['gnu', 'intel-classic'])
@mark.parametrize(
    'category',
    [Category.C_COMPILER, Category.FORTRAN_COMPILER, Category.LINKER]
)
def test_default_compiler_suite(suite: str, category: Category,
                                fake_process: FakeProcess) -> None:
    """
    Tests default compiler management.
    """
    fake_process.register(['icc', '-V'], stdout='icc (ICC) 1.2.3')
    fake_process.register(['ifort', '-V'], stdout='ifort (IFORT) 1.2.3')

    tr = ToolRepository()
    tr.set_default_compiler_suite(suite)

    def_tool = tr.get_default(category, mpi=False, openmp=False)
    assert def_tool.suite == suite


def test_default_compiler_suite_missing() -> None:
    tr = ToolRepository()

    with raises(RuntimeError) as err:
        tr.set_default_compiler_suite("does-not-exist")
    assert str(err.value) \
           == "Cannot find 'FORTRAN_COMPILER' in the suite 'does-not-exist'."


def test_no_tool_available(fake_process: FakeProcess) -> None:
    """
    Tests getting non existant default.
    """
    fake_process.register(['sh', '-c', 'echo hello'],
                          callback=not_found_callback)
    fake_process.register(['bash', '-c', 'echo hello'],
                          callback=not_found_callback)
    fake_process.register(['ksh', '-c', 'echo hello'],
                          callback=not_found_callback)
    fake_process.register(['dash', '-c', 'echo hello'],
                          callback=not_found_callback)
    fake_process.register(['zsh', '-c', 'echo hello'],
                          callback=not_found_callback)

    tr = ToolRepository()
    tr.set_default_compiler_suite("gnu")

    with raises(RuntimeError) as err:
        tr.get_default(Category.SHELL)
    assert str(err.value) == "Can't find available 'SHELL' tool. Tools are " \
                             "sh, bash, ksh, dash, zsh."
