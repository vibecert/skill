import pathlib
import re

from vibecert.detection import ImportPatterns


class FanInCounter:
    """Counts how many files in a repository import each changed file.

    Args:
        contents (dict[str, str]): Repository-relative path to file contents.

    """

    def __init__(self, contents: dict[str, str]) -> None:
        self.__contents: dict[str, str] = contents

    def count(self, path: str) -> int:
        """Return how many other files import a given file.

        Args:
            path (str): The repository-relative path of the imported file.

        Returns:
            int: The number of importing files, or zero where imports cannot be
                identified for the file type.

        """
        pattern: re.Pattern[str] | None = self._pattern(path)
        return (
            sum(
                1
                for other, content in self.__contents.items()
                if other != path and pattern.search(content)
            )
            if pattern
            else 0
        )

    @staticmethod
    def _pattern(path: str) -> re.Pattern[str] | None:
        return ImportPatterns.get_pattern(
            pathlib.PurePath(path).suffix, pathlib.PurePath(path).stem
        )
