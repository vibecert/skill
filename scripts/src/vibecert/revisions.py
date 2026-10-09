from vibecert.detection import CheckRegistry
from vibecert.vibecert_types import EditHunk, Prompt


class RevisionCounter:
    """Counts generated lines rewritten after the author challenged them.

    Args:
        edits (list[EditHunk]): Every hunk a tool call wrote, in any order.
        prompts (list[Prompt]): Every message the author typed, in any order.

    """

    def __init__(self, edits: list[EditHunk], prompts: list[Prompt]) -> None:
        self.__edits: list[EditHunk] = sorted(edits, key=lambda edit: edit.timestamp)
        self.__prompts: list[Prompt] = sorted(
            prompts, key=lambda prompt: prompt.timestamp
        )

    def count(self) -> int:
        """Return the number of lines written as revisions.

        Returns:
            int: Added lines belonging to a revising edit.

        """
        written: dict[str, str] = {}
        revised: int = 0
        for edit in self.__edits:
            if (
                edit.path in written
                and not self._is_formatter(edit)
                and self._challenged(written[edit.path], edit.timestamp)
            ):
                revised += len(edit.added)
            written[edit.path] = edit.timestamp
        return revised

    def _challenged(self, since: str, until: str) -> bool:
        return any(since < prompt.timestamp < until for prompt in self.__prompts)

    @staticmethod
    def _is_formatter(edit: EditHunk) -> bool:
        return any(
            CheckRegistry.invokes(edit.command, command)
            for check in CheckRegistry.CLASSES
            if check.name == "format"
            for command in check.commands
        )
