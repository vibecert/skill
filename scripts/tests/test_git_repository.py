import pathlib
import subprocess

import pytest
import pytest_mock

from tests.conftest import GIT_OUTPUT, GitMocks
from vibecert.git_repository import GitRepository
from vibecert.vibecert_types import FileDiff


class TestGitRepository:
    def test_get_root_relative_path_returns_resolved(self) -> None:
        assert GitRepository(pathlib.Path("/repo")).get_root() == pathlib.Path("/repo")

    def test_get_branch_checked_out_returns_name(
        self, repository: GitRepository
    ) -> None:
        assert repository.get_branch() == "feat/foo/add-bar"

    def test_get_head_checked_out_returns_sha(
        self, repository: GitRepository, git_mocks: GitMocks
    ) -> None:
        git_mocks._run.side_effect = lambda *arguments: (
            "def456" if arguments == ("rev-parse", "HEAD") else ""
        )
        assert repository.get_head() == "def456"

    def test_get_merge_base_base_branch_returns_sha(
        self, repository: GitRepository
    ) -> None:
        assert repository.get_merge_base("main") == "abc123"

    def test_get_merge_base_unknown_base_propagates(
        self, repository: GitRepository, git_mocks: GitMocks
    ) -> None:
        git_mocks._run.side_effect = subprocess.CalledProcessError(1, "git")
        with pytest.raises(subprocess.CalledProcessError):
            repository.get_merge_base("main")

    def test_get_commits_branch_commits_returns_oldest_first(
        self, repository: GitRepository
    ) -> None:
        assert [commit.subject for commit in repository.get_commits("abc123")] == [
            "feat: foo",
            "fix: bar",
        ]

    def test_get_diff_tracked_changes_returns_added_and_removed(
        self, repository: GitRepository
    ) -> None:
        assert repository.get_diff("abc123", False) == {
            "foo.py": FileDiff("foo.py", ["alpha", "beta"], 1)
        }

    def test_get_diff_untracked_requested_includes_untracked(
        self,
        repository: GitRepository,
        git_mocks: GitMocks,
        mocker: pytest_mock.MockerFixture,
    ) -> None:
        git_mocks._run.side_effect = lambda *arguments: (
            "new.py" if arguments[0] == "ls-files" else GIT_OUTPUT.get(arguments[0], "")
        )
        mocker.patch.object(GitRepository, "_read_lines", return_value=["delta"])
        assert repository.get_diff("abc123", True)["new.py"].added == ["delta"]

    def test_get_remote_origin_present_returns_url(
        self, repository: GitRepository
    ) -> None:
        assert repository.get_remote() == "git@github.com:foo/bar.git"

    def test_get_commit_time_known_sha_returns_date(
        self, repository: GitRepository
    ) -> None:
        assert repository.get_commit_time("abc123") == "2026-01-01T00:00:00+00:00"

    @pytest.mark.parametrize("status,expected", [("", False), (" M foo.py", True)])
    def test_is_dirty_working_tree_reports_state(
        self,
        repository: GitRepository,
        git_mocks: GitMocks,
        status: str,
        expected: bool,
    ) -> None:
        git_mocks._run.side_effect = lambda *arguments: status
        assert repository.is_dirty() is expected

    def test_get_remote_command_fails_returns_empty(
        self, repository: GitRepository, git_mocks: GitMocks
    ) -> None:
        git_mocks._run.side_effect = subprocess.CalledProcessError(1, "git")
        assert repository.get_remote() == ""

    def test_read_lines_unreadable_path_returns_empty(self) -> None:
        assert GitRepository._read_lines(pathlib.Path("/no/such/file")) == []


class TestGitRepositoryFiles:
    def test_get_tracked_files_repository_files_returns_paths(
        self, repository: GitRepository, git_mocks: GitMocks
    ) -> None:
        git_mocks._run.side_effect = lambda *arguments: "foo.py\nbar.md"
        assert repository.get_tracked_files() == ["foo.py", "bar.md"]

    def test_read_lines_unreadable_path_returns_empty(self) -> None:
        assert GitRepository.read_lines(pathlib.Path("/no/such/file")) == []
