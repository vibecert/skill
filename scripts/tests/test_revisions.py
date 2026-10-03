from vibecert.revisions import RevisionCounter
from vibecert.vibecert_types import EditHunk, Prompt


def edit(timestamp: str, path: str, lines: int, command: str = "") -> EditHunk:
    return EditHunk("session", timestamp, "bash", path, ["x"] * lines, 0, command)


class TestRevisionCounter:
    def test_count_first_write_of_file_is_not_a_revision(self) -> None:
        assert (
            RevisionCounter([edit("02", "foo.py", 10)], [Prompt("s", "01", "")]).count()
            == 0
        )

    def test_count_rewrite_after_human_message_counts(self) -> None:
        assert (
            RevisionCounter(
                [edit("01", "foo.py", 10), edit("03", "foo.py", 4)],
                [Prompt("s", "02", "why line 41?")],
            ).count()
            == 4
        )

    def test_count_rewrite_without_human_message_does_not_count(self) -> None:
        assert (
            RevisionCounter(
                [edit("01", "foo.py", 10), edit("02", "foo.py", 4)],
                [Prompt("s", "03", "later")],
            ).count()
            == 0
        )

    def test_count_formatter_rewrite_does_not_count(self) -> None:
        assert (
            RevisionCounter(
                [
                    edit("01", "foo.py", 10),
                    edit("03", "foo.py", 9, "uv run ruff format ."),
                ],
                [Prompt("s", "02", "tidy it")],
            ).count()
            == 0
        )

    def test_count_rewrite_of_other_file_counted_independently(self) -> None:
        assert (
            RevisionCounter(
                [
                    edit("01", "foo.py", 10),
                    edit("03", "bar.py", 7),
                    edit("05", "foo.py", 2),
                ],
                [Prompt("s", "02", "a"), Prompt("s", "04", "b")],
            ).count()
            == 2
        )
