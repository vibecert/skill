import dataclasses
import pathlib
import unittest.mock

import pytest
import pytest_mock

from vibecert.bundle_types import (
    ActivityInfo,
    AttributionInfo,
    BranchInfo,
    CheckInfo,
    DiffInfo,
    Evidence,
    FileInfo,
    RepositoryInfo,
    WindowInfo,
)
from vibecert.certificate_types import (
    CertificateDocument,
    MetricResult,
    WeightResult,
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
    checks: CheckInfo | None = None,
    comment_density: float = 0.0,
    fan_in_distribution: list[int] | None = None,
    revised: int = 0,
    revised_proportion: float = 0.0,
) -> Evidence:
    return Evidence(
        schema_version=EvidenceCollector.SCHEMA,
        collected_at="2026-01-01T00:00:00+00:00",
        repository=RepositoryInfo(
            root="/repo",
            name="repo",
            remote="git@github.com:foo/bar.git",
            comment_density=comment_density,
            fan_in_distribution=fan_in_distribution or [],
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
            guidelines=[],
            checks=checks
            or CheckInfo(applicable=[], configured=[], ran=[], configs={}),
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
    fan_in: int = 0,
    risk_signals: list[str] | None = None,
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
        fan_in=fan_in,
        risk_signals=risk_signals or [],
    )


def certificate_document(
    score: float | None = 2.3,
    scored: int = 6,
    applicable: int = 6,
    private: bool = False,
    evidence: str = "specific questions",
    findings: list[str] | None = None,
) -> CertificateDocument:
    return CertificateDocument(
        schema_version="vibecert/certificate@1",
        rubrics_version="vibecert/rubrics@1",
        issued_at="2026-01-01T00:00:00+00:00",
        identifier="abc1234",
        site="https://foo.github.io/vibecert",
        private=private,
        repository=None if private else "repo",
        branch=None if private else "feat/foo",
        commits=3,
        changed_lines=400,
        generative_proportion=0.99,
        certified=score is not None,
        score=score,
        scored=scored,
        applicable=applicable,
        weights=WeightResult(length=2, criticality=3, risk=1, applied=3),
        metrics=[
            MetricResult(
                number=1,
                name="follow_up_questions",
                title="Follow-up questions",
                state="scored",
                raw=3,
                adjusted=3,
                evidence=evidence,
            )
        ],
        findings=findings or [],
    )
