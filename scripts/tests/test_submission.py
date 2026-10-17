import dataclasses
import pathlib
import unittest.mock

import pytest
import pytest_mock

from tests.conftest import certificate_document
from vibecert.certificate_types import CertificateDocument
from vibecert.ownership import Ownership
from vibecert.submission import Submission

SITE: str = "https://foo.github.io/vibecert"
PATH: str = "abc1234/score.json"


class SubmissionFixture(Submission):
    def read(self, path: pathlib.Path) -> str | None:
        return self._read(path)


@dataclasses.dataclass
class SubmissionMocks:
    _read: unittest.mock.MagicMock
    permits: unittest.mock.MagicMock


@pytest.fixture
def submission_mocks(mocker: pytest_mock.MockerFixture) -> SubmissionMocks:
    return SubmissionMocks(
        mocker.patch.object(
            Submission,
            "_read",
            return_value=certificate_document().model_dump_json(),
        ),
        mocker.patch.object(Ownership, "permits", return_value=True),
    )


class TestSubmission:
    def test_get_problems_clean_submission_returns_none(
        self, submission_mocks: SubmissionMocks
    ) -> None:
        assert Submission([PATH], pathlib.Path("/site"), 1, SITE).get_problems() == []

    @pytest.mark.parametrize(
        "changed",
        [[], [PATH, "def5678/score.json"], ["abc1234/index.html"], ["foo/score.json"]],
    )
    def test_get_problems_wrong_paths_returns_path_problem(
        self, submission_mocks: SubmissionMocks, changed: list[str]
    ) -> None:
        assert Submission(changed, pathlib.Path("/site"), 1, SITE).get_problems() == [
            "a submission changes exactly one path, <identifier>/score.json"
        ]

    def test_get_problems_not_a_regular_file_returns_file_problem(
        self, submission_mocks: SubmissionMocks
    ) -> None:
        submission_mocks._read.return_value = None
        assert Submission([PATH], pathlib.Path("/site"), 1, SITE).get_problems() == [
            f"{PATH} is not a regular file"
        ]

    def test_get_problems_invalid_document_returns_validation_problem(
        self, submission_mocks: SubmissionMocks
    ) -> None:
        submission_mocks._read.return_value = "{}"
        assert (
            Submission([PATH], pathlib.Path("/site"), 1, SITE)
            .get_problems()[0]
            .startswith(f"{PATH} is not a certificate")
        )

    @pytest.mark.parametrize(
        ("document", "problem"),
        [
            (
                certificate_document().model_copy(
                    update={"schema_version": "vibecert/certificate@1"}
                ),
                "schema vibecert/certificate@1 is not vibecert/certificate@2",
            ),
            (
                certificate_document().model_copy(update={"identifier": "def5678"}),
                "identifier def5678 does not match its directory",
            ),
            (
                certificate_document().model_copy(
                    update={"site": "https://bar.github.io/vibecert"}
                ),
                f"site https://bar.github.io/vibecert is not {SITE}",
            ),
            (certificate_document(None), "the certificate is not certified"),
            (
                certificate_document().model_copy(update={"private": True}),
                "a private certificate names its repository or branch",
            ),
        ],
        ids=["schema", "identifier", "site", "certified", "private"],
    )
    def test_get_problems_failing_check_returns_its_problem(
        self,
        submission_mocks: SubmissionMocks,
        document: CertificateDocument,
        problem: str,
    ) -> None:
        submission_mocks._read.return_value = document.model_dump_json()
        assert Submission([PATH], pathlib.Path("/site"), 1, SITE).get_problems() == [
            problem
        ]

    def test_get_problems_identifier_owned_by_another_returns_owner_problem(
        self, submission_mocks: SubmissionMocks
    ) -> None:
        submission_mocks.permits.return_value = False
        assert Submission([PATH], pathlib.Path("/site"), 1, SITE).get_problems() == [
            "certificate abc1234 belongs to another user"
        ]

    def test_get_problems_redacted_private_certificate_returns_none(
        self, submission_mocks: SubmissionMocks
    ) -> None:
        submission_mocks._read.return_value = certificate_document(
            private=True
        ).model_dump_json()
        assert Submission([PATH], pathlib.Path("/site"), 1, SITE).get_problems() == []


class TestSubmissionRead:
    @pytest.mark.parametrize(
        ("is_file", "is_symlink", "expected"),
        [(True, False, "foo"), (False, False, None), (True, True, None)],
    )
    def test_read_regular_file_only_returns_its_text(
        self,
        mocker: pytest_mock.MockerFixture,
        is_file: bool,
        is_symlink: bool,
        expected: str | None,
    ) -> None:
        mocker.patch.object(pathlib.Path, "is_file", return_value=is_file)
        mocker.patch.object(pathlib.Path, "is_symlink", return_value=is_symlink)
        mocker.patch.object(pathlib.Path, "read_text", return_value="foo")
        assert (
            SubmissionFixture([PATH], pathlib.Path("/site"), 1, SITE).read(
                pathlib.Path("/site/" + PATH)
            )
            == expected
        )
