import argparse
import dataclasses
import json
import pathlib

from vibecert.bundle_types import Evidence
from vibecert.certificate import Certificate
from vibecert.certificate_types import CertificateDocument
from vibecert.collector import EvidenceCollector
from vibecert.evidence import EvidenceProjection
from vibecert.git_repository import GitRepository
from vibecert.json_values import Json
from vibecert.metrics import DeterministicMetrics
from vibecert.render import CertificateMarkdown
from vibecert.transcript import TranscriptStore
from vibecert.vibecert_types import Band


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


class ScoreCli:
    """Command line entry point for the certificate."""

    @staticmethod
    def run() -> None:
        """Combine the judged bands with the evidence and render a certificate."""
        arguments: argparse.Namespace = ScoreCli._parser().parse_args()
        Cli._emit(
            ScoreCli._format(
                Certificate(
                    MetricsCli._load(pathlib.Path(arguments.bundle)),
                    ScoreCli._judged(pathlib.Path(arguments.judged)),
                    arguments.private,
                ).get_document(),
                arguments.format,
            ),
            arguments.out,
        )

    @staticmethod
    def _format(document: CertificateDocument, style: str) -> str:
        return (
            document.model_dump_json(indent=1)
            if style == "json"
            else CertificateMarkdown(document).render()
        )

    @staticmethod
    def _judged(path: pathlib.Path) -> list[Band]:
        return [
            Band(
                Json.as_text(Json.as_dict(band).get("metric")),
                ScoreCli._score(Json.as_dict(band).get("score")),
                None,
                Json.as_text(Json.as_dict(band).get("evidence")),
            )
            for band in Json.as_list(json.loads(path.read_text()))
        ]

    @staticmethod
    def _score(value: object) -> int | None:
        return value if isinstance(value, int) else None

    @staticmethod
    def _parser() -> argparse.ArgumentParser:
        parser: argparse.ArgumentParser = argparse.ArgumentParser(
            description="Render a VibeCert certificate"
        )
        parser.add_argument("bundle")
        parser.add_argument("judged")
        parser.add_argument(
            "--format", choices=("markdown", "json"), default="markdown"
        )
        parser.add_argument("--private", action="store_true")
        parser.add_argument("--out", default=None)
        return parser
