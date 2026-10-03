from vibecert.bundle_types import Evidence, FileInfo
from vibecert.rubric import Thresholds
from vibecert.vibecert_types import Band


class AmendmentMetric:
    """Metric 3, how far the output was altered rather than accepted as delivered.

    Args:
        evidence (Evidence): The bundle for the branch under assessment.

    """

    NAME: str = "output_amendments"

    def __init__(self, evidence: Evidence) -> None:
        self.__revised: int = evidence.attribution.revised
        self.__touched: int = evidence.attribution.touched
        self.__rate: float = evidence.attribution.revised_proportion

    def get_band(self) -> Band:
        """Return the band, measured over the files the model wrote to.

        Returns:
            Band: The score, the amendment rate, and what placed it there.

        """
        if not self.__touched:
            return Band(self.NAME, None, None, "no generated files on the branch")
        return Band(
            self.NAME,
            self._score(),
            self.__rate,
            f"{self.__revised} of {self.__touched} generated lines were rewritten "
            f"after the author challenged them",
        )

    def _score(self) -> int:
        if self.__rate < Thresholds.AMENDMENT_LOW:
            return 1
        return 2 if self.__rate <= Thresholds.AMENDMENT_HIGH else 3


class SecondaryToolMetric:
    """Metric 5, whether automated checks were present, covered the change and ran.

    Args:
        evidence (Evidence): The bundle for the branch under assessment.

    """

    NAME: str = "secondary_tools"

    def __init__(self, evidence: Evidence) -> None:
        self.__applicable: list[str] = evidence.activity.checks.applicable
        self.__configured: list[str] = evidence.activity.checks.configured
        self.__ran: list[str] = evidence.activity.checks.ran

    def get_band(self) -> Band:
        """Return the band, judged against the strongest check the diff admits.

        Returns:
            Band: The score, no measure, and what placed it there.

        """
        if not self.__applicable:
            return Band(
                self.NAME, None, None, "no class of check applies to these file types"
            )
        return Band(self.NAME, self._score(), None, self._evidence())

    def _score(self) -> int:
        if self._highest() in self.__configured and self._highest() in self.__ran:
            return 3
        if self._highest() in self.__configured or self._lower_ran():
            return 2
        return 1

    def _evidence(self) -> str:
        configured: str = (
            "configured" if self._highest() in self.__configured else "not configured"
        )
        ran: str = "ran" if self._highest() in self.__ran else "did not run"
        return f"{self._highest()} checks {configured} and {ran}"

    def _highest(self) -> str:
        return self.__applicable[0]

    def _lower_ran(self) -> bool:
        return any(name in self.__ran for name in self.__applicable[1:])


class CommentMetric:
    """Metric 6, narration added to generated code, scored inversely.

    Args:
        evidence (Evidence): The bundle for the branch under assessment.

    """

    NAME: str = "generative_comments"

    def __init__(self, evidence: Evidence) -> None:
        self.__files: list[FileInfo] = [
            file for file in evidence.diff.files if file.touched and file.code
        ]
        self.__baseline: float = evidence.repository.comment_density

    def get_band(self) -> Band:
        """Return the band, measured over generated code the metric applies to.

        Returns:
            Band: The score, the comment density, and what placed it there.

        """
        if not self._code():
            return Band(
                self.NAME, None, None, "no generated code this metric applies to"
            )
        return Band(
            self.NAME,
            self._score(),
            self._density(),
            f"{self._comments()} comment lines over {self._code()} lines of code, "
            f"against a repository baseline of {self.__baseline}",
        )

    def _score(self) -> int:
        if self._density() < max(Thresholds.COMMENT_LOW, self.__baseline):
            return 3
        return 2 if self._density() <= Thresholds.COMMENT_HIGH else 1

    def _density(self) -> float:
        return round(self._comments() / self._code(), 3)

    def _comments(self) -> int:
        return sum(file.comments for file in self.__files)

    def _code(self) -> int:
        return sum(file.code for file in self.__files)


class DeterministicMetrics:
    """The metrics that are counted rather than judged.

    Args:
        evidence (Evidence): The bundle for the branch under assessment.

    """

    def __init__(self, evidence: Evidence) -> None:
        self.__evidence: Evidence = evidence

    def get_bands(self) -> list[Band]:
        """Return a band for each metric needing no judgement.

        Returns:
            list[Band]: Bands for metrics 3, 5 and 6, in that order.

        """
        return [
            AmendmentMetric(self.__evidence).get_band(),
            SecondaryToolMetric(self.__evidence).get_band(),
            CommentMetric(self.__evidence).get_band(),
        ]
