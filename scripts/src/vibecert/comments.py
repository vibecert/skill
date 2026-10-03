from vibecert.rubric import Languages


class CommentCounter:
    """Counts inline comment and code lines among the lines a diff adds."""

    @staticmethod
    def count(lines: list[str], suffix: str) -> tuple[int, int]:
        """Return the comment and code line counts for one file's added lines.

        Blank lines are counted as neither. A docstring body does not start with
        the comment marker, so it counts as code, which is intended: the metric
        is about narration added to code, not interface documentation.

        Args:
            lines (list[str]): The lines the diff adds to the file.
            suffix (str): The file suffix, including its leading dot.

        Returns:
            tuple[int, int]: Comment lines and code lines, both zero where
                comment density does not apply to the file type.

        """
        if not Languages.get_marker(suffix):
            return 0, 0
        return (
            sum(
                1
                for line in lines
                if line.strip().startswith(Languages.get_marker(suffix))
            ),
            sum(
                1
                for line in lines
                if line.strip()
                and not line.strip().startswith(Languages.get_marker(suffix))
            ),
        )
