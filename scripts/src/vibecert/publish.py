import json
import pathlib
import shutil

from vibecert.certificate_types import CertificateDocument
from vibecert.json_values import Json
from vibecert.page import CertificatePage, SiteIndex


class CertificateSite:
    """Writes one certificate into the directory a site is served from.

    Args:
        document (CertificateDocument): The scored result for the branch.
        root (pathlib.Path): The directory the site is served from.

    """

    COLOURS: tuple[tuple[float, str], ...] = (
        (2.5, "brightgreen"),
        (2.0, "yellow"),
        (0.0, "orange"),
    )

    def __init__(self, document: CertificateDocument, root: pathlib.Path) -> None:
        self.__document: CertificateDocument = document
        self.__root: pathlib.Path = root

    def write(self) -> pathlib.Path:
        """Write the machine-readable score, the only file a submission holds.

        Returns:
            pathlib.Path: The directory the score was written to.

        """
        self._directory().mkdir(parents=True, exist_ok=True)
        (self._directory() / "score.json").write_text(
            self.__document.model_dump_json(indent=1)
        )
        return self._directory()

    def write_page(self) -> pathlib.Path:
        """Write the page and the badge, which only the site builds.

        Returns:
            pathlib.Path: The directory the two files were written to.

        """
        self._directory().mkdir(parents=True, exist_ok=True)
        (self._directory() / "index.html").write_text(
            CertificatePage(self.__document).render()
        )
        (self._directory() / "badge.json").write_text(
            json.dumps(self.get_badge(), indent=1)
        )
        return self._directory()

    def get_badge(self) -> dict[str, object]:
        """Return the shields.io endpoint response for this certificate.

        Returns:
            dict[str, object]: The badge, as the endpoint schema defines it.

        """
        return {
            "schemaVersion": 1,
            "label": "vibecert",
            "message": "not certified"
            if self.__document.score is None
            else f"{self.__document.score}/3",
            "color": self._colour(),
        }

    def _colour(self) -> str:
        if self.__document.score is None:
            return "lightgrey"
        return next(
            colour for floor, colour in self.COLOURS if self.__document.score >= floor
        )

    def _directory(self) -> pathlib.Path:
        return self.__root / self.__document.identifier


class SiteBuild:
    """Builds the whole site from the scores submitted to it.

    A certificate from before the current schema was pushed with its page and
    badge, and is served as it was committed.

    Args:
        source (pathlib.Path): A checkout holding one score.json per certificate.
        out (pathlib.Path): The directory to build the site into.

    """

    LEGACY: tuple[str, ...] = ("vibecert/certificate@1",)

    def __init__(self, source: pathlib.Path, out: pathlib.Path) -> None:
        self.__source: pathlib.Path = source
        self.__out: pathlib.Path = out

    def build(self) -> list[pathlib.Path]:
        """Write every certificate's page, score and badge, and the root page.

        Returns:
            list[pathlib.Path]: Every file written.

        Raises:
            ValueError: If a score is filed under another certificate's identifier.

        """
        return [
            *(
                path
                for score in sorted(self.__source.glob("*/score.json"))
                for path in self._certificate(score)
            ),
            self._root(),
        ]

    def _certificate(self, score: pathlib.Path) -> list[pathlib.Path]:
        if (
            Json.as_text(
                Json.as_dict(json.loads(score.read_text())).get("schema_version")
            )
            in SiteBuild.LEGACY
        ):
            return self._legacy(score.parent)
        document: CertificateDocument = CertificateDocument.model_validate_json(
            score.read_text()
        )
        if document.identifier != score.parent.name:
            raise ValueError(f"{score} holds certificate {document.identifier}")
        directory: pathlib.Path = CertificateSite(document, self.__out).write_page()
        shutil.copyfile(score, directory / "score.json")
        return [directory / name for name in ("index.html", "score.json", "badge.json")]

    def _legacy(self, directory: pathlib.Path) -> list[pathlib.Path]:
        shutil.copytree(directory, self.__out / directory.name, dirs_exist_ok=True)
        return sorted(
            self.__out / directory.name / path.name for path in directory.iterdir()
        )

    def _root(self) -> pathlib.Path:
        self.__out.mkdir(parents=True, exist_ok=True)
        (self.__out / "index.html").write_text(SiteIndex.render())
        return self.__out / "index.html"
