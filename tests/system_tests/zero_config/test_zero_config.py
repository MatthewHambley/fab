from pathlib import Path
from shutil import copytree
from subprocess import run

from pytest import warns

from fab.cli import cli_fab
from fab.tools import ToolRepository


class TestZeroConfig:
    """
    Exercises "zero configuration" mode.
    """
    def test_fortran(self, tmp_path: Path) -> None:
        """
        Tests a sample Fortran source.

        ToDo: Fragile due to assumption of donor code.
        """
        copytree(
            Path(__file__).parent.parent / 'FortranDependencies' / 'project-source',
            tmp_path / 'source'
        )

        kwargs = {'project_label': 'fortran test',
                  'fab_workspace': tmp_path,
                  'multiprocessing': False}

        with warns(DeprecationWarning,
                   match="RootIncFiles is deprecated as .inc files are due "
                         "to be removed."):

            config = cli_fab(folder=tmp_path / 'source', kwargs=kwargs)

        assert (config.project_workspace / 'first').exists()
        assert (config.project_workspace / 'second').exists()

    def test_c(self, tmp_path: Path) -> None:
        """
        Tests a sample C project.

        ToDo: Fragility due to assumption of source donor.
        """
        copytree(
            Path(__file__).parent.parent / 'CUserHeader' / 'project-source',
            tmp_path / 'source'
        )

        kwargs = {'project_label': 'c test',
                  'fab_workspace': tmp_path,
                  'multiprocessing': False}
        with warns(DeprecationWarning,
                   match="RootIncFiles is deprecated as .inc files are due to be removed."):
            config = cli_fab(folder=tmp_path / 'source', kwargs=kwargs)
        print([fobject for fobject in config.project_workspace.iterdir()])
        assert (config.project_workspace / 'main').exists()

    def test_c_fortran(self, tmp_path: Path) -> None:
        """
        Tests a sample C project which interworks with Fortran.

        ToDo: Fragility due to assumption of source donor.
        """
        copytree(
            Path(__file__).parent.parent / 'CFortranInterop' / 'project-source',
            tmp_path / 'source'
        )

        kwargs = {'project_label': 'c fortran test',
                  'fab_workspace': tmp_path,
                  'multiprocessing': False}
        with warns(DeprecationWarning,
                   match="RootIncFiles is deprecated as .inc files are due to be removed."):
            config = cli_fab(folder=tmp_path / 'source', kwargs=kwargs)
        print([fobject for fobject in config.project_workspace.iterdir()])
        assert (config.project_workspace / 'main').exists()
