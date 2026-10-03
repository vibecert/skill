import argparse
import dataclasses
import json
import pathlib

from vibecert.bundle_types import Evidence
from vibecert.collector import EvidenceCollector
from vibecert.evidence import EvidenceProjection
from vibecert.git_repository import GitRepository
from vibecert.metrics import DeterministicMetrics
from vibecert.transcript import TranscriptStore


class Cli:
    """Command line entry point."""

    @staticmethod
    def run() -> None:
        """Collect evidence for a branch and write it as JSON."""
        arguments: argparse.Namespace = Cli._parser().parse_args()
        Cli._emit(
            EvidenceCollector(
                GitRepository(pathlib.Path(arguments.repo)),
                TranscriptStore(pathlib.Path(arguments.projects)),
                arguments.base,
                arguments.untracked,
            )
            .collect()
            .model_dump_json(indent=1),
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


class MetricsCli:
    """Command line entry point for the metrics that need no judgement."""

    @staticmethod
    def run() -> None:
        """Score the deterministic metrics from a collected bundle."""
        arguments: argparse.Namespace = MetricsCli._parser().parse_args()
        Cli._emit(
            json.dumps(
                [
                    dataclasses.asdict(band)
                    for band in DeterministicMetrics(
                        MetricsCli._load(pathlib.Path(arguments.bundle))
                    ).get_bands()
                ],
                indent=1,
            ),
            arguments.out,
        )

    @staticmethod
    def _load(path: pathlib.Path) -> Evidence:
        evidence: Evidence = Evidence.model_validate_json(path.read_text())
        if evidence.schema_version != EvidenceCollector.SCHEMA:
            raise ValueError(
                f"bundle is {evidence.schema_version}, "
                f"expected {EvidenceCollector.SCHEMA}"
            )
        return evidence

    @staticmethod
    def _parser() -> argparse.ArgumentParser:
        parser: argparse.ArgumentParser = argparse.ArgumentParser(
            description="Score the deterministic VibeCert metrics"
        )
        parser.add_argument("bundle")
        parser.add_argument("--out", default=None)
        return parser


class EvidenceCli:
    """Command line entry point for the evidence one metric is scored from."""

    @staticmethod
    def run() -> None:
        """Print the slice of a collected bundle that one metric needs."""
        arguments: argparse.Namespace = EvidenceCli._parser().parse_args()
        Cli._emit(
            EvidenceProjection(
                MetricsCli._load(pathlib.Path(arguments.bundle))
            ).project(arguments.metric),
            arguments.out,
        )

    @staticmethod
    def _parser() -> argparse.ArgumentParser:
        parser: argparse.ArgumentParser = argparse.ArgumentParser(
            description="Print the evidence for one VibeCert metric"
        )
        parser.add_argument("bundle")
        parser.add_argument("metric", choices=EvidenceProjection.METRICS)
        parser.add_argument("--out", default=None)
        return parser
