import urllib.error
import urllib.request

from vibecert.certificate import CertificateIdentifier
from vibecert.certificate_types import CertificateDocument
from vibecert.git_repository import GitRepository


class Verification:
    """A consumer's check that a branch carries a current, passing certificate.

    Args:
        repository (GitRepository): The checkout of the branch under review.
        branch (str): The branch's name, which a detached checkout cannot report.
        base (str): The branch it will merge into.
        site (str): The address certificates are served from.
        threshold (float): The lowest score that passes.

    """

    def __init__(
        self,
        repository: GitRepository,
        branch: str,
        base: str,
        site: str,
        threshold: float,
    ) -> None:
        self.__repository: GitRepository = repository
        self.__branch: str = branch
        self.__base: str = base
        self.__site: str = site
        self.__threshold: float = threshold

    def get_identifier(self) -> str:
        """Return the identifier the branch's certificate is published under.

        Returns:
            str: Seven characters, computed from Git alone.

        """
        return CertificateIdentifier.of(
            self.__repository.get_remote() or str(self.__repository.get_root()),
            self.__branch,
            self.__repository.get_merge_base(self.__base),
        )

    def get_problems(self) -> list[str]:
        """Return every reason the branch's certificate does not pass.

        Returns:
            list[str]: One line per problem, or none where it passes.

        """
        address: str = f"{self.__site}/{self.get_identifier()}/score.json"
        text: str | None = self._fetch(address)
        if text is None:
            return [f"no certificate at {address}"]
        document: CertificateDocument = CertificateDocument.model_validate_json(text)
        return [
            problem
            for problem in (
                None if document.certified else "the certificate is not certified",
                f"score {document.score} is below {self.__threshold}"
                if document.score is not None and document.score < self.__threshold
                else None,
                None
                if document.head == self.__repository.get_head()
                else f"the certificate covers {document.head[:7]}, not HEAD",
            )
            if problem is not None
        ]

    def _fetch(self, address: str) -> str | None:
        try:
            with urllib.request.urlopen(address) as response:
                return response.read().decode()
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            raise
