from tests.conftest import certificate_document
from vibecert.page import CertificatePage, SiteIndex, Stylesheet


class TestCertificatePage:
    def test_render_certified_branch_shows_the_score(self) -> None:
        assert (
            '<p class="score">2.0<small>/3</small></p>'
            in CertificatePage(certificate_document(score=2.0)).render()
        )

    def test_render_below_the_gate_says_not_certified(self) -> None:
        assert (
            "Not certified"
            in CertificatePage(certificate_document(score=None)).render()
        )

    def test_render_partial_coverage_states_it(self) -> None:
        assert (
            "only 3 of 5 metrics"
            in CertificatePage(certificate_document(scored=3, applicable=5)).render()
        )

    def test_render_public_repository_names_it(self) -> None:
        assert "<code>repo</code>" in CertificatePage(certificate_document()).render()

    def test_render_private_repository_withholds_names(self) -> None:
        page = CertificatePage(certificate_document(private=True)).render()
        assert "A private repository" in page and "feat/foo" not in page

    def test_render_escapes_evidence(self) -> None:
        assert (
            "&lt;script&gt;"
            in CertificatePage(
                certificate_document(evidence="<script>alert(1)</script>")
            ).render()
        )

    def test_render_findings_present_lists_them(self) -> None:
        assert (
            "S603"
            in CertificatePage(
                certificate_document(findings=["S603: subprocess call"])
            ).render()
        )

    def test_render_no_findings_omits_the_panel(self) -> None:
        assert (
            "Security findings" not in CertificatePage(certificate_document()).render()
        )

    def test_render_carries_the_explanation_link(self) -> None:
        assert CertificatePage.ABOUT in CertificatePage(certificate_document()).render()

    def test_render_has_no_external_resources(self) -> None:
        page = CertificatePage(certificate_document()).render()
        assert "<script" not in page and 'rel="stylesheet"' not in page


class TestStylesheet:
    def test_read_returns_the_packaged_stylesheet(self) -> None:
        assert "--paper" in Stylesheet.read()


class TestSiteIndex:
    def test_render_explains_what_a_certificate_is(self) -> None:
        assert "generative tooling" in SiteIndex.render()

    def test_render_states_the_self_assessed_caveat(self) -> None:
        assert "self-assessed" in SiteIndex.render()

    def test_render_says_certificates_are_not_listed(self) -> None:
        assert "not listed" in SiteIndex.render()

    def test_render_links_to_the_explanation(self) -> None:
        assert CertificatePage.ABOUT in SiteIndex.render()

    def test_render_inlines_the_stylesheet(self) -> None:
        assert "--paper" in SiteIndex.render()
