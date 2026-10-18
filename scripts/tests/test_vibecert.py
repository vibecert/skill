import pathlib
import unittest.mock

import pytest
import pytest_mock

from tests.conftest import certificate_document, evidence_of
from vibecert.certificate_types import CertificateDocument
from vibecert.collector import EvidenceCollector
from vibecert.publish import CertificateSite, SiteBuild
from vibecert.render import CertificateMarkdown, VerificationComment
from vibecert.submission import Submission
from vibecert.verification import Verification
from vibecert.vibecert import (
    AcceptCli,
    BuildCli,
    Cli,
    MetricsCli,
    PublishCli,
    ScoreCli,
    VerifyCli,
)


class TestCli:
    def test_emit_no_destination_writes_to_stdout(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        Cli._emit("{}", None)
        assert capsys.readouterr().out.strip() == "{}"

    def test_emit_destination_given_writes_to_file(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        write_text: unittest.mock.MagicMock = mocker.patch.object(
            pathlib.Path, "write_text"
        )
        Cli._emit("{}", "/out/bundle.json")
        write_text.assert_called_once_with("{}")

    def test_parser_defaults_returns_current_directory(self) -> None:
        assert Cli._parser().parse_args([]).repo == "."


class TestMetricsCli:
    def test_load_matching_schema_returns_evidence(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        mocker.patch.object(
            pathlib.Path,
            "read_text",
            return_value=evidence_of([]).model_dump_json(),
        )
        assert MetricsCli._load(pathlib.Path("/bundle.json")).schema_version == (
            EvidenceCollector.SCHEMA
        )

    def test_load_unknown_schema_raises(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        bundle = evidence_of([])
        bundle.schema_version = "vibecert/evidence@99"
        mocker.patch.object(
            pathlib.Path, "read_text", return_value=bundle.model_dump_json()
        )
        with pytest.raises(ValueError):
            MetricsCli._load(pathlib.Path("/bundle.json"))

    def test_parser_bundle_argument_returns_path(self) -> None:
        assert MetricsCli._parser().parse_args(["/bundle.json"]).bundle == (
            "/bundle.json"
        )


class TestScoreCli:
    def test_judged_bands_file_returns_bands(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        mocker.patch.object(
            pathlib.Path,
            "read_text",
            return_value='[{"metric": "follow_up_questions", "score": 3, '
            '"evidence": "specific questions"}]',
        )
        assert ScoreCli._judged(pathlib.Path("/judged.json"))[0].score == 3

    def test_judged_null_score_returns_none(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        mocker.patch.object(
            pathlib.Path,
            "read_text",
            return_value='[{"metric": "coding_guidelines", "score": null, '
            '"evidence": "nothing applies"}]',
        )
        assert ScoreCli._judged(pathlib.Path("/judged.json"))[0].score is None

    def test_parser_requires_bundle_and_judged(self) -> None:
        assert ScoreCli._parser().parse_args(["/b.json", "/j.json"]).judged == (
            "/j.json"
        )


class TestPublishCli:
    def test_run_certificate_without_an_address_refuses(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        document = certificate_document()
        document.site = ""
        mocker.patch.object(
            pathlib.Path, "read_text", return_value=document.model_dump_json()
        )
        mocker.patch.object(
            PublishCli,
            "_parser",
            return_value=mocker.MagicMock(
                parse_args=lambda: mocker.MagicMock(certificate="/c.json", site="/site")
            ),
        )
        with pytest.raises(ValueError):
            PublishCli.run()

    def test_run_uncertified_certificate_refuses_with_the_reason(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        mocker.patch.object(
            pathlib.Path,
            "read_text",
            return_value=certificate_document(None).model_dump_json(),
        )
        mocker.patch.object(
            PublishCli,
            "_parser",
            return_value=mocker.MagicMock(
                parse_args=lambda: mocker.MagicMock(certificate="/c.json", site="/site")
            ),
        )
        with pytest.raises(ValueError, match=CertificateMarkdown.UNCERTIFIED):
            PublishCli.run()

    def test_run_certified_certificate_writes_it(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        mocker.patch.object(
            pathlib.Path,
            "read_text",
            return_value=certificate_document().model_dump_json(),
        )
        mocker.patch.object(
            PublishCli,
            "_parser",
            return_value=mocker.MagicMock(
                parse_args=lambda: mocker.MagicMock(certificate="/c.json", site="/site")
            ),
        )
        write: unittest.mock.MagicMock = mocker.patch.object(
            CertificateSite, "write", return_value=pathlib.Path("/site/abc1234")
        )
        PublishCli.run()
        write.assert_called_once_with()


class TestAcceptCli:
    @pytest.fixture
    def arguments(self, mocker: pytest_mock.MockerFixture) -> None:
        mocker.patch.object(
            AcceptCli,
            "_parser",
            return_value=mocker.MagicMock(
                parse_args=lambda: mocker.MagicMock(
                    submission="/pull",
                    submitter=1,
                    changed=["abc1234/score.json"],
                    site_url="https://foo.github.io",
                )
            ),
        )

    def test_run_clean_submission_prints_the_identifier(
        self,
        arguments: unittest.mock.MagicMock,
        mocker: pytest_mock.MockerFixture,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mocker.patch.object(Submission, "get_problems", return_value=[])
        AcceptCli.run()
        assert capsys.readouterr().out.strip() == "identifier: abc1234"

    def test_run_problems_found_exits_with_them(
        self, arguments: unittest.mock.MagicMock, mocker: pytest_mock.MockerFixture
    ) -> None:
        mocker.patch.object(Submission, "get_problems", return_value=["foo", "bar"])
        with pytest.raises(SystemExit, match="foo\nbar"):
            AcceptCli.run()

    def test_parser_repeated_changed_returns_every_path(self) -> None:
        assert AcceptCli._parser().parse_args(
            [
                "/pull",
                "--submitter",
                "1",
                "--site-url",
                "https://foo.github.io",
                "--changed",
                "abc1234/score.json",
                "def5678/score.json",
            ]
        ).changed == ["abc1234/score.json", "def5678/score.json"]


class TestBuildCli:
    def test_run_built_site_prints_every_file(
        self, mocker: pytest_mock.MockerFixture, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mocker.patch.object(
            BuildCli,
            "_parser",
            return_value=mocker.MagicMock(
                parse_args=lambda: mocker.MagicMock(source="/source", out="/out")
            ),
        )
        mocker.patch.object(
            SiteBuild,
            "build",
            return_value=[pathlib.Path("/out/abc1234/index.html")],
        )
        BuildCli.run()
        assert capsys.readouterr().out.strip() == "/out/abc1234/index.html"


class TestVerifyCli:
    @pytest.fixture
    def arguments(self, mocker: pytest_mock.MockerFixture) -> unittest.mock.MagicMock:
        namespace: unittest.mock.MagicMock = mocker.MagicMock(
            repo="/repo",
            branch="feat/foo",
            base="origin/main",
            site_url="https://foo.github.io",
            threshold=2.0,
            comment=False,
        )
        mocker.patch.object(
            VerifyCli,
            "_parser",
            return_value=mocker.MagicMock(parse_args=lambda: namespace),
        )
        return namespace

    def test_run_passing_certificate_prints_the_identifier(
        self,
        arguments: unittest.mock.MagicMock,
        mocker: pytest_mock.MockerFixture,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mocker.patch.object(Verification, "get_problems", return_value=[])
        mocker.patch.object(Verification, "get_identifier", return_value="abc1234")
        VerifyCli.run()
        assert capsys.readouterr().out.strip() == "identifier: abc1234"

    def test_run_problems_found_exits_with_them(
        self, arguments: unittest.mock.MagicMock, mocker: pytest_mock.MockerFixture
    ) -> None:
        mocker.patch.object(Verification, "get_problems", return_value=["foo", "bar"])
        with pytest.raises(SystemExit, match="foo\nbar"):
            VerifyCli.run()

    @pytest.mark.parametrize(
        "document,problems", [(certificate_document(), ["foo"]), (None, [])]
    )
    def test_run_comment_requested_prints_the_comment(
        self,
        arguments: unittest.mock.MagicMock,
        mocker: pytest_mock.MockerFixture,
        capsys: pytest.CaptureFixture[str],
        document: CertificateDocument | None,
        problems: list[str],
    ) -> None:
        arguments.comment = True
        mocker.patch.object(Verification, "get_document", return_value=document)
        mocker.patch.object(Verification, "assess", return_value=["foo"])
        mocker.patch.object(Verification, "is_generated", return_value=True)
        init: unittest.mock.MagicMock = mocker.patch.object(
            VerificationComment, "__init__", return_value=None
        )
        mocker.patch.object(VerificationComment, "render", return_value="bar")
        VerifyCli.run()
        init.assert_called_once_with(document, problems, True)
        assert capsys.readouterr().out.strip() == "bar"

    def test_run_empty_comment_prints_nothing(
        self,
        arguments: unittest.mock.MagicMock,
        mocker: pytest_mock.MockerFixture,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        arguments.comment = True
        mocker.patch.object(Verification, "get_document", return_value=None)
        mocker.patch.object(Verification, "is_generated", return_value=False)
        mocker.patch.object(VerificationComment, "render", return_value="")
        VerifyCli.run()
        assert capsys.readouterr().out == ""

    def test_parser_branch_given_returns_defaults(self) -> None:
        assert (
            VerifyCli._parser()
            .parse_args(["--branch", "feat/foo", "--site-url", "https://foo.github.io"])
            .threshold
            == 0.0
        )
