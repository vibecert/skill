import pytest

from vibecert.comments import CommentCounter


class TestCommentCounter:
    @pytest.mark.parametrize(
        "suffix,lines,expected",
        [
            (".py", ["# note", "foo = 1", "", "  # indented"], (2, 1)),
            (".ts", ["// note", "const foo = 1;"], (1, 1)),
            (".sql", ["-- note", "SELECT 1"], (1, 1)),
            (".md", ["# heading", "text"], (0, 0)),
            (".json", ["{}"], (0, 0)),
            (".py", [], (0, 0)),
        ],
    )
    def test_count_added_lines_returns_comment_and_code_counts(
        self, suffix: str, lines: list[str], expected: tuple[int, int]
    ) -> None:
        assert CommentCounter.count(lines, suffix) == expected

    def test_count_docstring_body_counts_as_code(self) -> None:
        assert CommentCounter.count(['"""Summary."""', "foo = 1"], ".py") == (0, 2)
