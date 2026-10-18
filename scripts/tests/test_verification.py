import dataclasses
import pathlib
import unittest.mock

import pytest
import pytest_mock

from tests.conftest import certificate_document
from vibecert.certificate import CertificateIdentifier
from vibecert.git_repository import GitRepository
from vibecert.verification import Verification


@dataclasses.dataclass
class VerificationMocks:
    of: unittest.mock.MagicMock
    get_remote: unittest.mock.MagicMock
    get_merge_base: unittest.mock.MagicMock
    get_head: unittest.mock.MagicMock
    get_messages: unittest.mock.MagicMock
    _fetch: unittest.mock.MagicMock


@pytest.fixture
def verification_mocks(mocker: pytest_mock.MockerFixture) -> VerificationMocks:
    return VerificationMocks(
        mocker.patch.object(CertificateIdentifier, "of", return_value="abc1234"),
        mocker.patch.object(
            GitRepository, "get_remote", return_value="git@github.com:foo/bar.git"
        ),
        mocker.patch.object(GitRepository, "get_merge_base", return_value="abc123"),
        mocker.patch.object(GitRepository, "get_head", return_value="bar1234"),
        mocker.patch.object(GitRepository, "get_messages", return_value=["feat: foo"]),
        mocker.patch.object(
            Verification,
            "_fetch",
            return_value=certificate_document().model_dump_json(),
        ),
    )


@pytest.fixture
def verification() -> Verification:
    return Verification(
        GitRepository(pathlib.Path("/repo")),
        "feat/foo",
        "origin/main",
        "https://foo.github.io",
        2.0,
    )


class TestVerification:
    def test_get_identifier_branch_returns_identifier_from_git(
        self, verification: Verification, verification_mocks: VerificationMocks
    ) -> None:
        assert verification.get_identifier() == "abc1234"
        verification_mocks.of.assert_called_once_with(
            "git@github.com:foo/bar.git", "feat/foo", "abc123"
        )

    def test_get_identifier_no_remote_uses_the_root(
        self, verification: Verification, verification_mocks: VerificationMocks
    ) -> None:
        verification_mocks.get_remote.return_value = ""
        verification.get_identifier()
        verification_mocks.of.assert_called_once_with("/repo", "feat/foo", "abc123")

    def test_get_problems_current_passing_certificate_returns_none(
        self, verification: Verification, verification_mocks: VerificationMocks
    ) -> None:
        assert verification.get_problems() == []

    def test_get_problems_missing_certificate_returns_its_address(
        self, verification: Verification, verification_mocks: VerificationMocks
    ) -> None:
        verification_mocks._fetch.return_value = None
        assert verification.get_problems() == [
            "no certificate at https://foo.github.io/abc1234/score.json"
        ]

    def test_get_problems_legacy_certificate_returns_too_old(
        self, verification: Verification, verification_mocks: VerificationMocks
    ) -> None:
        verification_mocks._fetch.return_value = (
            '{"schema_version": "vibecert/certificate@1"}'
        )
        assert verification.get_problems() == [
            "the certificate uses vibecert/certificate@1, too old to verify; rescore it"
        ]

    def test_get_document_current_certificate_returns_it(
        self, verification: Verification, verification_mocks: VerificationMocks
    ) -> None:
        assert verification.get_document() == certificate_document()

    @pytest.mark.parametrize(
        "text", [None, '{"schema_version": "vibecert/certificate@1"}']
    )
    def test_get_document_missing_or_legacy_returns_none(
        self,
        verification: Verification,
        verification_mocks: VerificationMocks,
        text: str | None,
    ) -> None:
        verification_mocks._fetch.return_value = text
        assert verification.get_document() is None

    def test_assess_stale_head_returns_head_problem(
        self, verification: Verification, verification_mocks: VerificationMocks
    ) -> None:
        verification_mocks.get_head.return_value = "def5678"
        assert verification.assess(certificate_document()) == [
            "the certificate covers bar1234, not HEAD"
        ]

    def test_assess_below_threshold_returns_score_problem(
        self, verification: Verification, verification_mocks: VerificationMocks
    ) -> None:
        assert verification.assess(certificate_document(1.5)) == [
            "score 1.5 is below 2.0"
        ]

    def test_assess_uncertified_returns_certification_problem(
        self, verification: Verification, verification_mocks: VerificationMocks
    ) -> None:
        assert verification.assess(certificate_document(None)) == [
            "the certificate is not certified"
        ]

    @pytest.mark.parametrize(
        "messages,expected",
        [
            (["feat: foo\n\nCo-Authored-By: Claude <noreply@anthropic.com>"], True),
            (["feat: foo", "fix: bar"], False),
        ],
    )
    def test_is_generated_commit_messages_returns_whether_tool_credited(
        self,
        verification: Verification,
        verification_mocks: VerificationMocks,
        messages: list[str],
        expected: bool,
    ) -> None:
        verification_mocks.get_messages.return_value = messages
        assert verification.is_generated() is expected
        verification_mocks.get_messages.assert_called_once_with("abc123")
