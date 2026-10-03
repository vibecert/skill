import pathlib

import pytest
import pytest_mock

from vibecert.collector import EvidenceCollector
from vibecert.git_repository import GitRepository
from vibecert.json_values import Json
from vibecert.transcript import TranscriptStore


class TestEvidenceCollector:
    @pytest.fixture
    def collector(
        self, repository: GitRepository, mocker: pytest_mock.MockerFixture
    ) -> EvidenceCollector:
        mocker.patch.object(TranscriptStore, "_all_sessions", return_value=[])
        return EvidenceCollector(
            repository,
            TranscriptStore(pathlib.Path("/projects")),
            "main",
            False,
        )

    def test_collect_branch_evidence_returns_schema(
        self, collector: EvidenceCollector
    ) -> None:
        assert collector.collect()["schema"] == EvidenceCollector.SCHEMA

    def test_collect_branch_evidence_returns_diff_totals(
        self, collector: EvidenceCollector
    ) -> None:
        assert Json.as_dict(collector.collect()["diff"])["added"] == 2

    def test_collect_no_sessions_returns_zero_activity(
        self, collector: EvidenceCollector
    ) -> None:
        assert Json.as_dict(collector.collect()["activity"])["human_messages"] == 0

    def test_existing_missing_paths_returns_only_real_files(self) -> None:
        assert (
            EvidenceCollector._existing({"/no/such/rules.md"}, pathlib.Path("/repo"))
            == []
        )
