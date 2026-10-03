import pathlib

import pytest
import pytest_mock

from vibecert.guidelines import GuidelineIndex

PYTHON_RULE: str = (
    '---\npaths:\n  - "**/*.py"\n  - "**/pyproject.toml"\n---\n\n# Python\n'
)
GIT_RULE: str = "# Commit messages\n\n- Use Angular conventions\n"


class TestGuidelineIndex:
    @pytest.fixture
    def index(self) -> GuidelineIndex:
        return GuidelineIndex(pathlib.Path("/repo"), pathlib.Path("/rules"))

    def test_get_available_rules_and_repository_files_returns_both(
        self, index: GuidelineIndex, mocker: pytest_mock.MockerFixture
    ) -> None:
        mocker.patch.object(pathlib.Path, "is_dir", return_value=True)
        mocker.patch.object(
            pathlib.Path,
            "rglob",
            side_effect=lambda pattern: (
                [pathlib.Path("/rules/python/FOO.md")]
                if pattern == "*.md"
                else [pathlib.Path("/repo/CLAUDE.md")]
                if pattern == "CLAUDE.md"
                else []
            ),
        )
        assert index.get_available() == [
            pathlib.Path("/repo/CLAUDE.md"),
            pathlib.Path("/rules/python/FOO.md"),
        ]

    def test_get_applicable_matching_path_glob_returns_rule(
        self, index: GuidelineIndex, mocker: pytest_mock.MockerFixture
    ) -> None:
        mocker.patch.object(
            GuidelineIndex, "get_available", return_value=[pathlib.Path("/rules/py.md")]
        )
        mocker.patch.object(GuidelineIndex, "_read", return_value=PYTHON_RULE)
        assert index.get_applicable(["src/foo.py"]) == [pathlib.Path("/rules/py.md")]

    def test_get_applicable_non_matching_path_glob_excludes_rule(
        self, index: GuidelineIndex, mocker: pytest_mock.MockerFixture
    ) -> None:
        mocker.patch.object(
            GuidelineIndex, "get_available", return_value=[pathlib.Path("/rules/py.md")]
        )
        mocker.patch.object(GuidelineIndex, "_read", return_value=PYTHON_RULE)
        assert index.get_applicable(["README.md"]) == []

    def test_get_applicable_rule_without_paths_applies_always(
        self, index: GuidelineIndex, mocker: pytest_mock.MockerFixture
    ) -> None:
        mocker.patch.object(
            GuidelineIndex,
            "get_available",
            return_value=[pathlib.Path("/rules/git.md")],
        )
        mocker.patch.object(GuidelineIndex, "_read", return_value=GIT_RULE)
        assert index.get_applicable(["README.md"]) == [pathlib.Path("/rules/git.md")]

    def test_read_unreadable_file_returns_empty(self) -> None:
        assert GuidelineIndex._read(pathlib.Path("/no/such/rule.md")) == ""
