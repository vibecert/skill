from tests.conftest import certificate_document, evidence_of, file_of
from vibecert.bundle_types import CheckInfo
from vibecert.certificate import Certificate
from vibecert.render import CertificateMarkdown, CertificateSnippets
from vibecert.vibecert_types import Band


def rendered(touched: int = 100, private: bool = False) -> str:
    bundle = evidence_of([file_of("foo.py", ".py", 100, code=100)])
    bundle.diff.changed = 100
    bundle.attribution.touched = 100
    bundle.attribution.touched_proportion = touched / 100
    return CertificateMarkdown(
        Certificate(
            bundle,
            [Band("follow_up_questions", 3, None, "specific questions")],
            private,
        ).get_document()
    ).render()


def complete() -> str:
    bundle = evidence_of([file_of("foo.py", ".py", 100, code=100)])
    bundle.diff.changed = 100
    bundle.attribution.touched = 100
    bundle.attribution.touched_proportion = 1.0
    bundle.activity.checks = CheckInfo(
        applicable=["behavioural"],
        configured=["behavioural"],
        ran=["behavioural"],
        configs={},
    )
    return CertificateMarkdown(
        Certificate(
            bundle,
            [
                Band("follow_up_questions", 3, None, "specific questions"),
                Band("coding_guidelines", 3, None, "complies"),
                Band("prompt_granularity", 3, None, "scoped"),
            ],
        ).get_document()
    ).render()


class TestCertificateMarkdown:
    def test_render_partially_scored_branch_says_how_much_was_scored(self) -> None:
        assert (
            rendered().splitlines()[2].endswith("over only 3 of 5 metrics that apply")
        )

    def test_render_fully_scored_branch_leads_with_the_score_alone(self) -> None:
        assert complete().splitlines()[2].endswith("/3**")

    def test_render_below_the_gate_says_so_instead_of_scoring(self) -> None:
        assert "Not certified" in rendered(10)

    def test_render_metric_with_no_band_shows_as_missing(self) -> None:
        assert "| missing | missing |" in rendered()

    def test_render_metric_that_does_not_apply_shows_as_not_applicable(self) -> None:
        assert "| n/a | n/a |" in rendered()

    def test_render_reports_each_weight(self) -> None:
        assert "criticality" in rendered() and "risk" in rendered()

    def test_render_names_the_branch_and_its_size(self) -> None:
        assert "`feat/foo`, 0 commits, 100 changed lines" in rendered()

    def test_render_private_repository_withholds_its_names(self) -> None:
        assert "A private repository" in rendered(private=True)
        assert "feat/foo" not in rendered(private=True)

    def test_render_reports_the_identifier_and_rubric_version(self) -> None:
        assert "vibecert/rubrics@1" in rendered()


class TestCertificateSnippets:
    def test_get_trailer_certified_names_the_score_and_address(self) -> None:
        assert CertificateSnippets(certificate_document(score=2.3)).get_trailer() == (
            "VibeCert: 2.3/3 (https://foo.github.io/vibecert/abc1234)"
        )

    def test_get_trailer_fits_a_commit_body_line(self) -> None:
        assert len(CertificateSnippets(certificate_document()).get_trailer()) <= 72

    def test_get_trailer_below_the_gate_says_not_certified(self) -> None:
        assert (
            "not certified"
            in CertificateSnippets(certificate_document(score=None)).get_trailer()
        )

    def test_get_summary_carries_a_badge_and_a_sentence(self) -> None:
        summary = CertificateSnippets(certificate_document()).get_summary()
        assert "img.shields.io/endpoint" in summary and "scored 2.3/3" in summary

    def test_get_url_returns_the_published_address(self) -> None:
        assert CertificateSnippets(certificate_document()).get_url() == (
            "https://foo.github.io/vibecert/abc1234"
        )


class TestSharingSection:
    def test_render_offers_a_trailer_to_paste(self) -> None:
        assert "As a commit trailer:" in rendered()

    def test_render_offers_a_pull_request_snippet(self) -> None:
        assert "In a pull request:" in rendered()

    def test_render_without_an_address_says_it_cannot_be_published(self) -> None:
        bundle = evidence_of([file_of("foo.py", ".py", 100, code=100)])
        bundle.repository.remote = "/srv/git/local.git"
        bundle.attribution.touched_proportion = 1.0
        assert (
            "no address"
            in CertificateMarkdown(Certificate(bundle, []).get_document()).render()
        )
