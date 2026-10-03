from vibecert.bundle_types import Evidence
from vibecert.detection import RiskSeverity
from vibecert.rubric import Thresholds


class Weights:
    """How much good practice mattered on the branch under assessment.

    Args:
        evidence (Evidence): The bundle for the branch under assessment.

    """

    def __init__(self, evidence: Evidence) -> None:
        self.__evidence: Evidence = evidence

    def is_certifiable(self) -> bool:
        """Report whether enough of the branch is generated to be worth scoring.

        Returns:
            bool: False where the branch is mostly handwritten.

        """
        return self.__evidence.attribution.touched_proportion >= Thresholds.GATE

    def get_weight(self) -> int:
        """Return the weight the branch carries, being the highest that applies.

        Returns:
            int: The band, from 1 to 3.

        """
        return max(self.get_length(), self.get_criticality(), self.get_risk())

    def get_length(self) -> int:
        """Return the band for how much the branch changed.

        Returns:
            int: The band, from 1 to 3.

        """
        if self.__evidence.diff.changed < Thresholds.LENGTH_LOW:
            return 1
        return 2 if self.__evidence.diff.changed <= Thresholds.LENGTH_HIGH else 3

    def get_criticality(self) -> int:
        """Return the band for how much of the system depends on the change.

        Returns:
            int: The band, from 1 to 3.

        """
        if self._rank() < Thresholds.CRITICALITY_LOW:
            return 1
        return 2 if self._rank() <= Thresholds.CRITICALITY_HIGH else 3

    def _rank(self) -> float:
        distribution: list[int] = self.__evidence.repository.fan_in_distribution
        return (
            sum(1 for other in distribution if other <= self._fan_in())
            / len(distribution)
            if distribution
            else 0.0
        )

    def get_risk(self) -> int:
        """Return the band for what the change could do if it is wrong.

        Returns:
            int: The band, from 1 to 3.

        """
        if not self._findings():
            return 1
        return 3 if RiskSeverity.is_severe(self._findings()) else 2

    def _fan_in(self) -> int:
        return max((file.fan_in for file in self.__evidence.diff.files), default=0)

    def _findings(self) -> list[str]:
        return [
            finding
            for file in self.__evidence.diff.files
            for finding in file.risk_signals
        ]
