import pytest
import pytest_mock

from tests.conftest import evidence_of, file_of
from vibecert.bundle_types import CommitInfo, Evidence
from vibecert.certificate import Certificate, CertificateIdentifier
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

    def test_get_document_branch_with_commits_records_newest_as_head(self) -> None:
        bundle = _bundle()
        bundle.branch.commits = [
            CommitInfo(sha="foo1", timestamp="2026-01-01", subject="a"),
            CommitInfo(sha="bar2", timestamp="2026-01-02", subject="b"),
        ]
        assert Certificate(bundle, JUDGED).get_document().head == "bar2"

    def test_get_document_empty_branch_records_merge_base_as_head(self) -> None:
        assert certificate().get_document().head == "abc123"

    @pytest.mark.parametrize("uncommitted", [True, False])
    def test_get_document_records_uncommitted_state(self, uncommitted: bool) -> None:
        bundle = _bundle()
        bundle.branch.includes_uncommitted = uncommitted
        assert Certificate(bundle, JUDGED).get_document().uncommitted is uncommitted

    def test_get_identifier_delegates_to_certificate_identifier(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        mocker.patch.object(CertificateIdentifier, "of", return_value="foo1234")
        assert certificate().get_identifier() == "foo1234"

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


class TestCertificateIdentifier:
    def test_of_same_inputs_is_stable(self) -> None:
        assert CertificateIdentifier.of("foo", "feat/bar", "abc123") == (
            CertificateIdentifier.of("foo", "feat/bar", "abc123")
        )

    @pytest.mark.parametrize(
        ("remote", "branch", "merge_base"),
        [
            ("baz", "feat/bar", "abc123"),
            ("foo", "feat/baz", "abc123"),
            ("foo", "feat/bar", "def456"),
        ],
    )
    def test_of_different_input_differs(
        self, remote: str, branch: str, merge_base: str
    ) -> None:
        assert CertificateIdentifier.of(remote, branch, merge_base) != (
            CertificateIdentifier.of("foo", "feat/bar", "abc123")
        )

    @pytest.mark.parametrize(
        "remote",
        [
            "git@github.com:Foo/bar.git",
            "https://github.com/foo/bar",
            "https://github.com/foo/bar.git",
            "ssh://git@github.com/foo/bar.git",
            "https://x-access-token@github.com/foo/bar/",
        ],
    )
    def test_of_github_remote_forms_share_one_identifier(self, remote: str) -> None:
        assert CertificateIdentifier.of(remote, "feat/baz", "abc123") == (
            CertificateIdentifier.of("github.com/foo/bar", "feat/baz", "abc123")
        )

    def test_of_other_remote_is_used_as_given(self) -> None:
        assert CertificateIdentifier.of("/repo", "feat/baz", "abc123") != (
            CertificateIdentifier.of("/Repo", "feat/baz", "abc123")
        )

    def test_of_returns_seven_characters(self) -> None:
        assert len(CertificateIdentifier.of("foo", "feat/bar", "abc123")) == 7
