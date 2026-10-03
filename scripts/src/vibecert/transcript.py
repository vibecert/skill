import datetime
import json
import pathlib
import re
from collections import Counter

from vibecert.json_values import Json
from vibecert.vibecert_types import EditHunk, Prompt


class TranscriptSession:
    """One Claude Code transcript, parsed for evidence.

    Args:
        path (pathlib.Path): The transcript file, whose stem names the session.

    """

    GUIDELINE_PATTERN: re.Pattern[str] = re.compile(
        r"[\w~/.-]*(?:/\.claude/rules/[\w/.-]+\.md|CLAUDE\.md|AGENTS\.md|CONTRIBUTING\.md)"
    )

    def __init__(self, path: pathlib.Path) -> None:

        self.__path: pathlib.Path = path
        self.__entries: list[dict[str, object]] = self._read(path)

    def get_identifier(self) -> str:
        """Return the session identifier.

        Returns:
            str: The transcript file stem.

        """
        return self.__path.stem

    def get_path(self) -> pathlib.Path:
        """Return the transcript location.

        Returns:
            pathlib.Path: The path the transcript was read from.

        """
        return self.__path

    def get_working_directories(self) -> set[str]:
        """Return every working directory the session reported.

        Returns:
            set[str]: Absolute directory paths.

        """
        return {
            str(entry["cwd"])
            for entry in self.__entries
            if isinstance(entry.get("cwd"), str)
        }

    def get_span(self) -> tuple[str, str]:
        """Return the first and last timestamp in the session.

        Returns:
            tuple[str, str]: Earliest and latest ISO 8601 timestamps, empty when absent.

        """
        return (
            (self._timestamps()[0], self._timestamps()[-1])
            if self._timestamps()
            else ("", "")
        )

    def get_prompts(self) -> list[Prompt]:
        """Return the messages the author typed.

        Returns:
            list[Prompt]: One entry per human message, in order.

        """
        return [
            Prompt(
                self.get_identifier(),
                str(entry.get("timestamp", "")),
                self._text(entry),
            )
            for entry in self.__entries
            if entry.get("type") == "user"
            and not entry.get("isSidechain")
            and Json.as_dict(entry.get("origin")).get("kind") == "human"
        ]

    def get_edits(self) -> list[EditHunk]:
        """Return every file change the model made, across all edit channels.

        Returns:
            list[EditHunk]: One entry per changed file per tool result.

        """
        return [hunk for entry in self.__entries for hunk in self._edits_of(entry)]

    def get_tool_counts(self) -> dict[str, int]:
        """Return how many times each tool was called.

        Returns:
            dict[str, int]: Tool name to call count.

        """
        return dict(Counter(name for name, _ in self._tool_uses()))

    def get_bash_commands(self) -> list[str]:
        """Return the shell commands the model ran.

        Returns:
            list[str]: Command strings, in order.

        """
        return [
            str(arguments["command"])
            for name, arguments in self._tool_uses()
            if name == "Bash" and isinstance(arguments.get("command"), str)
        ]

    def get_guidelines_read(self) -> set[str]:
        """Return the guideline files the session opened for itself.

        Returns:
            set[str]: Absolute paths appearing in read commands or tool arguments.

        """
        return {
            path
            for _, arguments in self._tool_uses()
            for value in arguments.values()
            if isinstance(value, str)
            for path in self.GUIDELINE_PATTERN.findall(value)
        }

    def get_guidelines_in_context(self) -> set[str]:
        """Return the guideline files injected into the session.

        Returns:
            set[str]: Absolute paths of rule and memory files.

        """
        return {
            Json.as_text(Json.as_dict(file).get("path"))
            for entry in self.__entries
            if Json.as_dict(entry.get("attachment")).get("type") == "instructions"
            for file in Json.as_list(Json.as_dict(entry.get("attachment")).get("files"))
        }

    def _timestamps(self) -> list[str]:
        return sorted(
            str(entry["timestamp"])
            for entry in self.__entries
            if isinstance(entry.get("timestamp"), str)
        )

    def _commands_by_id(self) -> dict[str, str]:
        return {
            Json.as_text(Json.as_dict(block).get("id")): Json.as_text(
                Json.as_dict(Json.as_dict(block).get("input")).get("command")
            )
            for entry in self.__entries
            for block in Json.as_list(Json.as_dict(entry.get("message")).get("content"))
            if Json.as_dict(block).get("type") == "tool_use"
        }

    def _command_of(self, entry: dict[str, object]) -> str:
        return next(
            (
                self._commands_by_id().get(
                    Json.as_text(Json.as_dict(block).get("tool_use_id")), ""
                )
                for block in Json.as_list(
                    Json.as_dict(entry.get("message")).get("content")
                )
                if Json.as_dict(block).get("type") == "tool_result"
            ),
            "",
        )

    def _edits_of(self, entry: dict[str, object]) -> list[EditHunk]:
        result: dict[str, object] = Json.as_dict(entry.get("toolUseResult"))
        timestamp: str = Json.as_text(entry.get("timestamp"))
        if result.get("bashEditDiff"):
            return self._bash_edits(
                Json.as_dict(result["bashEditDiff"]), timestamp, self._command_of(entry)
            )
        if result.get("structuredPatch") and result.get("filePath"):
            return [
                self._hunk(
                    "tool",
                    Json.as_text(result["filePath"]),
                    Json.as_list(result["structuredPatch"]),
                    timestamp,
                    "",
                )
            ]
        return []

    def _bash_edits(
        self, diff: dict[str, object], timestamp: str, command: str
    ) -> list[EditHunk]:
        return [
            self._hunk(
                "bash",
                Json.as_text(Json.as_dict(file).get("filePath")),
                Json.as_list(Json.as_dict(file).get("hunks")),
                timestamp,
                command,
            )
            for file in Json.as_list(diff.get("files"))
        ]

    def _hunk(
        self,
        channel: str,
        path: str,
        hunks: list[object],
        timestamp: str,
        command: str,
    ) -> EditHunk:
        return EditHunk(
            self.get_identifier(),
            timestamp,
            channel,
            path,
            [line[1:] for line in self._hunk_lines(hunks) if line.startswith("+")],
            sum(1 for line in self._hunk_lines(hunks) if line.startswith("-")),
            command,
        )

    @staticmethod
    def _hunk_lines(hunks: list[object]) -> list[str]:
        return [
            Json.as_text(line)
            for hunk in hunks
            for line in Json.as_list(Json.as_dict(hunk).get("lines"))
        ]

    def _tool_uses(self) -> list[tuple[str, dict[str, object]]]:
        return [
            (
                Json.as_text(Json.as_dict(block)["name"]),
                self._arguments(Json.as_dict(block)),
            )
            for entry in self.__entries
            for block in Json.as_list(Json.as_dict(entry.get("message")).get("content"))
            if Json.as_dict(block).get("type") == "tool_use"
        ]

    @staticmethod
    def _arguments(block: dict[str, object]) -> dict[str, object]:
        return Json.as_dict(block.get("input"))

    @staticmethod
    def _text(entry: dict[str, object]) -> str:
        content: object = Json.as_dict(entry.get("message")).get("content")
        if isinstance(content, str):
            return content
        return "\n".join(
            Json.as_text(Json.as_dict(block).get("text"))
            for block in Json.as_list(content)
            if Json.as_dict(block).get("type") == "text"
        )

    @staticmethod
    def _read(path: pathlib.Path) -> list[dict[str, object]]:
        return [
            parsed
            for line in path.read_text(errors="ignore").splitlines()
            if line.strip()
            for parsed in (TranscriptSession._parse(line),)
            if parsed is not None
        ]

    @staticmethod
    def _parse(line: str) -> dict[str, object] | None:
        try:
            return Json.as_dict(json.loads(line)) or None
        except ValueError:
            return None


