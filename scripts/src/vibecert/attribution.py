import pathlib
from collections import Counter, defaultdict

from vibecert.vibecert_types import EditHunk, FileDiff


class LineAttribution:
    """Splits the branch diff into generated and human-authored lines.

    Args:
        diff (dict[str, FileDiff]): Added and removed lines, keyed by
            repository-relative path.
        edits (list[EditHunk]): Every hunk a tool call wrote, with absolute paths.
        root (pathlib.Path): The repository root, used to key edits against the diff.

    """

    PRECISION: int = 3

    def __init__(
        self, diff: dict[str, FileDiff], edits: list[EditHunk], root: pathlib.Path
    ) -> None:
        self.__diff: dict[str, FileDiff] = diff
        self.__generated: dict[str, int] = self._generated_per_file(diff, edits, root)
        self.__touched: set[str] = {self._relative(edit.path, root) for edit in edits}

    def get_generated(self) -> int:
        """Return the number of added lines attributable to the model.

        Returns:
            int: Generated line count across the branch.

        """
        return sum(self.__generated.values())

    def get_added(self) -> int:
        """Return the number of added lines in the branch diff.

        Returns:
            int: Added line count across the branch.

        """
        return sum(len(diff.added) for diff in self.__diff.values())

    def get_human(self) -> int:
        """Return the number of added lines the author wrote directly.

        Returns:
            int: Added lines not attributable to any tool call.

        """
        return self.get_added() - self.get_generated()

    def get_proportion(self) -> float:
        """Return the share of the diff that is generated.

        Returns:
            float: Generated lines over added lines, or 0.0 for an empty diff.

        """
        return (
            round(self.get_generated() / self.get_added(), self.PRECISION)
            if self.get_added()
            else 0.0
        )

    def get_touched(self) -> int:
        """Return the added lines in files the model wrote to at all.

        Returns:
            int: Added lines across every file the model changed.

        """
        return sum(
            len(diff.added)
            for path, diff in self.__diff.items()
            if path in self.__touched
        )

    def get_touched_proportion(self) -> float:
        """Return the share of the diff in files the model wrote to.

        Returns:
            float: Touched lines over added lines, or 0.0 for an empty diff.

        """
        return (
            round(self.get_touched() / self.get_added(), self.PRECISION)
            if self.get_added()
            else 0.0
        )

    def get_per_file(self) -> dict[str, dict[str, int]]:
        """Return the attribution split for each changed file.

        Returns:
            dict[str, dict[str, int]]: Path to its added, generated and human counts.

        """
        return {
            path: {
                "added": len(diff.added),
                "generated": self.__generated.get(path, 0),
                "human": len(diff.added) - self.__generated.get(path, 0),
                "touched": int(path in self.__touched),
            }
            for path, diff in self.__diff.items()
        }

    @classmethod
    def _generated_per_file(
        cls, diff: dict[str, FileDiff], edits: list[EditHunk], root: pathlib.Path
    ) -> dict[str, int]:
        written: dict[str, Counter[str]] = cls._written_lines(edits, root)
        return {
            path: sum(
                (Counter(file_diff.added) & written.get(path, Counter())).values()
            )
            for path, file_diff in diff.items()
        }

    @staticmethod
    def _written_lines(
        edits: list[EditHunk], root: pathlib.Path
    ) -> dict[str, Counter[str]]:
        written: dict[str, Counter[str]] = defaultdict(Counter)
        for edit in edits:
            written[LineAttribution._relative(edit.path, root)].update(edit.added)
        return written

    @staticmethod
    def _relative(path: str, root: pathlib.Path) -> str:
        resolved: str = str(pathlib.Path(path).resolve())
        return (
            resolved[len(str(root)) + 1 :]
            if resolved.startswith(str(root) + "/")
            else resolved
        )
