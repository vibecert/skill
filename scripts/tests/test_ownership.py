import dataclasses
import unittest.mock
import urllib.error

import pytest
import pytest_mock

from vibecert.ownership import Ownership

COMMITS: str = "repos/foo/foo.github.io/commits?path=abc1234/score.json"
PULLS: str = "repos/foo/foo.github.io/commits/sha1/pulls"


@dataclasses.dataclass
class OwnershipMocks:
    _fetch: unittest.mock.MagicMock


@pytest.fixture
def ownership_mocks(mocker: pytest_mock.MockerFixture) -> OwnershipMocks:
    return OwnershipMocks(
        mocker.patch.object(
            Ownership,
            "_fetch",
            side_effect=lambda path: (
                [{"sha": "sha2"}, {"sha": "sha1"}]
                if path.startswith(COMMITS)
                else [
                    {"merged_at": None, "user": {"id": 2}},
                    {"merged_at": "2026-01-01T00:00:00Z", "user": {"id": 1}},
                ]
                if path == PULLS
                else []
            ),
        )
    )


@pytest.fixture
def ownership() -> Ownership:
    return Ownership("foo/foo.github.io")


class TestOwnership:
    def test_get_owner_claimed_returns_author_of_merged_pull(
        self, ownership: Ownership, ownership_mocks: OwnershipMocks
    ) -> None:
        assert ownership.get_owner("abc1234") == 1

    def test_get_owner_unclaimed_returns_none(
        self, ownership: Ownership, ownership_mocks: OwnershipMocks
    ) -> None:
        ownership_mocks._fetch.side_effect = lambda path: []
        assert ownership.get_owner("abc1234") is None

    def test_get_owner_full_first_page_reads_the_last(
        self, ownership: Ownership, ownership_mocks: OwnershipMocks
    ) -> None:
        ownership_mocks._fetch.side_effect = lambda path: (
            [{"sha": "sha2"}] * Ownership.PAGE
            if path.endswith("&page=1")
            else [{"sha": "sha1"}]
            if path.endswith("&page=2")
            else [{"merged_at": "2026-01-01T00:00:00Z", "user": {"id": 1}}]
            if path == PULLS
            else []
        )
        assert ownership.get_owner("abc1234") == 1

    def test_get_owner_full_last_page_reads_its_final_commit(
        self, ownership: Ownership, ownership_mocks: OwnershipMocks
    ) -> None:
        ownership_mocks._fetch.side_effect = lambda path: (
            [{"sha": "sha2"}] * (Ownership.PAGE - 1) + [{"sha": "sha1"}]
            if path.endswith("&page=1")
            else [{"merged_at": "2026-01-01T00:00:00Z", "user": {"id": 1}}]
            if path == PULLS
            else []
        )
        assert ownership.get_owner("abc1234") == 1

    @pytest.mark.parametrize(
        "pulls",
        [[], [{"merged_at": None, "user": {"id": 1}}]],
    )
    def test_get_owner_commit_without_merged_pull_raises(
        self,
        ownership: Ownership,
        ownership_mocks: OwnershipMocks,
        pulls: list[dict[str, object]],
    ) -> None:
        ownership_mocks._fetch.side_effect = lambda path: (
            [{"sha": "sha1"}] if path.startswith(COMMITS) else pulls
        )
        with pytest.raises(ValueError, match="not merged from a pull request"):
            ownership.get_owner("abc1234")

    def test_get_owner_pull_without_author_raises(
        self, ownership: Ownership, ownership_mocks: OwnershipMocks
    ) -> None:
        ownership_mocks._fetch.side_effect = lambda path: (
            [{"sha": "sha1"}]
            if path.startswith(COMMITS)
            else [{"merged_at": "2026-01-01T00:00:00Z", "user": None}]
        )
        with pytest.raises(ValueError, match="has no author"):
            ownership.get_owner("abc1234")

    def test_get_owner_api_failure_propagates(
        self, ownership: Ownership, ownership_mocks: OwnershipMocks
    ) -> None:
        ownership_mocks._fetch.side_effect = urllib.error.URLError("foo")
        with pytest.raises(urllib.error.URLError):
            ownership.get_owner("abc1234")

    @pytest.mark.parametrize(
        ("owner", "user", "expected"),
        [(None, 1, True), (1, 1, True), (1, 2, False)],
        ids=["unclaimed", "same_owner", "different_owner"],
    )
    def test_permits_owner_and_user_returns_expected(
        self,
        ownership: Ownership,
        mocker: pytest_mock.MockerFixture,
        owner: int | None,
        user: int,
        expected: bool,
    ) -> None:
        mocker.patch.object(Ownership, "get_owner", return_value=owner)
        assert ownership.permits("abc1234", user) is expected
