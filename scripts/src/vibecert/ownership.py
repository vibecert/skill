import json
import os
import urllib.request

from vibecert.json_values import Json


class Ownership:
    """Who may replace a certificate on the shared site.

    The owner is whoever opened the merged pull request that first added the
    certificate. Nothing stores this, so it holds only while the site's main
    branch changes through accepted pull requests alone.

    Args:
        repository (str): The site's repository, as owner and name.

    """

    API: str = "https://api.github.com/"
    PAGE: int = 100

    def __init__(self, repository: str) -> None:
        self.__repository: str = repository

    def get_owner(self, identifier: str) -> int | None:
        """Return the GitHub user who first published a certificate.

        Args:
            identifier (str): The certificate's identifier.

        Returns:
            int | None: The user's numeric id, or None where it is unclaimed.

        Raises:
            ValueError: If the first commit came from no merged pull request.

        """
        sha: str | None = self._oldest(identifier, 1)
        if sha is None:
            return None
        pulls: list[dict[str, object]] = [
            Json.as_dict(pull)
            for pull in Json.as_list(
                self._fetch(f"repos/{self.__repository}/commits/{sha}/pulls")
            )
            if Json.as_dict(pull).get("merged_at")
        ]
        if not pulls:
            raise ValueError(f"commit {sha} was not merged from a pull request")
        owner: object = Json.as_dict(pulls[0].get("user")).get("id")
        if not isinstance(owner, int):
            raise ValueError(f"the pull request behind commit {sha} has no author")
        return owner

    def permits(self, identifier: str, user: int) -> bool:
        """Report whether a user may publish a certificate.

        Args:
            identifier (str): The certificate's identifier.
            user (int): The submitting user's numeric GitHub id.

        Returns:
            bool: True where the certificate is unclaimed or the user owns it.

        """
        return self.get_owner(identifier) in (None, user)

    def _oldest(self, identifier: str, page: int) -> str | None:
        commits: list[object] = Json.as_list(
            self._fetch(
                f"repos/{self.__repository}/commits?path={identifier}/score.json"
                f"&per_page={Ownership.PAGE}&page={page}"
            )
        )
        if len(commits) == Ownership.PAGE:
            return self._oldest(identifier, page + 1) or Json.as_text(
                Json.as_dict(commits[-1]).get("sha")
            )
        return Json.as_text(Json.as_dict(commits[-1]).get("sha")) if commits else None

    def _fetch(self, path: str) -> object:
        with urllib.request.urlopen(
            urllib.request.Request(
                Ownership.API + path,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
                },
            )
        ) as response:
            return json.load(response)
