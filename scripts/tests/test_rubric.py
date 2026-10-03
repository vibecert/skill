import pytest

from vibecert.rubric import CheckRegistry, Languages


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
