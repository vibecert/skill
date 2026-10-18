import pytest

from vibecert.detection import (
    CheckRegistry,
    GenerativeCommits,
    ImportPatterns,
    Languages,
    RiskSeverity,
    SensitiveData,
)


class TestSensitiveData:
    @pytest.mark.parametrize(
        "line,expected",
        [
            ("patient_record = load()", ["personal data referenced"]),
            ("nhs_number = read()", ["personal data referenced"]),
            ("self.patient.save()", ["personal data referenced"]),
            ("total = one + two", []),
            ('raise ValueError("no patient found")', []),
            ("# the patient record is loaded elsewhere", []),
            ('TERMS = re.compile(r"nhs_?number|patient")', []),
        ],
    )
    def test_scan_added_lines_returns_category_when_named(
        self, line: str, expected: list[str]
    ) -> None:
        assert SensitiveData.scan([line]) == expected


class TestImportPatterns:
    def test_get_pattern_known_suffix_returns_expression(self) -> None:
        assert ImportPatterns.get_pattern(".py", "foo") is not None

    def test_get_pattern_unknown_suffix_returns_none(self) -> None:
        assert ImportPatterns.get_pattern(".md", "foo") is None


class TestLanguages:
    @pytest.mark.parametrize(
        "suffix,expected", [(".py", "#"), (".ts", "//"), (".sql", "--"), (".md", "")]
    )
    def test_get_marker_file_suffix_returns_marker_or_empty(
        self, suffix: str, expected: str
    ) -> None:
        assert Languages.get_marker(suffix) == expected


class TestCheckRegistry:
    @pytest.mark.parametrize(
        "name,content,expected",
        [
            ("pytest.ini", "", ["behavioural"]),
            ("pyproject.toml", "[tool.pytest.ini_options]", ["behavioural"]),
            ("pyproject.toml", "[tool.ruff.lint]", ["static", "format"]),
            ("pyproject.toml", "[project]", []),
            (".markdownlint.json", "{}", ["static"]),
            (".shellcheckrc", "", ["static"]),
            ("README.md", "", []),
            ("README.md", "make test", []),
            ("Makefile", "prettier:\n\tshfmt -w *.sh", ["format"]),
            (
                ".github/workflows/ci.yml",
                "run: find . -name '*.sh' | xargs sh -n\nrun: make test",
                ["behavioural", "static"],
            ),
            (".github/workflows/release.yml", "run: git push -n origin", []),
            (".pre-commit-config.yaml", "entry: shellcheck", ["static"]),
        ],
    )
    def test_configured_by_file_contents_returns_classes_it_establishes(
        self, name: str, content: str, expected: list[str]
    ) -> None:
        assert CheckRegistry.configured_by(name, content) == expected

    @pytest.mark.parametrize(
        "path,expected",
        [
            ("Makefile", True),
            ("tools/Makefile", True),
            (".github/workflows/ci.yml", True),
            (".gitlab-ci.yml", True),
            (".github/dependabot.yml", False),
            ("ruff.toml", False),
        ],
    )
    def test_is_runner_file_path_reports_whether_it_runs_commands(
        self, path: str, expected: bool
    ) -> None:
        assert CheckRegistry.is_runner(path) is expected

    @pytest.mark.parametrize(
        "text,command,expected",
        [
            ("sh -n passs.sh", "sh -n", True),
            ("xargs -0 -n 1 sh -n", "sh -n", True),
            ("git push -n origin", "sh -n", False),
            ("bash -n foo.sh", "sh -n", False),
            ("uv run pytest -q", "pytest", True),
            ("uv run pytest-cov", "pytest", False),
            ("cd foo && make test 2>&1", "make test", True),
            ("make tests", "make test", False),
        ],
    )
    def test_invokes_command_text_matches_whole_words_only(
        self, text: str, command: str, expected: bool
    ) -> None:
        assert CheckRegistry.invokes(text, command) is expected


class TestRiskSeverity:
    @pytest.mark.parametrize(
        "findings,expected",
        [
            ([], False),
            (["S113: requests call without timeout"], False),
            (["S101: assert detected"], False),
            (["S602: subprocess call with shell=True"], True),
            (["S105: possible hardcoded password"], True),
            (["S608: possible SQL injection"], True),
            (["personal data referenced"], True),
            (["S113: no timeout", "S607: partial executable path"], True),
        ],
    )
    def test_is_severe_findings_reports_whether_any_can_do_harm(
        self, findings: list[str], expected: bool
    ) -> None:
        assert RiskSeverity.is_severe(findings) is expected


class TestGenerativeCommits:
    @pytest.mark.parametrize(
        "message,expected",
        [
            ("feat: foo\n\nCo-Authored-By: Claude <noreply@anthropic.com>", True),
            ("feat: foo\n\nGenerated with [Claude Code](https://foo.bar)", True),
            ("feat: foo\n\nco-authored-by: Copilot <foo@bar.baz>", True),
            ("feat: foo\n\nCo-authored-by: Foo Bar <foo@bar.baz>", False),
            ("feat: add claude support", False),
        ],
    )
    def test_pattern_commit_message_matches_generative_tools(
        self, message: str, expected: bool
    ) -> None:
        assert (GenerativeCommits.PATTERN.search(message) is not None) is expected
