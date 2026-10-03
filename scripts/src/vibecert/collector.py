import datetime
import pathlib
from collections import Counter

from vibecert.attribution import LineAttribution
from vibecert.bundle_types import (
    ActivityInfo,
    AttributionInfo,
    BranchInfo,
    CommitInfo,
    DiffInfo,
    Evidence,
    FileInfo,
    PromptInfo,
    RepositoryInfo,
    SessionInfo,
    WindowInfo,
)
from vibecert.comments import CommentCounter
from vibecert.git_repository import GitRepository
from vibecert.revisions import RevisionCounter
from vibecert.rubric import CheckRegistry
from vibecert.transcript import TranscriptSession, TranscriptStore
from vibecert.vibecert_types import Commit, EditHunk, FileDiff, Prompt


class EvidenceCollector:
    """Assembles the evidence bundle for one branch.

    Args:
        repository (GitRepository): The repository holding the branch.
        store (TranscriptStore): The transcripts to search for its sessions.
        base (str): The branch it was taken from.
        untracked (bool): Whether to count files Git is not tracking.

    """

    SCHEMA: str = "vibecert/evidence@2"

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

    def collect(self) -> Evidence:
        """Gather every signal the metrics are scored from.

        Returns:
            Evidence: The validated evidence bundle.

        """
        merge_base: str = self.__repository.get_merge_base(self.__base)
        diff: dict[str, FileDiff] = self.__repository.get_diff(
            merge_base, self.__untracked
        )
        sessions: list[TranscriptSession] = self.__store.find_sessions(
            self.__repository.get_root(), self._window_start(merge_base), self._now()
        )
        edits: list[EditHunk] = [
            edit for session in sessions for edit in session.get_edits()
        ]
        prompts: list[Prompt] = [
            prompt for session in sessions for prompt in session.get_prompts()
        ]
        attribution: LineAttribution = LineAttribution(
            diff, edits, self.__repository.get_root()
        )
        return Evidence(
            schema_version=self.SCHEMA,
            collected_at=self._now(),
            repository=self._repository_info(),
            branch=self._branch_info(
                merge_base, self.__repository.get_commits(merge_base)
            ),
            diff=self._diff_info(diff, attribution),
            sessions=self._session_info(sessions),
            prompts=[
                PromptInfo(
                    session=prompt.session,
                    timestamp=prompt.timestamp,
                    text=prompt.text,
                )
                for prompt in prompts
            ],
            attribution=self._attribution_info(
                attribution, RevisionCounter(edits, prompts).count()
            ),
            activity=self._activity_info(sessions),
        )

    def _repository_info(self) -> RepositoryInfo:
        return RepositoryInfo(
            root=str(self.__repository.get_root()),
            name=self.__repository.get_root().name,
            remote=self.__repository.get_remote(),
            comment_density=self._baseline_density(),
        )

    def _baseline_density(self) -> float:
        counts: list[tuple[int, int]] = [
            CommentCounter.count(
                GitRepository.read_lines(self.__repository.get_root() / path),
                pathlib.PurePath(path).suffix,
            )
            for path in self.__repository.get_tracked_files()
        ]
        return (
            round(
                sum(comments for comments, _ in counts)
                / sum(code for _, code in counts),
                LineAttribution.PRECISION,
            )
            if sum(code for _, code in counts)
            else 0.0
        )

    def _branch_info(self, merge_base: str, commits: list[Commit]) -> BranchInfo:
        return BranchInfo(
            name=self.__repository.get_branch(),
            base=self.__base,
            merge_base=merge_base,
            commits=[
                CommitInfo(
                    sha=commit.sha,
                    timestamp=commit.timestamp,
                    subject=commit.subject,
                )
                for commit in commits
            ],
            includes_uncommitted=self.__repository.is_dirty(),
            window=WindowInfo(start=self._window_start(merge_base), end=self._now()),
        )

    @staticmethod
    def _diff_info(diff: dict[str, FileDiff], attribution: LineAttribution) -> DiffInfo:
        return DiffInfo(
            files=[
                FileInfo(
                    path=path,
                    suffix=pathlib.PurePath(path).suffix,
                    added=len(file_diff.added),
                    removed=file_diff.removed,
                    generated=attribution.get_per_file()[path]["generated"],
                    human=attribution.get_per_file()[path]["human"],
                    touched=bool(attribution.get_per_file()[path]["touched"]),
                    comments=CommentCounter.count(
                        file_diff.added, pathlib.PurePath(path).suffix
                    )[0],
                    code=CommentCounter.count(
                        file_diff.added, pathlib.PurePath(path).suffix
                    )[1],
                )
                for path, file_diff in diff.items()
            ],
            added=sum(len(file_diff.added) for file_diff in diff.values()),
            removed=sum(file_diff.removed for file_diff in diff.values()),
            changed=sum(
                len(file_diff.added) + file_diff.removed for file_diff in diff.values()
            ),
        )

    @staticmethod
    def _attribution_info(
        attribution: LineAttribution, revised: int
    ) -> AttributionInfo:
        return AttributionInfo(
            added=attribution.get_added(),
            generated=attribution.get_generated(),
            human=attribution.get_human(),
            generative_proportion=attribution.get_proportion(),
            touched=attribution.get_touched(),
            touched_proportion=attribution.get_touched_proportion(),
            revised=revised,
            revised_proportion=(
                round(revised / attribution.get_touched(), LineAttribution.PRECISION)
                if attribution.get_touched()
                else 0.0
            ),
        )

    @staticmethod
    def _session_info(sessions: list[TranscriptSession]) -> list[SessionInfo]:
        return [
            SessionInfo(
                identifier=session.get_identifier(),
                path=str(session.get_path()),
                start=session.get_span()[0],
                end=session.get_span()[1],
            )
            for session in sessions
        ]

    def _activity_info(self, sessions: list[TranscriptSession]) -> ActivityInfo:
        return ActivityInfo(
            human_messages=sum(len(session.get_prompts()) for session in sessions),
            tool_counts=dict(
                sum(
                    (Counter(session.get_tool_counts()) for session in sessions),
                    Counter(),
                )
            ),
            bash_commands=[
                command
                for session in sessions
                for command in session.get_bash_commands()
            ],
            guidelines_in_context=self._existing(
                {
                    path
                    for session in sessions
                    for path in session.get_guidelines_in_context()
                    | session.get_guidelines_read()
                },
                self.__repository.get_root(),
            ),
            check_configs=self._check_configs(),
        )

    def _check_configs(self) -> dict[str, list[str]]:
        return {
            path: CheckRegistry.configured_by(
                pathlib.PurePath(path).name,
                "\n".join(
                    GitRepository.read_lines(self.__repository.get_root() / path)
                ),
            )
            for path in self.__repository.get_tracked_files()
            if any(
                pathlib.PurePath(path).name in check.configs
                for check in CheckRegistry.CLASSES
            )
        }

    @staticmethod
    def _existing(paths: set[str], root: pathlib.Path) -> list[str]:
        return sorted(
            {
                str(candidate)
                for path in paths
                for resolved in (pathlib.Path(path).expanduser(),)
                for candidate in (
                    resolved if resolved.is_absolute() else root / resolved,
                )
                if candidate.is_file()
            }
        )

    def _window_start(self, merge_base: str) -> str:
        return self.__repository.get_commit_time(merge_base)

    @staticmethod
    def _now() -> str:
        return datetime.datetime.now(datetime.UTC).isoformat()
