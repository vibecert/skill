import pathlib
import subprocess

from vibecert.vibecert_types import Commit, FileDiff


class GitRepository:
    """Read-only access to the branch under assessment.

    Args:
        root (pathlib.Path): The working tree, resolved on construction.

    """

    def __init__(self, root: pathlib.Path) -> None:
        self.__root: pathlib.Path = root.resolve()

    def get_root(self) -> pathlib.Path:
        """Return the resolved repository root.

        Returns:
            pathlib.Path: The directory containing the working tree.

        """
        return self.__root

    def get_branch(self) -> str:
        """Return the name of the checked out branch.

        Returns:
            str: The branch name, or 'HEAD' when detached.

        """
        return self._run("rev-parse", "--abbrev-ref", "HEAD")

    def get_merge_base(self, base: str) -> str:
        """Return the commit the branch was taken from.

        Args:
            base (str): The branch it was taken from.

        Returns:
            str: The merge base sha.

        """
        return self._run("merge-base", "HEAD", base)

    def get_commits(self, merge_base: str) -> list[Commit]:
        """Return the commits unique to the branch, oldest first.

        Args:
            merge_base (str): The sha the branch was taken from.

        Returns:
            list[Commit]: One entry per commit, oldest first.

        """
        return [
            Commit(line.split("\x1f")[0], line.split("\x1f")[1], line.split("\x1f")[2])
            for line in reversed(
                self._run(
                    "log", "--format=%H\x1f%aI\x1f%s", merge_base + "..HEAD"
                ).splitlines()
            )
            if line
        ]

    def get_diff(self, merge_base: str, untracked: bool) -> dict[str, FileDiff]:
        """Return added and removed lines per file, including uncommitted work.

        Args:
            merge_base (str): The sha the branch was taken from.
            untracked (bool): Whether to count files Git is not tracking.

        Returns:
            dict[str, FileDiff]: Repository-relative path to its diff.

        """
        return self._merge_diffs(
            self._parse_diff(
                self._run("diff", "--unified=0", "--no-color", merge_base)
            ),
            self._read_untracked() if untracked else {},
        )

    def get_remote(self) -> str:
        """Return the origin remote URL.

        Returns:
            str: The URL, or an empty string when there is no origin.

        """
        return self._try_run("remote", "get-url", "origin")

    def get_tracked_files(self) -> list[str]:
        """Return every file Git tracks.

        Returns:
            list[str]: Repository-relative paths.

        """
        return self._try_run("ls-files").splitlines()

    def get_commit_time(self, sha: str) -> str:
        """Return when a commit was authored.

        Args:
            sha (str): The commit to look up.

        Returns:
            str: The author date in ISO 8601.

        """
        return self._run("show", "-s", "--format=%aI", sha)

    def is_dirty(self) -> bool:
        """Report whether the working tree carries uncommitted changes.

        Returns:
            bool: True when tracked files are modified or files are untracked.

        """
        return bool(self._try_run("status", "--porcelain"))

    def _read_untracked(self) -> dict[str, FileDiff]:
        return {
            path: FileDiff(path, self._read_lines(self.__root / path), 0)
            for path in self._try_run(
                "ls-files", "--others", "--exclude-standard"
            ).splitlines()
            if path
        }

    @staticmethod
    def read_lines(path: pathlib.Path) -> list[str]:
        """Return a file's lines, tolerating one that cannot be read.

        Args:
            path (pathlib.Path): The file to read.

        Returns:
            list[str]: The lines, or an empty list when the file is unreadable.

        """
        return GitRepository._read_lines(path)

    @staticmethod
    def _read_lines(path: pathlib.Path) -> list[str]:
        try:
            return path.read_text(errors="ignore").splitlines()
        except OSError:
            return []

    @staticmethod
    def _merge_diffs(
        tracked: dict[str, FileDiff], untracked: dict[str, FileDiff]
    ) -> dict[str, FileDiff]:
        return tracked | {path: diff for path, diff in untracked.items() if diff.added}

    @staticmethod
    def _parse_diff(diff: str) -> dict[str, FileDiff]:
        files: dict[str, FileDiff] = {}
        current: FileDiff | None = None
        for line in diff.splitlines():
            if line.startswith("+++ b/"):
                current = files.setdefault(line[6:], FileDiff(line[6:], [], 0))
            elif current is None or line.startswith(
                ("+++", "---", "diff ", "index ", "@@")
            ):
                continue
            elif line.startswith("+"):
                current.added.append(line[1:])
            elif line.startswith("-"):
                current.removed += 1
        return files

    def _run(self, *arguments: str) -> str:
        return subprocess.run(
            ("git", "-C", str(self.__root), *arguments),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    def _try_run(self, *arguments: str) -> str:
        try:
            return self._run(*arguments)
        except subprocess.CalledProcessError:
            return ""
