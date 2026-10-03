import dataclasses
import datetime
import pathlib
from collections import Counter

from vibecert.attribution import LineAttribution
from vibecert.git_repository import GitRepository
from vibecert.transcript import TranscriptSession, TranscriptStore
from vibecert.vibecert_types import Commit, FileDiff, SessionSpan


class EvidenceCollector:
    """Assembles the evidence bundle for one branch.

    Args:
        repository (GitRepository): The repository holding the branch.
        store (TranscriptStore): The transcripts to search for its sessions.
        base (str): The branch it was taken from.
        untracked (bool): Whether to count files Git is not tracking.

    """

    SCHEMA: str = "vibecert/evidence@1"

    def __init__(
        self,
        repository: GitRepository,
        store: TranscriptStore,
        base: str,
        untracked: bool,
    ) -> None:

        self.__repository: GitRepository = repository
        self.__store: TranscriptStore = store
        self.__base: str = base
        self.__untracked: bool = untracked

    def collect(self) -> dict[str, object]:
        """Gather every signal the metrics are scored from.

        Returns:
            dict[str, object]: The evidence bundle, ready to serialise.

        """
        merge_base: str = self.__repository.get_merge_base(self.__base)
        commits: list[Commit] = self.__repository.get_commits(merge_base)
        diff: dict[str, FileDiff] = self.__repository.get_diff(
            merge_base, self.__untracked
        )
        sessions: list[TranscriptSession] = self.__store.find_sessions(
            self.__repository.get_root(), self._window_start(merge_base), self._now()
        )
        return {
            "schema": self.SCHEMA,
            "collected_at": self._now(),
            "repository": self._repository_block(),
            "branch": self._branch_block(self.__base, merge_base, commits),
            "diff": self._diff_block(diff),
            "sessions": [dataclasses.asdict(span) for span in self._spans(sessions)],
            "prompts": [
                dataclasses.asdict(prompt)
                for session in sessions
                for prompt in session.get_prompts()
            ],
            "attribution": self._attribution_block(diff, sessions),
            "activity": self._activity_block(sessions, self.__repository.get_root()),
        }

    def _repository_block(self) -> dict[str, object]:
        return {
            "root": str(self.__repository.get_root()),
            "name": self.__repository.get_root().name,
            "remote": self.__repository.get_remote(),
        }

    def _branch_block(
        self, base: str, merge_base: str, commits: list[Commit]
    ) -> dict[str, object]:
        return {
            "name": self.__repository.get_branch(),
            "base": base,
            "merge_base": merge_base,
            "commits": [dataclasses.asdict(commit) for commit in commits],
            "includes_uncommitted": self.__repository.is_dirty(),
            "window": {"start": self._window_start(merge_base), "end": self._now()},
        }

    @staticmethod
    def _diff_block(diff: dict[str, FileDiff]) -> dict[str, object]:
        return {
            "files": [
                {
                    "path": file_diff.path,
                    "suffix": pathlib.PurePath(file_diff.path).suffix,
                    "added": len(file_diff.added),
                    "removed": file_diff.removed,
                }
                for file_diff in diff.values()
            ],
            "added": sum(len(file_diff.added) for file_diff in diff.values()),
            "removed": sum(file_diff.removed for file_diff in diff.values()),
            "changed": sum(
                len(file_diff.added) + file_diff.removed for file_diff in diff.values()
            ),
        }

    def _attribution_block(
        self, diff: dict[str, FileDiff], sessions: list[TranscriptSession]
    ) -> dict[str, object]:
        attribution: LineAttribution = LineAttribution(
            diff,
            [edit for session in sessions for edit in session.get_edits()],
            self.__repository.get_root(),
        )
        return {
            "added": attribution.get_added(),
            "generated": attribution.get_generated(),
            "human": attribution.get_human(),
            "generative_proportion": attribution.get_proportion(),
            "touched": attribution.get_touched(),
            "touched_proportion": attribution.get_touched_proportion(),
            "per_file": attribution.get_per_file(),
        }

    @staticmethod
    def _existing(paths: set[str], root: pathlib.Path) -> list[str]:
        return sorted(
            {
                str(resolved)
                for path in paths
                for resolved in (pathlib.Path(path).expanduser(),)
                for candidate in (
                    resolved if resolved.is_absolute() else root / resolved,
                )
                if candidate.is_file()
            }
        )

    @classmethod
    def _activity_block(
        cls, sessions: list[TranscriptSession], root: pathlib.Path
    ) -> dict[str, object]:
        return {
            "human_messages": sum(len(session.get_prompts()) for session in sessions),
            "tool_counts": dict(
                sum(
                    (Counter(session.get_tool_counts()) for session in sessions),
                    Counter(),
                )
            ),
            "bash_commands": [
                command
                for session in sessions
                for command in session.get_bash_commands()
            ],
            "guidelines_in_context": cls._existing(
                {
                    path
                    for session in sessions
                    for path in session.get_guidelines_in_context()
                    | session.get_guidelines_read()
                },
                root,
            ),
        }

    @staticmethod
    def _spans(sessions: list[TranscriptSession]) -> list[SessionSpan]:
        return [
            SessionSpan(
                session.get_identifier(),
                str(session.get_path()),
                session.get_span()[0],
                session.get_span()[1],
            )
            for session in sessions
        ]

    def _window_start(self, merge_base: str) -> str:
        return self.__repository.get_commit_time(merge_base)

    @staticmethod
    def _now() -> str:
        return datetime.datetime.now(datetime.UTC).isoformat()
