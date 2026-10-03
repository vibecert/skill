import pathlib
import typing
import unittest.mock

import pytest
import pytest_mock

from vibecert.transcript import TranscriptSession, TranscriptStore
from vibecert.vibecert_types import EditHunk


def session_of(
    mocker: pytest_mock.MockerFixture, entries: list[dict[str, object]]
) -> TranscriptSession:
    mocker.patch.object(TranscriptSession, "_read", return_value=entries)
    return TranscriptSession(pathlib.Path("/projects/repo/session.jsonl"))


class TestTranscriptSession:
    HUMAN: typing.ClassVar[dict[str, object]] = {
        "type": "user",
        "origin": {"kind": "human"},
        "timestamp": "2026-01-01T00:00:00Z",
        "message": {"role": "user", "content": "why line 41?"},
        "cwd": "/repo",
    }
    HOOK: typing.ClassVar[dict[str, object]] = {
        "type": "user",
        "origin": {"kind": "hook"},
        "message": {},
    }
    SIDECHAIN: typing.ClassVar[dict[str, object]] = {
        "type": "user",
        "origin": {"kind": "human"},
        "isSidechain": True,
        "message": {},
    }

    def test_get_identifier_transcript_file_returns_stem(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        assert session_of(mocker, []).get_identifier() == "session"

    def test_get_path_transcript_file_returns_path(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        assert session_of(mocker, []).get_path().name == "session.jsonl"

    def test_get_working_directories_entries_present_returns_set(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        assert session_of(mocker, [self.HUMAN]).get_working_directories() == {"/repo"}

    def test_get_span_no_timestamps_returns_empty(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        assert session_of(mocker, [self.HOOK]).get_span() == ("", "")

    def test_get_span_timestamps_present_returns_first_and_last(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        assert session_of(mocker, [self.HUMAN]).get_span() == (
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:00:00Z",
        )

    def test_get_prompts_mixed_origins_returns_human_only(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        assert [
            prompt.text
            for prompt in session_of(
                mocker, [self.HUMAN, self.HOOK, self.SIDECHAIN]
            ).get_prompts()
        ] == ["why line 41?"]

    def test_get_prompts_block_content_returns_joined_text(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        assert (
            session_of(
                mocker,
                [
                    self.HUMAN
                    | {
                        "message": {
                            "content": [
                                {"type": "text", "text": "foo"},
                                {"type": "image"},
                            ]
                        }
                    }
                ],
            )
            .get_prompts()[0]
            .text
            == "foo"
        )

    def test_get_edits_bash_channel_returns_added_lines(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        assert session_of(
            mocker,
            [
                {
                    "toolUseResult": {
                        "bashEditDiff": {
                            "files": [
                                {
                                    "filePath": "/repo/foo.py",
                                    "hunks": [{"lines": ["+alpha", "-beta", " gamma"]}],
                                }
                            ]
                        }
                    }
                }
            ],
        ).get_edits() == [
            EditHunk("session", "", "bash", "/repo/foo.py", ["alpha"], 1, "")
        ]

    def test_get_edits_tool_channel_returns_added_lines(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        assert (
            session_of(
                mocker,
                [
                    {
                        "toolUseResult": {
                            "filePath": "/repo/foo.py",
                            "structuredPatch": [{"lines": ["+alpha"]}],
                        }
                    }
                ],
            )
            .get_edits()[0]
            .channel
            == "tool"
        )

    def test_get_edits_no_edit_result_returns_empty(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        assert (
            session_of(
                mocker, [{"toolUseResult": {"stdout": "foo"}}, self.HUMAN]
            ).get_edits()
            == []
        )

    def test_get_tool_counts_tool_uses_returns_histogram(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        assert session_of(
            mocker, [self._tool_use("Bash", {"command": "ls"})]
        ).get_tool_counts() == {"Bash": 1}

    def test_get_bash_commands_bash_calls_returns_commands(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        assert session_of(
            mocker,
            [self._tool_use("Bash", {"command": "ls"}), self._tool_use("Read", {})],
        ).get_bash_commands() == ["ls"]

    def test_get_guidelines_read_rule_path_in_command_returns_path(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        assert session_of(
            mocker,
            [self._tool_use("Bash", {"command": "cat ~/.claude/rules/python/FOO.md"})],
        ).get_guidelines_read() == {"~/.claude/rules/python/FOO.md"}

    def test_get_guidelines_in_context_instructions_attachment_returns_paths(
        self, mocker: pytest_mock.MockerFixture
    ) -> None:
        assert session_of(
            mocker,
            [
                {
                    "type": "attachment",
                    "attachment": {
                        "type": "instructions",
                        "files": [{"path": "/rules/FOO.md"}],
                    },
                }
            ],
        ).get_guidelines_in_context() == {"/rules/FOO.md"}

    def test_parse_malformed_line_returns_none(self) -> None:
        assert TranscriptSession._parse("{not json") is None

    @staticmethod
    def _tool_use(name: str, arguments: dict[str, object]) -> dict[str, object]:
        return {
            "type": "assistant",
            "message": {
                "content": [{"type": "tool_use", "name": name, "input": arguments}]
            },
        }


class TestTranscriptStore:
    @pytest.fixture
    def store_mocks(self, mocker: pytest_mock.MockerFixture) -> unittest.mock.MagicMock:
        return mocker.patch.object(TranscriptStore, "_all_sessions")

    def test_find_sessions_inside_repository_and_window_returns_session(
        self, store_mocks: unittest.mock.MagicMock
    ) -> None:
        store_mocks.return_value = [
            self._session("/repo/sub", ("2026-01-02", "2026-01-03"))
        ]
        assert (
            len(
                TranscriptStore(pathlib.Path("/projects")).find_sessions(
                    pathlib.Path("/repo"), "2026-01-01", "2026-01-04"
                )
            )
            == 1
        )

    def test_find_sessions_symlinked_working_directory_resolves_to_repository(
        self, store_mocks: unittest.mock.MagicMock, mocker: pytest_mock.MockerFixture
    ) -> None:
        store_mocks.return_value = [
            self._session("/link/sub", ("2026-01-02", "2026-01-03"))
        ]
        mocker.patch.object(
            pathlib.Path, "resolve", return_value=pathlib.Path("/repo/sub")
        )
        assert (
            len(
                TranscriptStore(pathlib.Path("/projects")).find_sessions(
                    pathlib.Path("/repo"), "2026-01-01", "2026-01-04"
                )
            )
            == 1
        )

    @pytest.mark.parametrize(
        "directory,span",
        [
            ("/other", ("2026-01-02", "2026-01-03")),
            ("/repo", ("2026-01-05", "2026-01-06")),
            ("/repo", ("", "")),
        ],
    )
    def test_find_sessions_outside_repository_or_window_returns_empty(
        self,
        store_mocks: unittest.mock.MagicMock,
        directory: str,
        span: tuple[str, str],
    ) -> None:
        store_mocks.return_value = [self._session(directory, span)]
        assert (
            TranscriptStore(pathlib.Path("/projects")).find_sessions(
                pathlib.Path("/repo"), "2026-01-01", "2026-01-04"
            )
            == []
        )

    @staticmethod
    def _session(directory: str, span: tuple[str, str]) -> unittest.mock.MagicMock:
        session: unittest.mock.MagicMock = unittest.mock.MagicMock()
        session.get_working_directories.return_value = {directory}
        session.get_span.return_value = span
        return session
