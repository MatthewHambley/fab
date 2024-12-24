##############################################################################
# (c) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT
# which you should have received as part of this distribution
##############################################################################
"""
Tests version control interfaces.
"""
from collections import deque
from filecmp import cmpfiles, dircmp
from pathlib import Path
from shutil import which
from unittest import mock
from subprocess import Popen, run
from time import sleep
from typing import List, Tuple

from pytest import TempPathFactory, fixture, mark, raises
from pytest_subprocess.fake_process import FakeProcess

from fab.category import Category
from fab.tools.versioning import Fcm, Git, Subversion


class TestGit:
    """
    Tests of the Git repository interface.
    """
    def test_git_constructor(self):
        '''Test the git constructor.'''
        git = Git()
        assert git.category == Category.GIT
        assert git.flags == []

    def test_git_available(self, mock_process: FakeProcess):
        """
        Tests Git availability.

        This test mocks the subprocess for speed and portability. Validation
        when actually shelling out to a subprocess happens in system testing.
        """
        git = Git()
        assert git.is_available is True
        assert mock_process.calls == deque([['git', 'help']])

    def test_git_unavailable(self, fake_process: FakeProcess):
        """
        Tests Git unavailability.

        This test mocks the subprocess for speed and portability. Validation
        when actually shelling out to a subprocess happens in system testing.
        """
        git = Git()
        fake_process.register(['git', 'help'], returncode=1)
        assert git.is_available is False
        assert fake_process.calls == deque([['git', 'help']])

    def test_git_current_commit(self, fake_process: FakeProcess):
        """
        Tests discover revision of the current working copy at CSD.

        This test mocks the subprocess for speed and portability. Validation
        when actually shelling out to a subprocess happens in system testing.
        """
        git = Git()
        fake_process.register(['git', 'log', '--oneline', '-n', '1'], stdout='abc\ndef')
        assert "abc" == git.current_commit()
        assert fake_process.calls \
               == deque([['git', 'log', '--oneline', '-n', '1']])
        # Todo: Need to check that cwd was correctly set to something. See
        #       https://github.com/aklajnert/pytest-subprocess/issues/177

    def test_git_current_commit_path(self, fake_process: FakeProcess):
        """
        Tests discover revision of the current working copy at path.

        This test mocks the subprocess for speed and portability. Validation
        when actually shelling out to a subprocess happens in system testing.
        """
        git = Git()
        fake_process.register(['git', 'log', '--oneline', '-n', '1'], stdout='abc\ndef')
        assert "abc" == git.current_commit("/not-exist")
        assert fake_process.calls \
               == deque([['git', 'log', '--oneline', '-n', '1']])
        # Todo: Need to check that cwd was correctly set to /not-exist. See
        #       https://github.com/aklajnert/pytest-subprocess/issues/177

    def test_git_init(self, mock_process: FakeProcess):
        """
        Tests Git initialisation functionality.

        This test mocks the subprocess for speed and portability. Validation
        when actually shelling out to a subprocess happens in system testing.
        """
        git = Git()
        git.init("/src")
        assert mock_process.calls == deque([['git', 'init', '.']])
        # Todo: Need to check that cwd was correctly set to /src. See
        #       https://github.com/aklajnert/pytest-subprocess/issues/177

    def test_git_clean(self, mock_process: FakeProcess):
        """
        Tests Git clean functionality.

        This test mocks the subprocess for speed and portability. Validation
        when actually shelling out to a subprocess happens in system testing.
        """
        git = Git()
        git.clean('/src')
        assert mock_process.calls == deque([['git', 'clean', '-f']])
        # Todo: Need to check that cwd was correctly set to /src. See
        #       https://github.com/aklajnert/pytest-subprocess/issues/177

    def test_git_fetch(self, mock_process: FakeProcess):
        """
        Tests Git fetch functionality.

        This test mocks the subprocess for speed and portability. Validation
        when actually shelling out to a subprocess happens in system testing.
        """
        git = Git()
        git.fetch("/src", "/dst", revision="revision")
        assert mock_process.calls == deque([['git', 'fetch', '/src', 'revision']])
        # Todo: Need to check that cwd was correctly set to /dst. See
        #       https://github.com/aklajnert/pytest-subprocess/issues/177

    def test_git_checkout(self, mock_process: FakeProcess):
        """
        Tests Git branch check-out functionality.

        This test mocks the subprocess for speed and portability. Validation
        when actually shelling out to a subprocess happens in system testing.
        """
        git = Git()
        git.checkout("/src", "/dst", revision="revision")
        assert mock_process.calls == deque(
            [
                ['git', 'fetch', '/src', 'revision'],
                ['git', 'checkout', 'FETCH_HEAD']
            ]
        )
        # Todo: Need to check that cwd was correctly set to /dst. See
        #       https://github.com/aklajnert/pytest-subprocess/issues/177

    def test_git_merge(self, mock_process: FakeProcess):
        """
        Tests Git merge functionality.

        This test mocks the subprocess for speed and portability. Validation
        when actually shelling out to a subprocess happens in system testing.
        """
        git = Git()
        git.merge("/dst", revision="revision")
        assert mock_process.calls == deque([['git', 'merge', 'FETCH_HEAD']])
        # Todo: Need to check that cwd was correctly set to /dst. See
        #       https://github.com/aklajnert/pytest-subprocess/issues/177

    def test_git_merge_fail(self, fake_process: FakeProcess):
        """
        Tests Git merge functionality with merge failure.

        This test mocks the subprocess for speed and portability. Validation
        when actually shelling out to a subprocess happens in system testing.
        """
        git = Git()
        foo = fake_process.register(['git', 'merge', 'FETCH_HEAD'], returncode=1)
        fake_process.register(['git', 'merge', '--abort'], returncode=0)
        with raises(RuntimeError) as err:
            git.merge("/dst", revision="revision")
        assert err.value.args[0].split('\n') \
               == ["Error merging revision. Merge aborted.",
                   "Command failed with return code 1:",
                   "git merge FETCH_HEAD"]
        assert fake_process.calls == deque(
            [
                ['git', 'merge', 'FETCH_HEAD'],
                ['git', 'merge', '--abort']
            ]
        )
        # Todo: Need to check that cwd was correctly set to /dst. See
        #       https://github.com/aklajnert/pytest-subprocess/issues/177

    def test_git_merge_abort_fail(self, fake_process: FakeProcess):
        """
        Tests Git merge functionality when merge fails followed by abort
        failure as well.

        This test mocks the subprocess for speed and portability. Validation
        when actually shelling out to a subprocess happens in system testing.
        """
        git = Git()
        foo = fake_process.register(['git', 'merge', 'FETCH_HEAD'], returncode=1)
        fake_process.register(['git', 'merge', '--abort'], returncode=2)
        with raises(RuntimeError) as err:
            git.merge("/dst", revision="revision")
        assert err.value.args[0].split('\n') \
               == ["Command failed with return code 2:",
                   "git merge --abort"]
        # Todo: Need to check that cwd was correctly set to /dst. See
        #       https://github.com/aklajnert/pytest-subprocess/issues/177


