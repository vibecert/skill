import pathlib
import unittest.mock

import pytest
import pytest_mock

from tests.conftest import evidence_of
from vibecert.collector import EvidenceCollector
from vibecert.vibecert import Cli, MetricsCli, ScoreCli


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
