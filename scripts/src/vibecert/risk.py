import json
import pathlib
import subprocess

from vibecert.detection import SensitiveData
from vibecert.json_values import Json


class RiskScanner:
    """Finds the risk signals in changed code, for the risk weight.

    Args:
        root (pathlib.Path): The repository root, which paths are relative to.

    """

    RULES: str = "S"
    IGNORED: str = "S101"

    def __init__(self, root: pathlib.Path) -> None:
        self.__root: pathlib.Path = root

    def scan(self, paths: list[str]) -> dict[str, list[str]]:
        """Return the security findings for each changed file.

        Args:
            paths (list[str]): Repository-relative paths in the branch diff.

        Returns:
            dict[str, list[str]]: Path to its findings, as rule code and summary.

        """
        findings: dict[str, list[str]] = {path: [] for path in paths}
        for finding in self._run([path for path in paths if path.endswith(".py")]):
            code: str = Json.as_text(finding.get("code"))
            message: str = Json.as_text(finding.get("message"))
            path: str = self._relative(Json.as_text(finding.get("filename")))
            if f"{code}: {message}" not in findings.setdefault(path, []):
                findings[path].append(f"{code}: {message}")
        return findings

    def scan_sensitive(self, lines: list[str]) -> list[str]:
        """Return the sensitive data terms appearing in a file's added lines.

        Args:
            lines (list[str]): The lines the diff adds to the file.

        Returns:
            list[str]: A single entry naming the category, or nothing.

        """
        return SensitiveData.scan(lines)

    def _run(self, paths: list[str]) -> list[dict[str, object]]:
        if not paths:
            return []
        try:
            return [
                Json.as_dict(finding)
                for finding in json.loads(
                    subprocess.run(
                        (
                            "ruff",
                            "check",
                            "--select",
                            self.RULES,
                            "--ignore",
                            self.IGNORED,
                            "--isolated",
                            "--output-format",
                            "json",
                            *paths,
                        ),
                        capture_output=True,
                        text=True,
                        cwd=self.__root,
                    ).stdout
                    or "[]"
                )
            ]
        except (OSError, ValueError):
            return []

    def _relative(self, path: str) -> str:
        return (
            path[len(str(self.__root)) + 1 :]
            if path.startswith(str(self.__root) + "/")
            else path
        )
