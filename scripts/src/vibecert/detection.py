import pathlib
import re

from vibecert.vibecert_types import CheckClass


class Languages:
    """Where a comment starts, for the file types comment density applies to."""

    MARKERS: dict[str, str] = {
        ".py": "#",
        ".sh": "#",
        ".rb": "#",
        ".tf": "#",
        ".yaml": "#",
        ".yml": "#",
        ".toml": "#",
        ".js": "//",
        ".jsx": "//",
        ".ts": "//",
        ".tsx": "//",
        ".go": "//",
        ".java": "//",
        ".c": "//",
        ".cpp": "//",
        ".rs": "//",
        ".sql": "--",
    }

    @classmethod
    def get_marker(cls, suffix: str) -> str:
        """Return the comment marker for a file type.

        Args:
            suffix (str): The file suffix, including its leading dot.

        Returns:
            str: The marker, or an empty string where density does not apply.

        """
        return cls.MARKERS.get(suffix, "")


class CheckRegistry:
    """The classes of automated check, in descending order of what they establish."""

    CLASSES: tuple[CheckClass, ...] = (
        CheckClass(
            "behavioural",
            frozenset(
                {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".java", ".rs", ".sh"}
            ),
            {
                "pytest.ini": "",
                "tox.ini": "",
                "pyproject.toml": "[tool.pytest",
                "package.json": '"test"',
                "Cargo.toml": "[[test]]",
            },
            frozenset(
                {
                    "pytest",
                    "jest",
                    "vitest",
                    "go test",
                    "cargo test",
                    "npm test",
                    "make test",
                    "shunit2",
                    "bats",
                }
            ),
        ),
        CheckClass(
            "static",
            frozenset(
                {
                    ".py",
                    ".js",
                    ".jsx",
                    ".ts",
                    ".tsx",
                    ".go",
                    ".rs",
                    ".sh",
                    ".tf",
                    ".md",
                    ".yaml",
                    ".yml",
                }
            ),
            {
                "ruff.toml": "",
                "mypy.ini": "",
                ".eslintrc": "",
                ".eslintrc.json": "",
                "eslint.config.js": "",
                ".markdownlint.json": "",
                ".yamllint": "",
                ".shellcheckrc": "",
                "tsconfig.json": "",
                "pyproject.toml": "[tool.ruff.lint",
            },
            frozenset(
                {
                    "ruff check",
                    "eslint",
                    "mypy",
                    "ty check",
                    "pyright",
                    "markdownlint",
                    "shellcheck",
                    "sh -n",
                    "bash -n",
                    "tflint",
                    "yamllint",
                    "tsc",
                }
            ),
        ),
        CheckClass(
            "format",
            frozenset(
                {
                    ".py",
                    ".js",
                    ".jsx",
                    ".ts",
                    ".tsx",
                    ".go",
                    ".rs",
                    ".md",
                    ".json",
                    ".sh",
                }
            ),
            {
                ".prettierrc": "",
                ".editorconfig": "",
                "ruff.toml": "",
                "pyproject.toml": "[tool.ruff",
            },
            frozenset(
                {"ruff format", "prettier", "black", "gofmt", "rustfmt", "shfmt"}
            ),
        ),
    )

    RUNNERS: frozenset[str] = frozenset(
        {"Makefile", ".gitlab-ci.yml", ".pre-commit-config.yaml"}
    )

    WORKFLOWS: str = ".github/workflows/"

    @classmethod
    def configured_by(cls, path: str, content: str) -> list[str]:
        """Return the check classes a file establishes.

        A configuration file establishes a class by its name and contents. A file
        that runs commands, such as a CI workflow or a Makefile, establishes the
        classes whose commands it invokes.

        Args:
            path (str): The repository-relative path of the file.
            content (str): The file's contents.

        Returns:
            list[str]: Names of the classes the file configures, possibly none.

        """
        name: str = pathlib.PurePath(path).name
        return [
            check.name
            for check in cls.CLASSES
            if (name in check.configs and check.configs[name] in content)
            or (
                cls.is_runner(path)
                and any(cls.invokes(content, command) for command in check.commands)
            )
        ]

    @classmethod
    def is_runner(cls, path: str) -> bool:
        """Return whether a file runs commands, as a CI workflow or Makefile does.

        Args:
            path (str): The repository-relative path of the file.

        Returns:
            bool: Whether the file can configure checks by invoking them.

        """
        return pathlib.PurePath(path).name in cls.RUNNERS or path.startswith(
            cls.WORKFLOWS
        )

    @staticmethod
    def invokes(text: str, command: str) -> bool:
        """Return whether text invokes a command as a whole word.

        Args:
            text (str): A shell command, or a file of them.
            command (str): The command to look for, such as "sh -n".

        Returns:
            bool: Whether the command appears without letters, digits or hyphens
                either side, so "sh -n" is not found inside "git push -n".

        """
        return re.search(rf"(?<![\w-]){re.escape(command)}(?![\w-])", text) is not None


