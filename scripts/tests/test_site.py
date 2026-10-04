import pytest

from vibecert.site import SiteAddress


class TestSiteAddress:
    @pytest.mark.parametrize(
        "remote,expected",
        [
            ("git@github.com:foo/bar.git", "https://foo.github.io/vibecert"),
            ("https://github.com/foo/bar", "https://foo.github.io/vibecert"),
            (
                "https://github.com/Foo-Bar/baz.git",
                "https://foo-bar.github.io/vibecert",
            ),
        ],
    )
    def test_derive_github_remote_returns_the_owner_site(
        self, remote: str, expected: str
    ) -> None:
        assert SiteAddress.derive(remote) == expected

    @pytest.mark.parametrize(
        "remote", ["", "git@gitlab.com:foo/bar.git", "/local/path"]
    )
    def test_derive_remote_without_an_owner_returns_empty(self, remote: str) -> None:
        assert SiteAddress.derive(remote) == ""

    @pytest.mark.parametrize(
        "site,expected",
        [
            ("https://foo.github.io/vibecert", "foo/vibecert"),
            ("https://foo.github.io/vibecert/", "foo/vibecert"),
            ("https://vibecert.github.io", "vibecert/vibecert.github.io"),
            ("https://vibecert.github.io/", "vibecert/vibecert.github.io"),
        ],
    )
    def test_repository_pages_address_returns_the_repository(
        self, site: str, expected: str
    ) -> None:
        assert SiteAddress.repository(site) == expected

    @pytest.mark.parametrize("site", ["https://example.com/vibecert", "not a url"])
    def test_repository_other_address_raises(self, site: str) -> None:
        with pytest.raises(ValueError):
            SiteAddress.repository(site)
