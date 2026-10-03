import json
import pathlib

from vibecert.certificate_types import CertificateDocument
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
        """Write the page, the machine-readable score and the badge.

        Returns:
            pathlib.Path: The directory the three files were written to.

        """
        self._directory().mkdir(parents=True, exist_ok=True)
        (self._directory() / "index.html").write_text(
            CertificatePage(self.__document).render()
        )
        (self._directory() / "score.json").write_text(
            self.__document.model_dump_json(indent=1)
        )
        (self._directory() / "badge.json").write_text(
            json.dumps(self.get_badge(), indent=1)
        )
        return self._directory()

    def write_index(self) -> pathlib.Path:
        """Write the page served at the root of the site.

        Returns:
            pathlib.Path: The file written.

        """
        self.__root.mkdir(parents=True, exist_ok=True)
        (self.__root / "index.html").write_text(SiteIndex.render())
        return self.__root / "index.html"

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

    def get_url(self, host: str) -> str:
        """Return the address this certificate will be served from.

        Args:
            host (str): The site's base address, without a trailing slash.

        Returns:
            str: The certificate's address.

        """
        return f"{host}/{self.__document.identifier}"

    def _colour(self) -> str:
        if self.__document.score is None:
            return "lightgrey"
        return next(
            colour for floor, colour in self.COLOURS if self.__document.score >= floor
        )

    def _directory(self) -> pathlib.Path:
        return self.__root / self.__document.identifier
