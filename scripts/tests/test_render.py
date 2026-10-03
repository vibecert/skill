from tests.conftest import evidence_of, file_of
from vibecert.certificate import Certificate
from vibecert.render import CertificateMarkdown
from vibecert.vibecert_types import Band


def rendered(touched: int = 100) -> str:
    bundle = evidence_of([file_of("foo.py", ".py", 100, code=100)])
    bundle.diff.changed = 100
    bundle.attribution.touched = 100
    bundle.attribution.touched_proportion = touched / 100
    return CertificateMarkdown(
        Certificate(
            bundle, [Band("follow_up_questions", 3, None, "specific questions")]
        )
    ).render()


class TestCertificateMarkdown:
    def test_render_certified_branch_leads_with_the_score(self) -> None:
        assert rendered().splitlines()[2].endswith("/3**")

    def test_render_below_the_gate_says_so_instead_of_scoring(self) -> None:
        assert "Not certified" in rendered(10)

    def test_render_unscored_metric_shows_as_not_applicable(self) -> None:
        assert "| n/a | n/a |" in rendered()

    def test_render_reports_each_weight(self) -> None:
        assert "criticality" in rendered() and "risk" in rendered()

    def test_render_names_the_branch_and_its_size(self) -> None:
        assert "`feat/foo`, 0 commits, 100 changed lines" in rendered()
