import pytest

from vibecert.detection import (
    CheckRegistry,
    ImportPatterns,
    Languages,
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
