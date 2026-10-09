import pytest

from vibecert.make_targets import MakeTargets

MAKEFILE: list[str] = [
    ".PHONY: prettier test",
    "",
    "prettier:",
    "\tshfmt -w *.sh",
    "",
    "test lint: build",
    "\tsh test/foo_test.sh",
    "",
    "VERSION := 1.0",
]


class TestMakeTargets:
    @pytest.mark.parametrize(
        "command,expected",
        [
            ("make test", ["sh test/foo_test.sh"]),
            ("make lint", ["sh test/foo_test.sh"]),
            ("make", ["shfmt -w *.sh"]),
            ("make -j2 V=1 prettier", ["shfmt -w *.sh"]),
            ("make prettier test", ["shfmt -w *.sh", "sh test/foo_test.sh"]),
            ("make test 2>&1 | tail -1", ["sh test/foo_test.sh"]),
            ("make missing", []),
            ("cmake test", []),
            ("git status", []),
        ],
    )
    def test_expand_shell_command_returns_recipes_of_targets_made(
        self, command: str, expected: list[str]
    ) -> None:
        assert MakeTargets(MAKEFILE).expand(command) == expected

    def test_expand_no_makefile_returns_nothing(self) -> None:
        assert MakeTargets([]).expand("make test") == []
