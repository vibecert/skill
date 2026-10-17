import json
import pathlib

import pytest
from pydantic import ValidationError

from tests.conftest import certificate_document
from vibecert.certificate_types import CertificateDocument
from vibecert.publish import CertificateSite, SiteBuild


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

    def test_write_certificate_writes_the_score_only(
        self, tmp_path: pathlib.Path
    ) -> None:
        written = CertificateSite(certificate_document(), tmp_path).write()
        assert [path.name for path in written.iterdir()] == ["score.json"]

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

    def test_write_page_leaves_the_score_unwritten(
        self, tmp_path: pathlib.Path
    ) -> None:
        written = CertificateSite(certificate_document(), tmp_path).write_page()
        assert sorted(path.name for path in written.iterdir()) == [
            "badge.json",
            "index.html",
        ]


class TestSiteBuild:
    @staticmethod
    def submit(source: pathlib.Path, document: CertificateDocument) -> str:
        (source / document.identifier).mkdir(parents=True)
        (source / document.identifier / "score.json").write_text(
            document.model_dump_json()
        )
        return document.model_dump_json()

    def test_build_two_certificates_writes_six_files_and_the_root(
        self, tmp_path: pathlib.Path
    ) -> None:
        TestSiteBuild.submit(tmp_path / "source", certificate_document())
        TestSiteBuild.submit(
            tmp_path / "source",
            certificate_document().model_copy(update={"identifier": "def5678"}),
        )
        assert [
            str(path.relative_to(tmp_path / "out"))
            for path in SiteBuild(tmp_path / "source", tmp_path / "out").build()
        ] == [
            "abc1234/index.html",
            "abc1234/score.json",
            "abc1234/badge.json",
            "def5678/index.html",
            "def5678/score.json",
            "def5678/badge.json",
            "index.html",
        ]

    def test_build_score_is_served_byte_identical(self, tmp_path: pathlib.Path) -> None:
        submitted = TestSiteBuild.submit(tmp_path / "source", certificate_document())
        SiteBuild(tmp_path / "source", tmp_path / "out").build()
        assert (tmp_path / "out" / "abc1234" / "score.json").read_text() == submitted

    def test_build_invalid_score_raises(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "source" / "abc1234").mkdir(parents=True)
        (tmp_path / "source" / "abc1234" / "score.json").write_text("{}")
        with pytest.raises(ValidationError):
            SiteBuild(tmp_path / "source", tmp_path / "out").build()

    def test_build_score_under_another_identifier_raises(
        self, tmp_path: pathlib.Path
    ) -> None:
        (tmp_path / "source" / "def5678").mkdir(parents=True)
        (tmp_path / "source" / "def5678" / "score.json").write_text(
            certificate_document().model_dump_json()
        )
        with pytest.raises(ValueError, match="holds certificate abc1234"):
            SiteBuild(tmp_path / "source", tmp_path / "out").build()

    def test_build_legacy_certificate_is_served_as_committed(
        self, tmp_path: pathlib.Path
    ) -> None:
        (tmp_path / "source" / "abc1234").mkdir(parents=True)
        (tmp_path / "source" / "abc1234" / "score.json").write_text(
            '{"schema_version": "vibecert/certificate@1"}'
        )
        (tmp_path / "source" / "abc1234" / "index.html").write_text("<p>foo</p>")
        assert SiteBuild(tmp_path / "source", tmp_path / "out").build()[:2] == [
            tmp_path / "out" / "abc1234" / "index.html",
            tmp_path / "out" / "abc1234" / "score.json",
        ]
        assert (tmp_path / "out" / "abc1234" / "index.html").read_text() == (
            "<p>foo</p>"
        )

    def test_build_no_certificates_writes_the_root_only(
        self, tmp_path: pathlib.Path
    ) -> None:
        (tmp_path / "source").mkdir()
        assert SiteBuild(tmp_path / "source", tmp_path / "out").build() == [
            tmp_path / "out" / "index.html"
        ]
