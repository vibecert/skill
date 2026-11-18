import pathlib
import unittest.mock

import pytest
import pytest_mock

from vibecert.collector import EvidenceCollector
from vibecert.git_repository import GitRepository
from vibecert.guidelines import GuidelineIndex
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

    def test_collect_base_merged_after_commits_starts_window_at_first_commit(
        self, collector: EvidenceCollector, mocker: pytest_mock.MockerFixture
    ) -> None:
        mocker.patch.object(
            GitRepository, "get_commit_time", return_value="2026-01-03T00:00:00+00:00"
        )
        assert collector.collect().branch.window.start == "2026-01-01T00:00:00+00:00"

    @pytest.mark.parametrize(
        "created,expected",
        [
            ("2025-12-31T00:00:00+00:00", "2025-12-31T00:00:00+00:00"),
            ("2026-01-02T00:00:00+00:00", "2026-01-01T00:00:00+00:00"),
        ],
    )
    def test_collect_branch_creation_recorded_starts_window_at_earliest(
        self,
        collector: EvidenceCollector,
        mocker: pytest_mock.MockerFixture,
        created: str,
        expected: str,
    ) -> None:
        mocker.patch.object(GitRepository, "get_branch_created", return_value=created)
        get_commit_time: unittest.mock.MagicMock = mocker.patch.object(
            GitRepository, "get_commit_time", return_value="2025-01-01T00:00:00+00:00"
        )
        assert collector.collect().branch.window.start == expected
        get_commit_time.assert_not_called()

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

    def test_invocations_make_command_returns_command_and_recipe(
        self, collector: EvidenceCollector, mocker: pytest_mock.MockerFixture
    ) -> None:
        mocker.patch.object(
            GitRepository, "read_lines", return_value=["test:", "\tshunit2 foo.sh"]
        )
        session: unittest.mock.MagicMock = mocker.MagicMock()
        session.get_bash_commands.return_value = ["make test"]
        assert collector._invocations([session]) == ["make test", "shunit2 foo.sh"]

    @pytest.mark.parametrize(
        "config,changed,expected",
        [
            (".github/workflows/ci.yml", ["foo.sh"], True),
            ("Makefile", ["foo.sh"], True),
            ("tools/Makefile", ["foo.sh"], False),
            ("tools/Makefile", ["tools/foo.sh"], True),
        ],
    )
    def test_governs_config_location_reports_whether_it_covers_changes(
        self, config: str, changed: list[str], expected: bool
    ) -> None:
        assert EvidenceCollector._governs(config, changed) is expected

    def test_existing_missing_paths_returns_only_real_files(self) -> None:
        assert (
            EvidenceCollector._existing({"/no/such/rules.md"}, pathlib.Path("/repo"))
            == []
        )

    def test_existing_path_through_symlink_returns_resolved_path(
        self, tmp_path: pathlib.Path
    ) -> None:
        (tmp_path / "rules").mkdir()
        (tmp_path / "rules" / "FOO.md").write_text("foo")
        (tmp_path / "link").symlink_to(tmp_path / "rules")
        assert EvidenceCollector._existing(
            {str(tmp_path / "link" / "FOO.md")}, tmp_path
        ) == [str(tmp_path / "rules" / "FOO.md")]

    def test_guideline_info_guideline_listed_through_symlink_reports_in_context(
        self,
        collector: EvidenceCollector,
        mocker: pytest_mock.MockerFixture,
        tmp_path: pathlib.Path,
    ) -> None:
        (tmp_path / "rules").mkdir()
        (tmp_path / "rules" / "FOO.md").write_text("foo")
        (tmp_path / "link").symlink_to(tmp_path / "rules")
        mocker.patch.object(
            GuidelineIndex, "get_available", return_value=[tmp_path / "link" / "FOO.md"]
        )
        mocker.patch.object(GuidelineIndex, "get_applicable", return_value=[])
        session: unittest.mock.MagicMock = mocker.MagicMock()
        session.get_guidelines_in_context.return_value = {
            str(tmp_path / "rules" / "FOO.md")
        }
        session.get_guidelines_read.return_value = set()
        assert [
            guideline.in_context
            for guideline in collector._guideline_info([session], ["foo.py"])
        ] == [True]
