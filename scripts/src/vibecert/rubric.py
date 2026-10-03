from vibecert.vibecert_types import CheckClass


class Thresholds:
    """Band boundaries, fixed from published measurement."""

    AMENDMENT_LOW: float = 0.05
    AMENDMENT_HIGH: float = 0.15
    COMMENT_LOW: float = 0.10
    COMMENT_HIGH: float = 0.20
    GATE: float = 0.25
    LENGTH_LOW: int = 200
    LENGTH_HIGH: int = 800
    PROMPT_LOW: int = 50
    PROMPT_HIGH: int = 200


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
