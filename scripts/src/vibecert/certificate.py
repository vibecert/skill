import datetime
import hashlib

from vibecert.bundle_types import Evidence
from vibecert.certificate_types import CertificateDocument, MetricResult, WeightResult
from vibecert.metrics import DeterministicMetrics
from vibecert.rubric import Thresholds
from vibecert.vibecert_types import Band
from vibecert.weights import Weights

ORDER: tuple[tuple[str, str], ...] = (
    ("follow_up_questions", "Follow-up questions"),
    ("coding_guidelines", "Coding guidelines"),
    ("output_amendments", "Output amendments"),
    ("prompt_granularity", "Prompt granularity"),
    ("secondary_tools", "Secondary tool usage"),
    ("generative_comments", "Generative comments"),
)


class Certificate:
    """The scored result for one branch.

    A metric is scored, not applicable where it ran and found nothing to
    measure, or not scored where no band reached us at all. The last is a
    failure rather than a finding, and is kept distinct so that a lost
    subagent cannot quietly shrink the denominator.

    Args:
        evidence (Evidence): The bundle for the branch under assessment.
        judged (list[Band]): The bands for the metrics that need judgement.
        private (bool): Whether to withhold the repository and branch names.

    """

    SCHEMA: str = "vibecert/certificate@1"

    def __init__(
        self, evidence: Evidence, judged: list[Band], private: bool = False
    ) -> None:
        self.__evidence: Evidence = evidence
        self.__private: bool = private
        self.__weights: Weights = Weights(evidence)
        self.__bands: dict[str, Band] = {
            band.metric: band
            for band in judged + DeterministicMetrics(evidence).get_bands()
        }

    def get_document(self) -> CertificateDocument:
        """Return the certificate, validated and ready to serialise.

        Returns:
            CertificateDocument: Everything the certificate records.

        """
        return CertificateDocument(
            schema_version=self.SCHEMA,
            rubrics_version=Thresholds.VERSION,
            issued_at=datetime.datetime.now(datetime.UTC).isoformat(),
            identifier=self.get_identifier(),
            private=self.__private,
            repository=None if self.__private else self.__evidence.repository.name,
            branch=None if self.__private else self.__evidence.branch.name,
            commits=len(self.__evidence.branch.commits),
            changed_lines=self.__evidence.diff.changed,
            generative_proportion=self.__evidence.attribution.touched_proportion,
            certified=self.__weights.is_certifiable(),
            score=self.get_score(),
            scored=len(self._scored()),
            applicable=sum(
                1 for metric in self.get_metrics() if metric.state != "not_applicable"
            ),
            weights=WeightResult(
                length=self.__weights.get_length(),
                criticality=self.__weights.get_criticality(),
                risk=self.__weights.get_risk(),
                applied=self.__weights.get_weight(),
            ),
            metrics=self.get_metrics(),
            findings=sorted(
                {
                    finding
                    for file in self.__evidence.diff.files
                    for finding in file.risk_signals
                }
            ),
        )

    def get_identifier(self) -> str:
        """Return the short identifier this certificate is published under.

        Returns:
            str: Seven characters, stable for a given repository, branch and head.

        """
        return hashlib.sha256(
            "\x1f".join(
                [
                    self.__evidence.repository.remote
                    or self.__evidence.repository.root,
                    self.__evidence.branch.name,
                    self.__evidence.branch.merge_base,
                ]
            ).encode()
        ).hexdigest()[:7]

    def get_metrics(self) -> list[MetricResult]:
        """Return each metric in rubric order, raw and adjusted.

        Returns:
            list[MetricResult]: One entry per metric the rubric defines.

        """
        return [
            MetricResult(
                number=number,
                name=name,
                title=title,
                state=self._state(name),
                raw=self._band(name).score,
                adjusted=self._adjusted(self._band(name).score),
                evidence=self._band(name).evidence,
            )
            for number, (name, title) in enumerate(ORDER, 1)
        ]

    def get_score(self) -> float | None:
        """Return the mean adjusted band over the metrics that apply.

        Returns:
            float | None: The score out of 3, or None where the branch did not
                pass the certification gate.

        """
        if not self.__weights.is_certifiable() or not self._scored():
            return None
        return round(sum(self._scored()) / len(self._scored()), 1)

    def _scored(self) -> list[int]:
        return [
            metric.adjusted
            for metric in self.get_metrics()
            if metric.adjusted is not None
        ]

    def get_weights(self) -> Weights:
        """Return the weights the branch carries.

        Returns:
            Weights: The length, criticality and risk bands, and their maximum.

        """
        return self.__weights

    def is_certifiable(self) -> bool:
        """Report whether the branch passed the certification gate.

        Returns:
            bool: False where the branch is mostly handwritten.

        """
        return self.__weights.is_certifiable()

    def _state(self, name: str) -> str:
        if name not in self.__bands:
            return "not_scored"
        return "scored" if self.__bands[name].score is not None else "not_applicable"

    def _band(self, name: str) -> Band:
        return self.__bands.get(name, Band(name, None, None, "no band was returned"))

    def _adjusted(self, score: int | None) -> int | None:
        return (
            Thresholds.LOOKUP[(score, self.__weights.get_weight())]
            if score is not None
            else None
        )
