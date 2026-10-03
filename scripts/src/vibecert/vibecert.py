import argparse
import json
import pathlib

from vibecert.collector import EvidenceCollector
from vibecert.git_repository import GitRepository
from vibecert.transcript import TranscriptStore


class Cli:
    """Command line entry point."""

    @staticmethod
    def run() -> None:
        """Collect evidence for a branch and write it as JSON."""
        arguments: argparse.Namespace = Cli._parser().parse_args()
        Cli._emit(
            json.dumps(
                EvidenceCollector(
                    GitRepository(pathlib.Path(arguments.repo)),
                    TranscriptStore(pathlib.Path(arguments.projects)),
                    arguments.base,
                    arguments.untracked,
                ).collect(),
                indent=1,
            ),
            arguments.out,
        )

    @staticmethod
    def _emit(bundle: str, out: str | None) -> None:
        if out:
            pathlib.Path(out).write_text(bundle)
        else:
            print(bundle)

    @staticmethod
    def _parser() -> argparse.ArgumentParser:
        parser: argparse.ArgumentParser = argparse.ArgumentParser(
            description="Collect VibeCert evidence for a Git branch"
        )
        parser.add_argument("--repo", default=".")
        parser.add_argument("--base", default="main")
        parser.add_argument(
            "--projects", default=str(pathlib.Path.home() / ".claude" / "projects")
        )
        parser.add_argument("--untracked", action="store_true")
        parser.add_argument("--out", default=None)
        return parser
