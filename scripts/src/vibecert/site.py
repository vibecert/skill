import re


class SiteAddress:
    """Where an author's certificates are served from."""

    OWNER: re.Pattern[str] = re.compile(r"github\.com[:/](?P<owner>[\w.-]+)/")
    PROJECT: re.Pattern[str] = re.compile(
        r"https?://(?P<owner>[\w-]+)\.github\.io(?:/(?P<name>[\w.-]+))?/?$"
    )
    TEMPLATE: str = "https://{owner}.github.io/vibecert"

    @classmethod
    def derive(cls, remote: str) -> str:
        """Return the site an author's certificates belong on.

        Args:
            remote (str): The scored repository's origin URL.

        Returns:
            str: The base address without a trailing slash, or an empty string
                where the remote names no GitHub owner. Scoring a branch does
                not require an address; only publishing one does.

        """
        owner: re.Match[str] | None = cls.OWNER.search(remote)
        return cls.TEMPLATE.format(owner=owner["owner"].lower()) if owner else ""

    @classmethod
    def repository(cls, site: str) -> str:
        """Return the GitHub repository that serves a site.

        Args:
            site (str): The site's base address.

        Returns:
            str: The repository, as owner and name.

        Raises:
            ValueError: If the address is not a GitHub Pages site.

        """
        parts: re.Match[str] | None = cls.PROJECT.match(site)
        if not parts:
            raise ValueError(f"{site!r} is not a GitHub Pages address")
        return f"{parts['owner']}/{parts['name'] or parts['owner'] + '.github.io'}"