class TranscriptStore:
    """The transcripts on disk, filtered to one repository and time window.

    Args:
        projects (pathlib.Path): The directory holding one folder of transcripts per
            working directory.

    """

    def __init__(self, projects: pathlib.Path) -> None:

        self.__projects: pathlib.Path = projects

    def find_sessions(
        self, root: pathlib.Path, start: str, end: str
    ) -> list[TranscriptSession]:
        """Return the sessions worked inside a repository during a window.

        Args:
            root (pathlib.Path): The repository root.
            start (str): ISO 8601 window start.
            end (str): ISO 8601 window end.

        Returns:
            list[TranscriptSession]: Matching sessions, earliest first.

        """
        return sorted(
            (
                session
                for session in self._all_sessions()
                if self._in_repository(session, root)
                and self._overlaps(session, start, end)
            ),
            key=lambda session: session.get_span()[0],
        )

    def _all_sessions(self) -> list[TranscriptSession]:
        return [
            TranscriptSession(path)
            for path in sorted(self.__projects.glob("*/*.jsonl"))
        ]

    @staticmethod
    def _in_repository(session: TranscriptSession, root: pathlib.Path) -> bool:
        return any(
            resolved == str(root) or resolved.startswith(str(root) + "/")
            for directory in session.get_working_directories()
            for resolved in (str(pathlib.Path(directory).resolve()),)
        )

    @classmethod
    def _overlaps(cls, session: TranscriptSession, start: str, end: str) -> bool:
        return (
            bool(session.get_span()[0])
            and cls._moment(session.get_span()[1]) >= cls._moment(start)
            and cls._moment(session.get_span()[0]) <= cls._moment(end)
        )

    @staticmethod
    def _moment(timestamp: str) -> datetime.datetime:
        return datetime.datetime.fromisoformat(timestamp).astimezone(datetime.UTC)
