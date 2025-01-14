##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Tests tool repository functionality.
"""
from pytest import mark, raises

from fab.category import Category
from fab.tools.ar import Ar
from fab.tools.compiler import FortranCompiler, Gcc, Gfortran, Ifort
from fab.tools.linker import Linker
from fab.tool_repository import ToolRepository


class TestToolRepository:
    """
    Ensures ToolRepository functions correctly.
    """
    def test_singleton_action(self):
        """
        Tests the singleton behaviour.
        """
        tr1 = ToolRepository()
        tr2 = ToolRepository()
        print(repr(tr1))
        assert tr1 == tr2

    def test_tool_repository_constructor(self):
        '''Tests the ToolRepository constructor.'''
        tr = ToolRepository()
        assert Category.C_COMPILER in tr
        assert Category.FORTRAN_COMPILER in tr

    def test_tool_repository_get_tool(self):
        '''Tests get_tool.'''
        tr = ToolRepository()
        gfortran = tr.get_tool(Category.FORTRAN_COMPILER, "gfortran")
        assert isinstance(gfortran, Gfortran)

        ifort = tr.get_tool(Category.FORTRAN_COMPILER, "ifort")
        assert isinstance(ifort, Ifort)

    def test_tool_repository_get_tool_error(self):
        '''Tests error handling during tet_tool.'''
        tr = ToolRepository()
        with raises(KeyError) as err:
            tr.get_tool("unknown-category", "something")
        assert "Unknown category 'unknown-category'" in str(err.value)

        with raises(KeyError) as err:
            tr.get_tool(Category.C_COMPILER, "something")
        assert ("Unknown tool 'something' in category 'C_COMPILER'"
                in str(err.value))

    def test_tool_repository_get_default(self):
        '''Tests get_default.'''
        tr = ToolRepository()
        gfortran = tr.get_default(Category.FORTRAN_COMPILER, mpi=False,
                                  openmp=False)
        assert isinstance(gfortran, Gfortran)

        gcc_linker = tr.get_default(Category.LINKER, mpi=False, openmp=False)
        assert isinstance(gcc_linker, Linker)
        assert gcc_linker.name == "linker-gcc"

        gcc = tr.get_default(Category.C_COMPILER, mpi=False, openmp=False)
        assert isinstance(gcc, Gcc)

        # Test a non-compiler
        ar = tr.get_default(Category.AR)
        assert isinstance(ar, Ar)

    def test_tool_repository_get_default_error_invalid_category(self):
        '''Tests error handling in get_default, the category
        must be a Category, not e.g. a string.'''
        tr = ToolRepository()
        with raises(RuntimeError) as err:
            tr.get_default("unknown-category-type")
        assert "Invalid category type 'str'." in str(err.value)

    def test_tool_repository_get_default_error_missing_mpi(self):
        '''Tests error handling in get_default when the optional MPI
        parameter is missing (which is required for a compiler).'''
        tr = ToolRepository()
        with raises(RuntimeError) as err:
            tr.get_default(Category.FORTRAN_COMPILER, openmp=True)
        assert ("Invalid or missing mpi specification for 'FORTRAN_COMPILER'"
                in str(err.value))
        with raises(RuntimeError) as err:
            tr.get_default(Category.FORTRAN_COMPILER, mpi="123")
        assert ("Invalid or missing mpi specification for 'FORTRAN_COMPILER'"
                in str(err.value))

    def test_tool_repository_get_default_error_missing_openmp(self):
        '''Tests error handling in get_default when the optional openmp
        parameter is missing (which is required for a compiler).'''
        tr = ToolRepository()
        with raises(RuntimeError) as err:
            tr.get_default(Category.FORTRAN_COMPILER, mpi=True)
        assert ("Invalid or missing openmp specification for 'FORTRAN_COMPILER'"
                in str(err.value))
        with raises(RuntimeError) as err:
            tr.get_default(Category.FORTRAN_COMPILER, mpi=True, openmp="123")
        assert ("Invalid or missing openmp specification for 'FORTRAN_COMPILER'"
                in str(err.value))

    @mark.parametrize("mpi, openmp, message",
                      [(False, False, "any 'FORTRAN_COMPILER'."),
                       (False, True,
                        "'FORTRAN_COMPILER' that supports OpenMP."),
                       (True, False,
                        "'FORTRAN_COMPILER' that supports MPI."),
                       (True, True, "'FORTRAN_COMPILER' that supports MPI "
                        "and OpenMP.")])
    def test_tool_repository_get_default_error_missing_compiler(self,
                                                                mpi,
                                                                openmp,
                                                                message,
                                                                monkeypatch):
        '''Tests error handling in get_default when there is no compiler
        that fulfils the requirements with regards to OpenMP and MPI.'''
        tr = ToolRepository()
        monkeypatch.setitem(tr, Category.FORTRAN_COMPILER, [])
        with raises(RuntimeError) as err:
            tr.get_default(Category.FORTRAN_COMPILER, mpi=mpi, openmp=openmp)
        assert str(err.value) == f"Could not find {message}"

    def test_tool_repository_get_default_error_missing_openmp_compiler(self, monkeypatch):
        '''Tests error handling in get_default when there is a compiler, but it
        does not support OpenMP (which triggers additional tests in the
        ToolRepository.'''
        tr = ToolRepository()
        _ = FortranCompiler("gfortran", "gfortran", "gnu",
                            openmp_flag=None, module_folder_flag="-J")

        monkeypatch.setitem(tr, Category.FORTRAN_COMPILER, [])
        with raises(RuntimeError) as err:
            tr.get_default(Category.FORTRAN_COMPILER, mpi=False, openmp=True)
        assert ("Could not find 'FORTRAN_COMPILER' that supports OpenMP."
                in str(err.value))

    def test_tool_repository_default_compiler_suite(self):
        '''Tests the setting of default suite for compiler and linker.'''
        tr = ToolRepository()
        tr.set_default_compiler_suite("gnu")
        for cat in [Category.C_COMPILER, Category.FORTRAN_COMPILER,
                    Category.LINKER]:
            def_tool = tr.get_default(cat, mpi=False, openmp=False)
            assert def_tool.suite == "gnu"

        tr.set_default_compiler_suite("intel-classic")
        for cat in [Category.C_COMPILER, Category.FORTRAN_COMPILER,
                    Category.LINKER]:
            def_tool = tr.get_default(cat, mpi=False, openmp=False)
            assert def_tool.suite == "intel-classic"
        with raises(RuntimeError) as err:
            tr.set_default_compiler_suite("does-not-exist")
        assert ("Cannot find 'FORTRAN_COMPILER' in the suite 'does-not-exist'"
                in str(err.value))
