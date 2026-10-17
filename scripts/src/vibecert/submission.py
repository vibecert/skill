import datetime
import pathlib
import re

from pydantic import ValidationError

from vibecert.account import Account
from vibecert.certificate import Certificate
from vibecert.certificate_types import CertificateDocument
from vibecert.ownership import Ownership
from vibecert.site import SiteAddress


class Submission:
    """A pull request to the shared site, checked before it is merged.

    Args:
        changed (list[str]): The paths the pull request changes.
        root (pathlib.Path): A checkout holding the submitted files.
        submitter (int): The numeric GitHub id of the pull request's author.
        site (str): The address the shared site is served from.

    """

    PATH: re.Pattern[str] = re.compile(r"(?P<identifier>[0-9a-f]{7})/score\.json")
    AGE: datetime.timedelta = datetime.timedelta(days=30)

    def __init__(
        self, changed: list[str], root: pathlib.Path, submitter: int, site: str
    ) -> None:
        self.__changed: list[str] = changed
        self.__root: pathlib.Path = root
        self.__submitter: int = submitter
        self.__site: str = site

    def get_problems(self) -> list[str]:
        """Return every reason the submission cannot be accepted.

        Returns:
            list[str]: One line per problem, or none where it can be merged.

        """
        if (problem := self._path()) is not None:
            return [problem]
        text: str | None = self._read(self.__root / self.__changed[0])
        if text is None:
            return [f"{self.__changed[0]} is not a regular file"]
        try:
            document: CertificateDocument = CertificateDocument.model_validate_json(
                text
            )
        except ValidationError as error:
            return [f"{self.__changed[0]} is not a certificate: {error}"]
        return [
            problem
            for problem in (
                self._age(),
                self._schema(document),
                self._identifier(document),
                self._address(document),
                self._certified(document),
                self._private(document),
                self._owner(document),
            )
            if problem is not None
        ]

    def _path(self) -> str | None:
        if len(self.__changed) == 1 and Submission.PATH.fullmatch(self.__changed[0]):
            return None
        return "a submission changes exactly one path, <identifier>/score.json"

    def _read(self, path: pathlib.Path) -> str | None:
        return path.read_text() if path.is_file() and not path.is_symlink() else None

    def _age(self) -> str | None:
        if Account(self.__submitter).get_age() >= Submission.AGE:
            return None
        return f"accounts under {Submission.AGE.days} days old cannot submit"

    def _schema(self, document: CertificateDocument) -> str | None:
        if document.schema_version == Certificate.SCHEMA:
            return None
        return f"schema {document.schema_version} is not {Certificate.SCHEMA}"

    def _identifier(self, document: CertificateDocument) -> str | None:
        if self.__changed[0] == document.identifier + "/score.json":
            return None
        return f"identifier {document.identifier} does not match its directory"

    def _address(self, document: CertificateDocument) -> str | None:
        if document.site == self.__site:
            return None
        return f"site {document.site} is not {self.__site}"

    def _certified(self, document: CertificateDocument) -> str | None:
        return None if document.certified else "the certificate is not certified"

    def _private(self, document: CertificateDocument) -> str | None:
        if not document.private or (
            document.repository is None and document.branch is None
        ):
            return None
        return "a private certificate names its repository or branch"

    def _owner(self, document: CertificateDocument) -> str | None:
        if Ownership(SiteAddress.repository(self.__site)).permits(
            document.identifier, self.__submitter
        ):
            return None
        return f"certificate {document.identifier} belongs to another user"
