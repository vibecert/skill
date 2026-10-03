from vibecert.bundle_types import Evidence
from vibecert.metrics import DeterministicMetrics
from vibecert.rubric import Thresholds
from vibecert.vibecert_types import Band, ScoredMetric
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

    Args:
        evidence (Evidence): The bundle for the branch under assessment.
        judged (list[Band]): The bands for the metrics that need judgement.

    """

    def __init__(self, evidence: Evidence, judged: list[Band]) -> None:
        self.__evidence: Evidence = evidence
        self.__weights: Weights = Weights(evidence)
        self.__bands: dict[str, Band] = {
            band.metric: band
            for band in judged + DeterministicMetrics(evidence).get_bands()
        }

    def get_metrics(self) -> list[ScoredMetric]:
        """Return each metric in rubric order, raw and adjusted.

        Returns:
            list[ScoredMetric]: One entry per metric the rubric defines.

        """
        return [
            ScoredMetric(
                number,
                title,
                self._band(name).score,
                self._adjusted(self._band(name).score),
                self._band(name).evidence,
            )
            for number, (name, title) in enumerate(ORDER, 1)
        ]

    def get_score(self) -> float | None:
        """Return the mean adjusted band over the metrics that apply.

        Returns:
            float | None: The score out of 3, or None where the branch did not
                pass the certification gate.

        """
        if not self.__weights.is_certifiable():
            return None
        scored: list[int] = [
            metric.adjusted
            for metric in self.get_metrics()
            if metric.adjusted is not None
        ]
        return round(sum(scored) / len(scored), 1) if scored else None

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

    def get_evidence(self) -> Evidence:
        """Return the bundle the certificate was scored from.

        Returns:
            Evidence: The evidence bundle.

        """
        return self.__evidence

    def _band(self, name: str) -> Band:
        return self.__bands.get(name, Band(name, None, None, "not scored"))

    def _adjusted(self, score: int | None) -> int | None:
        return (
            Thresholds.LOOKUP[(score, self.__weights.get_weight())]
            if score is not None
            else None
        )
