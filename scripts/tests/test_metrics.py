import pytest

from tests.conftest import evidence_of, file_of
from vibecert.metrics import (
    AmendmentMetric,
    CommentMetric,
    DeterministicMetrics,
    SecondaryToolMetric,
)


class TestAmendmentMetric:
    @pytest.mark.parametrize("rate,expected", [(0.02, 1), (0.10, 2), (0.40, 3)])
    def test_get_band_revision_rate_returns_banded_score(
        self, rate: float, expected: int
    ) -> None:
        assert (
            AmendmentMetric(
                evidence_of(
                    [file_of("foo.py", ".py", 100)],
                    revised=int(rate * 100),
                    revised_proportion=rate,
                )
            )
            .get_band()
            .score
            == expected
        )

    def test_get_band_formatter_rewrite_excluded_by_collection(self) -> None:
        assert (
            AmendmentMetric(evidence_of([file_of("foo.py", ".py", 100)], revised=0))
            .get_band()
            .score
            == 1
        )

    def test_get_band_no_generated_files_returns_not_applicable(self) -> None:
        assert AmendmentMetric(evidence_of([])).get_band().score is None


class TestSecondaryToolMetric:
    def test_get_band_highest_class_configured_and_ran_returns_three(self) -> None:
        assert (
            SecondaryToolMetric(
                evidence_of(
                    [file_of("foo.py", ".py", 10)],
                    ["uv run pytest -q"],
                    {"pyproject.toml": ["behavioural"]},
                )
            )
            .get_band()
            .score
            == 3
        )

    def test_get_band_highest_class_configured_not_run_returns_two(self) -> None:
        assert (
            SecondaryToolMetric(
                evidence_of(
                    [file_of("foo.py", ".py", 10)],
                    ["ls"],
                    {"pyproject.toml": ["behavioural"]},
                )
            )
            .get_band()
            .score
            == 2
        )

    def test_get_band_only_lower_class_ran_returns_two(self) -> None:
        assert (
            SecondaryToolMetric(
                evidence_of([file_of("foo.py", ".py", 10)], ["ruff check ."], {})
            )
            .get_band()
            .score
            == 2
        )

    def test_get_band_nothing_configured_or_run_returns_one(self) -> None:
        assert (
            SecondaryToolMetric(evidence_of([file_of("foo.py", ".py", 10)]))
            .get_band()
            .score
            == 1
        )

    def test_get_band_markdown_linter_ran_returns_three(self) -> None:
        assert (
            SecondaryToolMetric(
                evidence_of(
                    [file_of("foo.md", ".md", 10)],
                    ["markdownlint foo.md"],
                    {".markdownlint.json": ["static"]},
                )
            )
            .get_band()
            .score
            == 3
        )

    def test_get_band_no_class_applies_returns_not_applicable(self) -> None:
        assert (
            SecondaryToolMetric(
                evidence_of([file_of("foo.excalidraw", ".excalidraw", 10)])
            )
            .get_band()
            .score
            is None
        )


class TestCommentMetric:
    @pytest.mark.parametrize("comments,expected", [(5, 3), (15, 2), (25, 1)])
    def test_get_band_comment_density_returns_inverted_score(
        self, comments: int, expected: int
    ) -> None:
        assert (
            CommentMetric(
                evidence_of([file_of("foo.py", ".py", 100, 0, True, comments, 100)])
            )
            .get_band()
            .score
            == expected
        )

    def test_get_band_repository_baseline_higher_scores_against_baseline(self) -> None:
        assert (
            CommentMetric(
                evidence_of(
                    [file_of("foo.py", ".py", 100, 0, True, 15, 100)],
                    comment_density=0.25,
                )
            )
            .get_band()
            .score
            == 3
        )

    def test_get_band_markup_only_returns_not_applicable(self) -> None:
        assert (
            CommentMetric(evidence_of([file_of("foo.md", ".md", 10)])).get_band().score
            is None
        )


class TestDeterministicMetrics:
    def test_get_bands_evidence_bundle_returns_three_metrics_in_order(self) -> None:
        assert [
            band.metric
            for band in DeterministicMetrics(
                evidence_of([file_of("foo.py", ".py", 10)])
            ).get_bands()
        ] == ["output_amendments", "secondary_tools", "generative_comments"]
