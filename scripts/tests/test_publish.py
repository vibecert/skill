import json
import pathlib

import pytest

from tests.conftest import certificate_document
from vibecert.publish import CertificateSite


class TestCertificateSite:
    @pytest.mark.parametrize(
        "score,message,colour",
        [
            (2.8, "2.8/3", "brightgreen"),
            (2.5, "2.5/3", "brightgreen"),
            (2.1, "2.1/3", "yellow"),
            (1.4, "1.4/3", "orange"),
            (None, "not certified", "lightgrey"),
        ],
    )
    def test_get_badge_score_returns_endpoint_response(
        self, score: float | None, message: str, colour: str
    ) -> None:
        badge = CertificateSite(
            certificate_document(score=score), pathlib.Path("/site")
        ).get_badge()
        assert (badge["schemaVersion"], badge["message"], badge["color"]) == (
            1,
            message,
            colour,
        )

    def test_get_url_host_returns_certificate_address(self) -> None:
        assert CertificateSite(certificate_document(), pathlib.Path("/site")).get_url(
            "https://vibecert.github.io"
        ) == ("https://vibecert.github.io/abc1234")

    def test_write_certificate_writes_three_files(self, tmp_path: pathlib.Path) -> None:
        written = CertificateSite(certificate_document(), tmp_path).write()
        assert sorted(path.name for path in written.iterdir()) == [
            "badge.json",
            "index.html",
            "score.json",
        ]

    def test_write_certificate_uses_the_identifier_as_its_directory(
        self, tmp_path: pathlib.Path
    ) -> None:
        assert CertificateSite(certificate_document(), tmp_path).write().name == (
            "abc1234"
        )

    def test_write_score_is_the_document_verbatim(self, tmp_path: pathlib.Path) -> None:
        CertificateSite(certificate_document(), tmp_path).write()
        assert (
            json.loads((tmp_path / "abc1234" / "score.json").read_text())["identifier"]
            == "abc1234"
        )

    def test_write_index_creates_the_site_root_page(
        self, tmp_path: pathlib.Path
    ) -> None:
        assert (
            CertificateSite(certificate_document(), tmp_path).write_index().name
            == "index.html"
        )

    def test_write_index_leaves_certificates_untouched(
        self, tmp_path: pathlib.Path
    ) -> None:
        site = CertificateSite(certificate_document(), tmp_path)
        site.write()
        site.write_index()
        assert (tmp_path / "abc1234" / "index.html").exists()
