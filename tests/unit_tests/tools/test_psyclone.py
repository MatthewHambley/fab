##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Tests the PSyclone tool.
"""
from importlib import reload
from pathlib import Path
import typing  # Needed for monkey patching
from typing import Optional, Tuple
from unittest.mock import Mock

from pyfakefs.fake_filesystem import FakeFilesystem
from pytest import mark, raises, warns
from pytest_subprocess.fake_process import FakeProcess

from fab.tools.category import Category
import fab.tools.psyclone  # Needed for mockery
from fab.tools.psyclone import Psyclone

from source.fab import FabException
from tests.conftest import call_list, not_found_callback


def test_constructor():
    """
    Tests the default constructor.
    """
    psyclone = Psyclone()
    assert psyclone.category == Category.PSYCLONE
    assert psyclone.name == "psyclone"
    assert psyclone.exec_name == "psyclone"
    # pylint: disable=use-implicit-booleaness-not-comparison
    assert psyclone.get_flags() == []


@mark.parametrize("version", ["2.4.0", "2.5.0", "3.0.0", "3.1.0"])
def test_is_available_and_version(version: str,
                                  fs: FakeFilesystem,
                                  fake_process: FakeProcess) -> None:
    """
    Checks availability check.

    This check includes harvesting the tool's version number.
    """
    fs.create_file('/bin/psyclone', create_missing_dirs=True, st_mode=0o755)
    version_command = ['psyclone', '--version']
    fake_process.register(version_command,
                          stdout='PSyclone version: ' + version)

    psyclone = Psyclone()

    version_tuple = tuple(int(i) for i in version.split("."))
    assert psyclone.is_available is True
    assert psyclone.version == version_tuple
    assert call_list(fake_process) == [version_command]


def test_not_available(fs: FakeFilesystem) -> None:
    """
    Tests lack of availability.
    """
    fs.create_dir('/bin')
    psyclone = Psyclone()
    assert psyclone.is_available is False


def test_check_available_bad_version(fs: FakeFilesystem,
                                     fake_process: FakeProcess) -> None:
    """
    Tests executable which returns an unexpected version string.
    """
    fs.create_file('/bin/psyclone', create_missing_dirs=True, st_mode=0o755)
    fake_process.register(['psyclone', '--version'],
                          stdout='PSyclone version: NOT_A_NUMBER.4.0')

    psyclone = Psyclone()

    with raises(FabException,
               match="Unexpected version information for PSyclone: "
                     "'PSyclone version: NOT_A_NUMBER.4.0'"):
        _ = psyclone.is_available


def test_is_available_broken(fs: FakeFilesystem, fake_process: FakeProcess) -> None:
    """
    Checks a present but broken installation.
    """
    fs.create_file('/bin/psyclone', create_missing_dirs=True, st_mode=0o755)
    fake_process.register(['psyclone', '--version'], returncode=1)

    psyclone = Psyclone()
    config = Mock()

    with raises(RuntimeError) as err:
        psyclone.process(config,
                         Path("x90file"),
                         api='lfric',
                         psy_file=Path('/home/user/psy.f90'),
                         alg_file=Path('/home/user/alg.f90'))
    assert str(err.value) == ("PSyclone present but version unobtainable."
                              " Is installation broken?")


def test_processing_errors_without_api(fake_process: FakeProcess) -> None:
    """
    Test all processing errors in PSyclone if no API is specified.
    """
    version_command = ['psyclone', '--version']
    fake_process.register(version_command, stdout='PSyclone version: 3.0.0')

    psyclone = Psyclone()
    config = Mock()

    with raises(RuntimeError) as err:
        psyclone.process(config,
                         Path('x90file'),
                         api=None,
                         psy_file=Path('psy_file'))
    assert (str(err.value) == "PSyclone called without api, but psy_file "
                              "is specified.")

    with raises(RuntimeError) as err:
        psyclone.process(config,
                         Path('x90file'),
                         api=None,
                         alg_file=Path('alg_file'))
    assert (str(err.value) == "PSyclone called without api, but alg_file is "
                              "specified.")

    with raises(RuntimeError) as err:
        psyclone.process(config,
                         Path('x90file'),
                         api=None)
    assert (str(err.value) == "PSyclone called without api, but "
                              "transformed_file is not specified.")


@mark.parametrize("api", ["dynamo0.3", "lfric"])
def test_processing_errors_with_api(api: str,
                                    fake_process: FakeProcess) -> None:
    """
    Tests potential processing errors with unspecified API.
    """
    version_command = ['psyclone', '--version']
    fake_process.register(version_command, stdout='PSyclone version: 2.6.0')

    psyclone = Psyclone()
    config = Mock()

    with raises(RuntimeError) as err:
        psyclone.process(config,
                         Path("x90file"),
                         api=api,
                         psy_file=Path("psy_file"))
    assert str(err.value).startswith(
        f"PSyclone called with api '{api}', but no alg_file is specified"
    )
    with raises(RuntimeError) as err:
        psyclone.process(config,
                         Path("x90file"),
                         api=api,
                         alg_file=Path("alg_file"))
    assert str(err.value).startswith(
        f"PSyclone called with api '{api}', but no psy_file is specified"
    )
    with raises(RuntimeError) as err:
        psyclone.process(config,
                         Path("x90file"),
                         api=api,
                         psy_file=Path("psy_file"),
                         alg_file=Path("alg_file"),
                         transformed_file=Path("transformed_file"))
    assert str(err.value).startswith(
        f"PSyclone called with api '{api}' and transformed_file"
    )


@mark.parametrize("version", ["2.4.0", "2.5.0"])
@mark.parametrize("api", [("dynamo0.3", "dynamo0.3"),
                          ("lfric", "dynamo0.3"),
                          ("gocean1.0", "gocean1.0"),
                          ("gocean", "gocean1.0")
                          ])
def test_process_api_old_psyclone(api: Tuple[str, str], version: str,
                                  fs: FakeFilesystem,
                                  fake_process: FakeProcess) -> None:
    """
    Tests old style API support with PSyclone 2.5.0 and earlier.
    """
    api_in, api_out = api

    fs.create_file('/bin/psyclone', create_missing_dirs=True, st_mode=0o755)

    version_command = ['psyclone', '--version']
    fake_process.register(version_command,
                          stdout='PSyclone version: ' + version)

    process_command = ['psyclone', '-api', api_out, '-opsy', 'psy_file',
                       '-oalg', 'alg_file', '-l', 'all', '-s', 'script_called',
                       '-c', 'psyclone.cfg', '-d', 'root1', '-d', 'root2',
                       'x90_file']
    fake_process.register(process_command)

    psyclone = Psyclone()
    config = Mock()

    psyclone.process(config=config,
                     api=api_in,
                     x90_file=Path("x90_file"),
                     psy_file=Path("psy_file"),
                     alg_file=Path("alg_file"),
                     transformation_script=lambda x, y: Path('script_called'),
                     kernel_roots=["root1", "root2"],
                     additional_parameters=["-c", "psyclone.cfg"])

    assert call_list(fake_process) == [
        version_command, process_command
    ]


@mark.parametrize('version', ['2.4.0', '2.5.0'])
@mark.parametrize('api', [None, 'nemo'])
def test_process_nemo_api_old_psyclone(version: str, api: Optional[str],
                                       fs: FakeFilesystem,
                                       fake_process: FakeProcess) -> None:
    """
    Tests NEMO API with PSyclone 2.5.0 or earlier.

    ToDo: The wierd extra bits performed for 2.5.0 look highly dubious.
    """
    fs.create_file('/bin/psyclone', create_missing_dirs=True, st_mode=0o755)

    version_command = ['psyclone', '--version']
    fake_process.register(version_command,
                          stdout='PSyclone version: ' + version)
    if version == '2.5.0':
        random_command = ['psyclone', '-api', 'nemo',
                          fab.tools.psyclone.__file__]
        fake_process.register(random_command, returncode=1)
    psyclone_command = ['psyclone', '-api', 'nemo', '-opsy', 'psy_file',
                        '-l', 'all', '-s', 'script_called',
                        '-c', 'psyclone.cfg', '-d', 'root1', '-d', 'root2',
                        'x90_file']
    fake_process.register(psyclone_command)

    psyclone = Psyclone()

    config = Mock()

    psyclone.process(config=config,
                     api=api,
                     x90_file=Path('x90_file'),
                     transformed_file=Path('psy_file'),
                     transformation_script=lambda x, y: Path('script_called'),
                     kernel_roots=["root1", "root2"],
                     additional_parameters=["-c", "psyclone.cfg"])

    assert call_list(fake_process) == [
        version_command, psyclone_command
    ]


@mark.parametrize("api",
                  [
                      ("dynamo0.3", "lfric"),
                      ("lfric", "lfric"),
                      ("gocean1.0", "gocean"),
                      ("gocean", "gocean")
                  ])
def test_process_api_new_psyclone(api: Tuple[str, str],
                                  fs: FakeFilesystem,
                                  fake_process: FakeProcess) -> None:
    """
    Test running PSyclone 3.0.0. It uses new API names, and we need to
    check that the old style names are converted to the new names.
    """
    api_in, api_out = api

    fs.create_file('/bin/psyclone', create_missing_dirs=True, st_mode=0o755)

    version_command = ['psyclone', '--version']
    fake_process.register(version_command, stdout='PSyclone version: 3.0.0')
    psyclone_command = ['psyclone', '--psykal-dsl', api_out,
                        '-opsy', 'psy_file', '-oalg', 'alg_file', '-l', 'all',
                        '-s', 'script_called', '-c', 'psyclone.cfg',
                        '-d', 'root1', '-d', 'root2', 'x90_file']
    fake_process.register(psyclone_command)

    psyclone = Psyclone()
    config = Mock()

    psyclone.process(config=config,
                     api=api_in,
                     x90_file=Path('x90_file'),
                     psy_file=Path('psy_file'),
                     alg_file="alg_file",
                     transformation_script=lambda x, y: Path('script_called'),
                     kernel_roots=["root1", "root2"],
                     additional_parameters=["-c", "psyclone.cfg"])

    assert call_list(fake_process) == [
        version_command, psyclone_command
    ]


def test_process_no_api_new_psyclone(fs: FakeFilesystem,
                                     fake_process: FakeProcess) -> None:
    """
    Test running the PSyclone 3.0.0 without an API, i.e. as transformation
    only.
    """
    fs.create_file('/bin/psyclone', create_missing_dirs=True, st_mode=0o755)

    version_command = ['psyclone', '--version']
    fake_process.register(version_command, stdout='PSyclone version: 3.0.0')
    psyclone_command = ['psyclone', '-o', 'psy_file', '-l', 'all',
                        '-s', 'script_called', '-c', 'psyclone.cfg',
                        '-d', 'root1', '-d', 'root2', 'x90_file']
    fake_process.register(psyclone_command)

    psyclone = Psyclone()
    config = Mock()

    psyclone.process(config=config,
                     api="",
                     x90_file=Path('x90_file'),
                     transformed_file=Path('psy_file'),
                     transformation_script=lambda x, y: Path('script_called'),
                     kernel_roots=["root1", "root2"],
                     additional_parameters=["-c", "psyclone.cfg"])

    assert call_list(fake_process) == [
        version_command, psyclone_command
    ]


def test_process_nemo_api_new_psyclone(fs: FakeFilesystem,
                                       fake_process: FakeProcess) -> None:
    """
    Test running PSyclone 3.0.0 and test that backwards compatibility of
    using the nemo api works, i.e. '-api nemo' is just removed.
    """
    fs.create_file('/bin/psyclone', create_missing_dirs=True, st_mode=0o755)

    version_command = ['psyclone', '--version']
    fake_process.register(version_command, stdout='PSyclone version: 3.0.0')
    psyclone_command = ['psyclone', '-o', 'psy_file', '-l', 'all',
                        '-s', 'script_called', '-c', 'psyclone.cfg',
                        '-d', 'root1', '-d', 'root2', 'x90_file']
    fake_process.register(psyclone_command)

    psyclone = Psyclone()
    config = Mock()

    psyclone.process(config=config,
                     api="nemo",
                     x90_file=Path('x90_file'),
                     transformed_file=Path('psy_file'),
                     transformation_script=lambda x, y: Path('script_called'),
                     kernel_roots=["root1", "root2"],
                     additional_parameters=["-c", "psyclone.cfg"])

    assert call_list(fake_process) == [
        version_command, psyclone_command
    ]


def test_type_checking_import(monkeypatch) -> None:
    """
    PSyclone contains an import of TYPE_CHECKING to break a circular
    dependency. In order to reach 100% coverage of PSyclone, we set
    mock TYPE_CHECKING to be true and force a re-import of the module.
    TODO 314: This test can be removed once #314 is fixed.
    """
    monkeypatch.setattr(typing, 'TYPE_CHECKING', True)
    # This import will not actually re-import, since the module
    # is already imported. But we need this in order to call reload:
    # pylint: disable=import-outside-toplevel
    import fab.tools.psyclone
    reload(fab.tools.psyclone)