# ============================================================================
class TestSubversion:
    """
    Tests the Subversion interface.
    """
    def test_svn_constructor(self):
        """
        Tests the constructor.
        """
        svn = Subversion()
        assert svn.category == Category.SUBVERSION
        assert svn.flags == []
        assert svn.name == "Subversion"
        assert svn.executable == Path("svn")

    def test_svn_export_revision(self, mock_process):
        """
        Tests Subversion source tree export functionality.

        This test mocks the subprocess for speed and portability. Validation
        when actually shelling out to a subprocess happens in system testing.
        """
        svn = Subversion()
        svn.export("/src", "/dst", revision="123")
        assert mock_process.calls == deque([['svn', 'export', '--force',
                                             '--revision', '123',
                                             '/src', '/dst']])

    def test_svn_export_head(self, mock_process):
        """
        Tests Subversion source tree export functionality.

        This test mocks the subprocess for speed and portability. Validation
        when actually shelling out to a subprocess happens in system testing.
        """
        svn = Subversion()
        svn.export("/src", "/dst")
        assert mock_process.calls == deque([['svn', 'export', '--force',
                                             '/src', '/dst']])

    def test_svn_checkout_revision(self, mock_process):
        """
        Tests Subversion working copy check-out functionality.

        This test mocks the subprocess for speed and portability. Validation
        when actually shelling out to a subprocess happens in system testing.
        """
        svn = Subversion()
        svn.checkout("/src", "/dst", revision="123")
        assert mock_process.calls == deque([['svn', 'checkout',
                                             '--revision', '123',
                                             '/src', '/dst']])

    def test_svn_checkout_head(self, mock_process):
        """
        Tests Subversion working copy check-out functionality.

        This test mocks the subprocess for speed and portability. Validation
        when actually shelling out to a subprocess happens in system testing.
        """
        svn = Subversion()
        svn.checkout("/src", "/dst")
        assert mock_process.calls == deque([['svn', 'checkout',
                                             '/src', '/dst']])

    def test_svn_update(self, mock_process):
        """
        Tests Subversion working copy update functionality.

        This test mocks the subprocess for speed and portability. Validation
        when actually shelling out to a subprocess happens in system testing.
        """
        svn = Subversion()
        svn.update("/dst", revision="123")
        assert mock_process.calls == deque([['svn', 'update',
                                             '--revision', '123', '/dst']])

    def test_svn_merge(self, mock_process):
        """
        Tests Subversion merge functionality.

        This test mocks the subprocess for speed and portability. Validation
        when actually shelling out to a subprocess happens in system testing.
        """
        svn = Subversion()
        svn.merge("/src", "/dst", "123")
        assert mock_process.calls == deque([['svn', 'merge',
                                             '--non-interactive', '/src@123']])
        # Todo: Need to check that cwd was correctly set to /dst. See
        #       https://github.com/aklajnert/pytest-subprocess/issues/177


