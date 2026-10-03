import pathlib
import unittest.mock

import pytest
import pytest_mock

from vibecert.vibecert import Cli


class TestCli:
    def test_emit_no_destination_writes_to_stdout(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        Cli._emit("{}", None)
        assert capsys.readouterr().out.strip() == "{}"

    def test_emit_destination_given_writes_to_file(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        write_text: unittest.mock.MagicMock = mocker.patch.object(
            pathlib.Path, "write_text"
        )
        Cli._emit("{}", "/out/bundle.json")
        write_text.assert_called_once_with("{}")

    def test_parser_defaults_returns_current_directory(self) -> None:
        assert Cli._parser().parse_args([]).repo == "."
