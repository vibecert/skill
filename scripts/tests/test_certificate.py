import pytest

from tests.conftest import evidence_of, file_of
from vibecert.certificate import Certificate
from vibecert.vibecert_types import Band

JUDGED: list[Band] = [
    Band("follow_up_questions", 3, None, "specific questions"),
    Band("coding_guidelines", 2, None, "partial compliance"),
    Band("prompt_granularity", 3, None, "scoped requests"),
]


def certificate(changed: int = 100, fan_in: int = 0, touched: int = 100) -> Certificate:
    bundle = evidence_of([file_of("foo.py", ".py", 100, fan_in=fan_in, code=100)])
    bundle.diff.changed = changed
    bundle.attribution.touched = 100
    bundle.attribution.touched_proportion = touched / 100
    return Certificate(bundle, JUDGED)


class TestCertificate:
    def test_get_metrics_rubric_order_returns_six(self) -> None:
        assert [metric.number for metric in certificate().get_metrics()] == [
            1,
            2,
            3,
            4,
            5,
            6,
        ]

    def test_get_metrics_low_weight_raises_a_shortfall(self) -> None:
        assert [
            metric.adjusted
            for metric in certificate().get_metrics()
            if metric.number == 2
        ] == [3]

    def test_get_metrics_high_weight_lowers_a_middling_band(self) -> None:
        assert [
            metric.adjusted
            for metric in certificate(fan_in=9).get_metrics()
            if metric.number == 2
        ] == [1]

    def test_get_metrics_unscored_metric_stays_none(self) -> None:
        assert any(metric.adjusted is None for metric in certificate().get_metrics())

    def test_get_score_applicable_metrics_returns_mean(self) -> None:
        assert certificate().get_score() == pytest.approx(2.8, abs=0.3)

    def test_get_score_below_the_gate_returns_none(self) -> None:
        assert certificate(touched=10).get_score() is None

    def test_is_certifiable_below_the_gate_reports_false(self) -> None:
        assert certificate(touched=10).is_certifiable() is False
