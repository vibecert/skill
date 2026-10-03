import pathlib

import pytest_mock

from vibecert.risk import RiskScanner

RUFF_OUTPUT: str = (
    '[{"code": "S602", "filename": "/repo/foo.py", '
    '"message": "subprocess call with shell=True"}]'
)


class TestRiskScanner:
    def test_scan_python_findings_returns_code_and_message(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        mocker.patch.object(
            RiskScanner,
            "_run",
            return_value=[
                {"code": "S602", "filename": "/repo/foo.py", "message": "shell=True"}
            ],
        )
        assert RiskScanner(pathlib.Path("/repo")).scan(["foo.py"]) == {
            "foo.py": ["S602: shell=True"]
        }

    def test_scan_non_python_file_returns_no_findings(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        mocker.patch.object(RiskScanner, "_run", return_value=[])
        assert RiskScanner(pathlib.Path("/repo")).scan(["foo.md"]) == {"foo.md": []}

    def test_run_tool_unavailable_returns_no_findings(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        mocker.patch("vibecert.risk.subprocess.run", side_effect=OSError)
        assert RiskScanner(pathlib.Path("/repo"))._run(["foo.py"]) == []

    def test_run_no_python_files_does_not_invoke_tool(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        run = mocker.patch("vibecert.risk.subprocess.run")
        RiskScanner(pathlib.Path("/repo"))._run([])
        run.assert_not_called()

    def test_scan_sensitive_personal_data_named_returns_category(self) -> None:
        assert RiskScanner(pathlib.Path("/repo")).scan_sensitive(
            ["patient = load()"]
        ) == ["personal data referenced"]
