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
            frozenset({".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".java", ".rs"}),
            {
                "pytest.ini": "",
                "tox.ini": "",
                "pyproject.toml": "[tool.pytest",
                "package.json": '"test"',
                "Cargo.toml": "[[test]]",
            },
            frozenset(
                {"pytest", "jest", "vitest", "go test", "cargo test", "npm test"}
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
                    "tflint",
                    "yamllint",
                    "tsc",
                }
            ),
        ),
        CheckClass(
            "format",
            frozenset(
                {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".md", ".json"}
            ),
            {
                ".prettierrc": "",
                ".editorconfig": "",
                "ruff.toml": "",
                "pyproject.toml": "[tool.ruff",
            },
            frozenset({"ruff format", "prettier", "black", "gofmt", "rustfmt"}),
        ),
    )

    @classmethod
    def configured_by(cls, name: str, content: str) -> list[str]:
        """Return the check classes a configuration file establishes.

        Args:
            name (str): The file name, without its directory.
            content (str): The file's contents.

        Returns:
            list[str]: Names of the classes the file configures, possibly none.

        """
        return [
            check.name
            for check in cls.CLASSES
            if name in check.configs and check.configs[name] in content
        ]


class SensitiveData:
    """Domain terms that mark code as handling personal data."""

    TERMS: re.Pattern[str] = re.compile(
        r"\b(nhs_?number|patient|date_?of_?birth|national_?insurance|postcode|"
        r"medical_?record|diagnosis)",
        re.IGNORECASE,
    )

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
            if any(cls.TERMS.search(line) for line in lines)
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
