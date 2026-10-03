import dataclasses
import pathlib
import unittest.mock

import pytest
import pytest_mock

from vibecert.git_repository import GitRepository


@dataclasses.dataclass
class GitMocks:
    _run: unittest.mock.MagicMock


GIT_OUTPUT: dict[str, str] = {
    "rev-parse": "feat/foo/add-bar",
    "merge-base": "abc123",
    "log": (
        "sha2\x1f2026-01-02T00:00:00+00:00\x1ffix: bar\n"
        "sha1\x1f2026-01-01T00:00:00+00:00\x1ffeat: foo"
    ),
    "diff": "+++ b/foo.py\n@@ -1,0 +1,2 @@\n+alpha\n+beta\n-gamma\n",
    "ls-files": "",
    "remote": "git@github.com:foo/bar.git",
    "status": "",
    "show": "2026-01-01T00:00:00+00:00",
}


@pytest.fixture
def git_mocks(mocker: pytest_mock.MockerFixture) -> GitMocks:
    return GitMocks(
        mocker.patch.object(
            GitRepository,
            "_run",
            side_effect=lambda *arguments: GIT_OUTPUT.get(arguments[0], ""),
        )
    )


@pytest.fixture
def repository(git_mocks: GitMocks) -> GitRepository:
    return GitRepository(pathlib.Path("/repo"))
