import pathlib
import typing

import pytest

from vibecert.attribution import LineAttribution
from vibecert.vibecert_types import EditHunk, FileDiff


class TestLineAttribution:
    DIFF: typing.ClassVar[dict[str, FileDiff]] = {
        "foo.py": FileDiff("foo.py", ["alpha", "beta", "gamma"], 0),
        "bar.md": FileDiff("bar.md", ["delta"], 0),
    }
    EDITS: typing.ClassVar[list[EditHunk]] = [
        EditHunk("session", "", "bash", "/repo/foo.py", ["alpha", "beta"], 0)
    ]

    @pytest.fixture
    def attribution(self) -> LineAttribution:
        return LineAttribution(self.DIFF, self.EDITS, pathlib.Path("/repo"))

    def test_get_added_branch_diff_returns_total(
        self, attribution: LineAttribution
    ) -> None:
        assert attribution.get_added() == 4

    def test_get_generated_matching_lines_returns_count(
        self, attribution: LineAttribution
    ) -> None:
        assert attribution.get_generated() == 2

    def test_get_human_unmatched_lines_returns_count(
        self, attribution: LineAttribution
    ) -> None:
        assert attribution.get_human() == 2

    def test_get_proportion_lines_present_returns_share(
        self, attribution: LineAttribution
    ) -> None:
        assert attribution.get_proportion() == 0.5

    def test_get_proportion_empty_diff_returns_zero(self) -> None:
        assert LineAttribution({}, [], pathlib.Path("/repo")).get_proportion() == 0.0

    def test_get_touched_file_written_returns_all_its_lines(
        self, attribution: LineAttribution
    ) -> None:
        assert attribution.get_touched() == 3

    def test_get_touched_proportion_lines_present_returns_share(
        self, attribution: LineAttribution
    ) -> None:
        assert attribution.get_touched_proportion() == 0.75

    def test_get_touched_proportion_empty_diff_returns_zero(self) -> None:
        assert (
            LineAttribution({}, [], pathlib.Path("/repo")).get_touched_proportion()
            == 0.0
        )

    def test_get_per_file_mixed_authorship_returns_split(
        self, attribution: LineAttribution
    ) -> None:
        assert attribution.get_per_file()["foo.py"] == {
            "added": 3,
            "generated": 2,
            "human": 1,
            "touched": 1,
        }