def _tree_compare(first: Path, second: Path) -> None:
    """
    Compare two file trees to ensure they are identical.
    """
    tree_comparison = dircmp(str(first), str(second))
    assert len(tree_comparison.left_only) == 0 \
        and len(tree_comparison.right_only) == 0
    _, mismatch, errors = cmpfiles(str(first), str(second),
                                   tree_comparison.common_files,
                                   shallow=False)
    assert len(mismatch) == 0 and len(errors) == 0


@mark.skipif(which('svn') is None,
             reason="No Subversion executable found on path.")
class TestSubversionReal:
    """
    Tests the Subversion interface against a real executable.
    """
    @fixture(scope='class')
    def repo(self, tmp_path_factory: TempPathFactory) -> Tuple[Path, Path]:
        """
        Set up a repository and return its path along with the path of the
        original file tree.
        """
        repo_path = tmp_path_factory.mktemp('repo', numbered=True)
        command = ['svnadmin', 'create', str(repo_path)]
        assert run(command).returncode == 0
        tree_path = tmp_path_factory.mktemp('tree', numbered=True)
        (tree_path / 'alpha').write_text("First file")
        (tree_path / 'beta').mkdir()
        (tree_path / 'beta' / 'gamma').write_text("Second file")
        command = ['svn', 'import', '-m', "Initial import",
                   str(tree_path), f'file://{repo_path}/trunk']
        assert run(command).returncode == 0
        return repo_path, tree_path

    def test_extract_from_file(self, repo: Tuple[Path, Path], tmp_path: Path):
        """
        Checks that a source tree can be extracted from a Subversion
        repository stored on disc.
        """
        test_unit = Subversion()
        test_unit.export(f'file://{repo[0]}/trunk', tmp_path)
        _tree_compare(repo[1], tmp_path)
        assert not (tmp_path / '.svn').exists()

    def test_extract_from_svn(self, repo: Tuple[Path, Path], tmp_path: Path):
        """
        Checks that a source tree can be extracted from a Subversion
        repository accessed through its own protocol.
        """
        command: List[str] = ['svnserve', '-r', str(repo[0]), '-X']
        process = Popen(command)

        test_unit = Subversion()
        #
        # It seems there can be a delay between the server starting and the
        # listen socket opening. Thus we have a number of retries.
        #
        # TODO: Is there a better solution such that we don't try to connect
        #       until the socket is open?
        #
        for retry in range(3, 0, -1):
            try:
                test_unit.export('svn://localhost/trunk', tmp_path)
            except Exception as ex:
                if range == 0:
                    raise ex
                sleep(1.0)
            else:
                break
        _tree_compare(repo[1], tmp_path)
        assert not (tmp_path / '.svn').exists()

        process.wait(timeout=1)
        assert process.returncode == 0

    @mark.skip(reason="Too hard to test at the moment.")
    def test_extract_from_http(self, repo: Tuple[Path, Path], tmp_path: Path):
        """
        Checks that a source tree can be extracted from a Subversion
        repository accessed through HTTP.

        TODO: This is hard to test without a full Apache installation. For the
              moment we forgo the test on the basis that it's too hard.
        """
        pass


# ============================================================================
class TestFcm:
    """
    Tests the FCM interface task.
    """
    def test_fcm_constructor(self):
        """
        Tests this constructor.
        """
        fcm = Fcm()
        assert fcm.category == Category.FCM
        assert fcm.flags == []
        assert fcm.name == "FCM"
        assert fcm.executable == Path("fcm")
