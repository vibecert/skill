import pytest

from vibecert.detection import (
    CheckRegistry,
    ImportPatterns,
    Languages,
    RiskSeverity,
    SensitiveData,
)


class TestSensitiveData:
    @pytest.mark.parametrize(
        "line,expected",
        [
            ("patient_record = load()", ["personal data referenced"]),
            ("nhs_number = read()", ["personal data referenced"]),
            ("total = one + two", []),
        ],
    )
    def test_scan_added_lines_returns_category_when_named(
        self, line: str, expected: list[str]
    ) -> None:
        assert SensitiveData.scan([line]) == expected


class TestImportPatterns:
    def test_get_pattern_known_suffix_returns_expression(self) -> None:
        assert ImportPatterns.get_pattern(".py", "foo") is not None

    def test_get_pattern_unknown_suffix_returns_none(self) -> None:
        assert ImportPatterns.get_pattern(".md", "foo") is None


class TestLanguages:
    @pytest.mark.parametrize(
        "suffix,expected", [(".py", "#"), (".ts", "//"), (".sql", "--"), (".md", "")]
    )
    def test_get_marker_file_suffix_returns_marker_or_empty(
        self, suffix: str, expected: str
    ) -> None:
        assert Languages.get_marker(suffix) == expected


class TestCheckRegistry:
    @pytest.mark.parametrize(
        "name,content,expected",
        [
            ("pytest.ini", "", ["behavioural"]),
            ("pyproject.toml", "[tool.pytest.ini_options]", ["behavioural"]),
            ("pyproject.toml", "[tool.ruff.lint]", ["static", "format"]),
            ("pyproject.toml", "[project]", []),
            (".markdownlint.json", "{}", ["static"]),
            ("README.md", "", []),
        ],
    )
    def test_configured_by_file_contents_returns_classes_it_establishes(
        self, name: str, content: str, expected: list[str]
    ) -> None:
        assert CheckRegistry.configured_by(name, content) == expected


class TestRiskSeverity:
    @pytest.mark.parametrize(
        "findings,expected",
        [
            ([], False),
            (["S113: requests call without timeout"], False),
            (["S101: assert detected"], False),
            (["S602: subprocess call with shell=True"], True),
            (["S105: possible hardcoded password"], True),
            (["S608: possible SQL injection"], True),
            (["personal data referenced"], True),
            (["S113: no timeout", "S607: partial executable path"], True),
        ],
    )
    def test_is_severe_findings_reports_whether_any_can_do_harm(
        self, findings: list[str], expected: bool
    ) -> None:
        assert RiskSeverity.is_severe(findings) is expected
