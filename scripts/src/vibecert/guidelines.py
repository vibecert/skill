import pathlib
import re


class GuidelineIndex:
    """The prose rules available to a repository, and which of them the diff invokes.

    Args:
        root (pathlib.Path): The repository root, for rules held in the repository.
        rules (pathlib.Path): The directory of personal rule files.

    """

    REPOSITORY_NAMES: tuple[str, ...] = ("CLAUDE.md", "AGENTS.md", "CONTRIBUTING.md")
    PATHS_BLOCK: re.Pattern[str] = re.compile(
        r"^---\s*$.*?^paths:\s*$(.*?)^(?:\w|---)", re.MULTILINE | re.DOTALL
    )
    PATHS_ENTRY: re.Pattern[str] = re.compile(
        r'^\s*-\s*["\']?([^"\'\n]+)["\']?\s*$', re.MULTILINE
    )

    def __init__(self, root: pathlib.Path, rules: pathlib.Path) -> None:
        self.__root: pathlib.Path = root
        self.__rules: pathlib.Path = rules

    def get_available(self) -> list[pathlib.Path]:
        """Return every guideline file that could govern this repository.

        Returns:
            list[pathlib.Path]: Rule and convention files, sorted by path.

        """
        return sorted(
            set(self.__rules.rglob("*.md") if self.__rules.is_dir() else [])
            | {
                path
                for name in self.REPOSITORY_NAMES
                for path in self.__root.rglob(name)
                if ".git" not in path.parts
            }
        )

    def get_applicable(self, changed: list[str]) -> list[pathlib.Path]:
        """Return the guidelines the changed files invoke.

        Args:
            changed (list[str]): Repository-relative paths in the branch diff.

        Returns:
            list[pathlib.Path]: The subset of available guidelines that govern
                at least one changed file.

        """
        return [
            guideline
            for guideline in self.get_available()
            if self._governs(self._get_paths(guideline), changed)
        ]

    @classmethod
    def _get_paths(cls, guideline: pathlib.Path) -> list[str]:
        return cls.PATHS_ENTRY.findall(
            "".join(cls.PATHS_BLOCK.findall(cls._read(guideline)))
        )

    @staticmethod
    def _governs(patterns: list[str], changed: list[str]) -> bool:
        return not patterns or any(
            pathlib.PurePath(path).full_match(pattern)
            for pattern in patterns
            for path in changed
        )

    @staticmethod
    def _read(guideline: pathlib.Path) -> str:
        try:
            return guideline.read_text(errors="ignore")
        except OSError:
            return ""
