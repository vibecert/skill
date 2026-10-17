import dataclasses
import datetime
import unittest.mock
import urllib.error

import pytest
import pytest_mock

from vibecert.account import Account


@dataclasses.dataclass
class AccountMocks:
    _fetch: unittest.mock.MagicMock


@pytest.fixture
def account_mocks(mocker: pytest_mock.MockerFixture) -> AccountMocks:
    return AccountMocks(
        mocker.patch.object(
            Account,
            "_fetch",
            return_value={
                "created_at": (
                    datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=30)
                ).isoformat()
            },
        )
    )


class TestAccount:
    def test_get_age_created_date_returns_time_since(
        self, account_mocks: AccountMocks
    ) -> None:
        assert Account(1).get_age().days == 30
        account_mocks._fetch.assert_called_once_with("user/1")

    def test_get_age_no_created_date_raises(self, account_mocks: AccountMocks) -> None:
        account_mocks._fetch.return_value = {}
        with pytest.raises(ValueError):
            Account(1).get_age()

    def test_get_age_api_failure_propagates(self, account_mocks: AccountMocks) -> None:
        account_mocks._fetch.side_effect = urllib.error.URLError("foo")
        with pytest.raises(urllib.error.URLError):
            Account(1).get_age()
