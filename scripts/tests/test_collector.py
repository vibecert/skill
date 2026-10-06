import pathlib
import unittest.mock

import pytest
import pytest_mock

from vibecert.collector import EvidenceCollector
from vibecert.git_repository import GitRepository
from vibecert.transcript import TranscriptStore
from vibecert.vibecert_types import EditHunk


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
        assert collector.collect().schema_version == EvidenceCollector.SCHEMA

    def test_collect_branch_evidence_returns_diff_totals(
        self, collector: EvidenceCollector
    ) -> None:
        assert collector.collect().diff.added == 2

    def test_collect_no_sessions_returns_zero_activity(
        self, collector: EvidenceCollector
    ) -> None:
        assert collector.collect().activity.human_messages == 0

    def test_collect_edits_in_another_repository_returns_only_own_lines(
        self, collector: EvidenceCollector, mocker: pytest_mock.MockerFixture
    ) -> None:
        session: unittest.mock.MagicMock = mocker.MagicMock()
        session.get_edits.return_value = [
            EditHunk("foo", "2026-01-02", "bash", "/repo/foo.py", ["alpha"], 0, ""),
            EditHunk("foo", "2026-01-02", "bash", "/other/foo.py", ["beta"], 0, ""),
        ]
        session.get_prompts.return_value = []
        session.get_tool_counts.return_value = {}
        session.get_bash_commands.return_value = []
        session.get_guidelines_in_context.return_value = set()
        session.get_guidelines_read.return_value = set()
        session.get_span.return_value = ("2026-01-02", "2026-01-03")
        session.get_identifier.return_value = "foo"
        session.get_path.return_value = pathlib.Path("/projects/foo.jsonl")
        mocker.patch.object(TranscriptStore, "find_sessions", return_value=[session])
        assert collector.collect().attribution.generated == 1

    def test_existing_missing_paths_returns_only_real_files(self) -> None:
        assert (
            EvidenceCollector._existing({"/no/such/rules.md"}, pathlib.Path("/repo"))
            == []
        )