class SensitiveData:
    """Domain terms that mark code as handling personal data."""

    TERMS: re.Pattern[str] = re.compile(
        r"\b(nhs_?number|patient|date_?of_?birth|national_?insurance|postcode|"
        r"medical_?record|diagnosis)",
        re.IGNORECASE,
    )

    QUOTED: re.Pattern[str] = re.compile(r"""(['"]).*?\1|\#.*|//.*""")

    @classmethod
    def scan(cls, lines: list[str]) -> list[str]:
        """Return whether a file's added lines name personal data.

        Args:
            lines (list[str]): The lines the diff adds to the file.

        Returns:
            list[str]: A single entry naming the category, or nothing.

        """
        return (
            ["personal data referenced"]
            if any(cls.TERMS.search(cls.QUOTED.sub("", line)) for line in lines)
            else []
        )


class ImportPatterns:
    """How one file refers to another, for the criticality weight."""

    TEMPLATES: dict[str, str] = {
        ".py": r"^\s*(?:from|import)\s+[\w.]*\b{stem}\b",
        ".js": r"(?:from|require\()\s*['\"][^'\"]*\b{stem}\b",
        ".jsx": r"(?:from|require\()\s*['\"][^'\"]*\b{stem}\b",
        ".ts": r"(?:from|require\()\s*['\"][^'\"]*\b{stem}\b",
        ".tsx": r"(?:from|require\()\s*['\"][^'\"]*\b{stem}\b",
        ".go": r"^\s*import\s+[^\n]*\b{stem}\b",
    }

    @classmethod
    def get_pattern(cls, suffix: str, stem: str) -> re.Pattern[str] | None:
        """Return the expression matching an import of a module.

        Args:
            suffix (str): The imported file's suffix, including its leading dot.
            stem (str): The imported file's name without its suffix.

        Returns:
            re.Pattern[str] | None: The expression, or None where imports cannot
                be identified for the file type.

        """
        return (
            re.compile(cls.TEMPLATES[suffix].format(stem=re.escape(stem)), re.MULTILINE)
            if suffix in cls.TEMPLATES
            else None
        )


class RiskSeverity:
    """Which security findings can do harm outside the process."""

    SEVERE: tuple[str, ...] = (
        "S105",
        "S106",
        "S107",
        "S602",
        "S603",
        "S604",
        "S605",
        "S606",
        "S607",
        "S608",
        "personal data",
    )

    @classmethod
    def is_severe(cls, findings: list[str]) -> bool:
        """Report whether any finding belongs to a class that can do harm.

        Args:
            findings (list[str]): The findings recorded against the changed files.

        Returns:
            bool: True where at least one is credentials, personal data, shell
                execution or assembled SQL.

        """
        return any(
            finding.startswith(severe) or severe in finding
            for finding in findings
            for severe in cls.SEVERE
        )


class GenerativeCommits:
    """Commit message lines that credit a generative tool."""

    PATTERN: re.Pattern[str] = re.compile(
        r"^(co-authored-by:|.*\bgenerated (with|by)\b).*"
        r"\b(claude|anthropic\.com|copilot|cursor|aider|codex|gemini|devin)\b",
        re.IGNORECASE | re.MULTILINE,
    )
