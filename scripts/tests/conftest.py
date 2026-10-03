import dataclasses
import pathlib
import unittest.mock

import pytest
import pytest_mock

from vibecert.bundle_types import (
    ActivityInfo,
    AttributionInfo,
    BranchInfo,
    DiffInfo,
    Evidence,
    FileInfo,
    RepositoryInfo,
    WindowInfo,
)
from vibecert.collector import EvidenceCollector
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


def evidence_of(
    files: list[FileInfo],
    bash_commands: list[str] | None = None,
    check_configs: dict[str, list[str]] | None = None,
    comment_density: float = 0.0,
    revised: int = 0,
    revised_proportion: float = 0.0,
) -> Evidence:
    return Evidence(
        schema_version=EvidenceCollector.SCHEMA,
        collected_at="2026-01-01T00:00:00+00:00",
        repository=RepositoryInfo(
            root="/repo", name="repo", remote="", comment_density=comment_density
        ),
        branch=BranchInfo(
            name="feat/foo",
            base="main",
            merge_base="abc123",
            commits=[],
            includes_uncommitted=False,
            window=WindowInfo(start="2026-01-01", end="2026-01-02"),
        ),
        diff=DiffInfo(
            files=files,
            added=sum(file.added for file in files),
            removed=0,
            changed=sum(file.added for file in files),
        ),
        sessions=[],
        prompts=[],
        attribution=AttributionInfo(
            added=sum(file.added for file in files),
            generated=0,
            human=0,
            generative_proportion=0.0,
            touched=sum(file.added for file in files if file.touched),
            touched_proportion=0.0,
            revised=revised,
            revised_proportion=revised_proportion,
        ),
        activity=ActivityInfo(
            human_messages=0,
            tool_counts={},
            bash_commands=bash_commands or [],
            guidelines_in_context=[],
            check_configs=check_configs or {},
        ),
    )


def file_of(
    path: str,
    suffix: str,
    added: int = 0,
    human: int = 0,
    touched: bool = True,
    comments: int = 0,
    code: int = 0,
) -> FileInfo:
    return FileInfo(
        path=path,
        suffix=suffix,
        added=added,
        removed=0,
        generated=added - human,
        human=human,
        touched=touched,
        comments=comments,
        code=code,
    )
