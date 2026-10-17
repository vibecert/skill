import datetime
import json
import os
import urllib.request

from vibecert.json_values import Json


class Account:
    """A GitHub account that submits to the shared site.

    Args:
        user (int): The account's numeric GitHub id.

    """

    API: str = "https://api.github.com/"

    def __init__(self, user: int) -> None:
        self.__user: int = user

    def get_age(self) -> datetime.timedelta:
        """Return how long ago the account was created.

        Returns:
            datetime.timedelta: The time since the account was created.

        Raises:
            ValueError: If the account has no creation date.

        """
        return datetime.datetime.now(datetime.UTC) - datetime.datetime.fromisoformat(
            Json.as_text(
                Json.as_dict(self._fetch(f"user/{self.__user}")).get("created_at")
            )
        )

    def _fetch(self, path: str) -> object:
        with urllib.request.urlopen(
            urllib.request.Request(
                Account.API + path,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
                },
            )
        ) as response:
            return json.load(response)
