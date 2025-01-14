from pathlib import Path

from pytest import fixture, warns

from fab.cli import cli_fab
from fab.tool_repository import ToolRepository


@fixture(scope='class')
def dep_source_dir() -> Path:
    return Path(__file__).parent.parent / 'FortranDependencies' / 'project-source'


@fixture(scope='class')
def c_interop_source_dir() -> Path:
    return Path(__file__).parent.parent / 'CFortranInterop' / 'project-source'


class TestZeroConfig:
    def test_fortran_dependencies(self, dep_source_dir: Path, tmp_path: Path):
        """
        Tests that a simple Fortran program can be built.
        """
        with warns(DeprecationWarning,
                   match="RootIncFiles is deprecated as .inc files are due to be removed."):
            kwargs = {'project_label': 'fortran deps test',
                      'fab_workspace': tmp_path,
                      'multiprocessing': False}

            config = cli_fab(folder=dep_source_dir, kwargs=kwargs)

            assert (config.project_workspace / 'first').exists()
            assert (config.project_workspace / 'second').exists()

    def test_c_fortran_interop(self,
                               tmp_path: Path,
                               c_interop_source_dir: Path):
        """
        Tests a C prgram which calls Fortran.
        """
        with warns(DeprecationWarning,
                   match="RootIncFiles is deprecated as .inc files are due to be removed."):
            kwargs = {'project_label': 'CFInterop test',
                      'fab_workspace': tmp_path,
                      'multiprocessing': 'False'}

            config = cli_fab(folder=c_interop_source_dir, kwargs=kwargs)

            assert (config.project_workspace / 'main').exists()

    def test_fortran_explicit_gfortran(self,
                                       tmp_path: Path,
                                       c_interop_source_dir: Path):
        """
        Tests explicitly setting GCC as the default.
        """
        kwargs = {'project_label': 'fortran explicit gfortran',
                  'fab_workspace': tmp_path,
                  'multiprocessing': False}

        tr = ToolRepository()
        tr.set_default_compiler_suite("gnu")

        # TODO: If the intel compiler should be used here, the linker will
        # need an additional flag (otherwise duplicated `main` symbols will
        # occur). The following code can be used e.g. in cli.py:
        #
        # if config.tool_box.get_tool(Category.LINKER).name == "linker-ifort":
        #    flags = ["-nofor-main"]

        with warns(DeprecationWarning,
                   match="RootIncFiles is deprecated as .inc files are due to be removed."):
            config = cli_fab(folder=c_interop_source_dir, kwargs=kwargs)

        assert (config.project_workspace / 'main').exists()
