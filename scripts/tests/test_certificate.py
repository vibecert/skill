import pytest

from tests.conftest import evidence_of, file_of
from vibecert.bundle_types import Evidence
from vibecert.certificate import Certificate
from vibecert.rubric import Thresholds
from vibecert.vibecert_types import Band

JUDGED: list[Band] = [
    Band("follow_up_questions", 3, None, "specific questions"),
    Band("coding_guidelines", 2, None, "partial compliance"),
    Band("prompt_granularity", 3, None, "scoped requests"),
]


def _bundle(
    changed: int = 100,
    fan_in: int = 0,
    touched: int = 100,
    distribution: list[int] | None = None,
) -> Evidence:
    bundle = evidence_of(
        [file_of("foo.py", ".py", 100, fan_in=fan_in, code=100)],
        fan_in_distribution=distribution,
    )
    bundle.diff.changed = changed
    bundle.attribution.touched = 100
    bundle.attribution.touched_proportion = touched / 100
    return bundle


def certificate(
    changed: int = 100,
    fan_in: int = 0,
    touched: int = 100,
    distribution: list[int] | None = None,
) -> Certificate:
    return Certificate(_bundle(changed, fan_in, touched, distribution), JUDGED)


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
            for metric in certificate(fan_in=9, distribution=[0, 1, 2, 9]).get_metrics()
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


class TestCertificateDocument:
    def test_get_document_carries_both_versions(self) -> None:
        document = certificate().get_document()
        assert (document.schema_version, document.rubrics_version) == (
            Certificate.SCHEMA,
            Thresholds.VERSION,
        )

    def test_get_document_public_repository_names_it(self) -> None:
        assert certificate().get_document().repository == "repo"

    def test_get_document_private_repository_withholds_names(self) -> None:
        document = Certificate(_bundle(), JUDGED, True).get_document()
        assert (document.repository, document.branch, document.private) == (
            None,
            None,
            True,
        )

    def test_get_document_private_repository_keeps_the_identifier(self) -> None:
        assert len(Certificate(_bundle(), JUDGED, True).get_document().identifier) == 7

    def test_get_identifier_same_branch_is_stable(self) -> None:
        assert certificate().get_identifier() == certificate().get_identifier()

    def test_get_identifier_different_branch_differs(self) -> None:
        other = _bundle()
        other.branch.name = "feat/bar"
        assert Certificate(other, JUDGED).get_identifier() != (
            certificate().get_identifier()
        )

    def test_get_metrics_scored_metric_reports_scored(self) -> None:
        assert [
            metric.state
            for metric in certificate().get_metrics()
            if metric.name == "follow_up_questions"
        ] == ["scored"]

    def test_get_metrics_metric_with_no_band_reports_not_scored(self) -> None:
        assert [
            metric.state
            for metric in Certificate(_bundle(), []).get_metrics()
            if metric.name == "follow_up_questions"
        ] == ["not_scored"]

    def test_get_metrics_declining_metric_reports_not_applicable(self) -> None:
        assert [
            metric.state
            for metric in Certificate(
                _bundle(), [Band("follow_up_questions", None, None, "nothing to ask")]
            ).get_metrics()
            if metric.name == "follow_up_questions"
        ] == ["not_applicable"]

    def test_get_document_reports_how_much_of_the_rubric_was_scored(self) -> None:
        document = certificate().get_document()
        assert (document.scored, document.applicable) == (5, 5)

    def test_get_document_reports_risk_findings_whatever_the_band(self) -> None:
        bundle = _bundle()
        bundle.diff.files[0].risk_signals = ["S603: subprocess call"]
        assert Certificate(bundle, JUDGED).get_document().findings == [
            "S603: subprocess call"
        ]
