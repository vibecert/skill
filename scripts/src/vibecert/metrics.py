from vibecert.bundle_types import Evidence, FileInfo
from vibecert.rubric import CheckRegistry, Languages, Thresholds
from vibecert.vibecert_types import Band, CheckClass


class AmendmentMetric:
    """Metric 3, how far the output was altered rather than accepted as delivered.

    Args:
        evidence (Evidence): The bundle for the branch under assessment.

    """

    NAME: str = "output_amendments"

    def __init__(self, evidence: Evidence) -> None:
        self.__files: list[FileInfo] = [
            file for file in evidence.diff.files if file.touched
        ]

    def get_band(self) -> Band:
        """Return the band, measured over the files the model wrote to.

        Returns:
            Band: The score, the amendment rate, and what placed it there.

        """
        if not self._added():
            return Band(self.NAME, None, None, "no generated files on the branch")
        return Band(
            self.NAME,
            self._score(),
            self._rate(),
            f"{self._human()} of {self._added()} added lines in generated files "
            f"were not written by a tool call",
        )

    def _score(self) -> int:
        if self._rate() < Thresholds.AMENDMENT_LOW:
            return 1
        return 2 if self._rate() <= Thresholds.AMENDMENT_HIGH else 3

    def _rate(self) -> float:
        return round(self._human() / self._added(), 3)

    def _human(self) -> int:
        return sum(file.human for file in self.__files)

    def _added(self) -> int:
        return sum(file.added for file in self.__files)


class SecondaryToolMetric:
    """Metric 5, whether automated checks were present, covered the change and ran.

    Args:
        evidence (Evidence): The bundle for the branch under assessment.

    """

    NAME: str = "secondary_tools"

    def __init__(self, evidence: Evidence) -> None:
        self.__applicable: tuple[CheckClass, ...] = self._applicable(
            {file.suffix for file in evidence.diff.files}
        )
        self.__configured: set[str] = {
            name for names in evidence.activity.check_configs.values() for name in names
        }
        self.__commands: list[str] = evidence.activity.bash_commands

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
        if self._configured(self._highest()) and self._ran(self._highest()):
            return 3
        if self._configured(self._highest()) or self._lower_ran():
            return 2
        return 1

    def _evidence(self) -> str:
        return (
            f"{self._highest().name} checks "
            f"{'configured' if self._configured(self._highest()) else 'not configured'}"
            f" and {'ran' if self._ran(self._highest()) else 'did not run'}"
        )

    def _highest(self) -> CheckClass:
        return self.__applicable[0]

    def _lower_ran(self) -> bool:
        return any(self._ran(check) for check in self.__applicable[1:])

    @staticmethod
    def _applicable(suffixes: set[str]) -> tuple[CheckClass, ...]:
        return tuple(
            check for check in CheckRegistry.CLASSES if check.suffixes & suffixes
        )

    def _configured(self, check: CheckClass) -> bool:
        return check.name in self.__configured

    def _ran(self, check: CheckClass) -> bool:
        return any(
            command in invocation
            for invocation in self.__commands
            for command in check.commands
        )


class CommentMetric:
    """Metric 6, narration added to generated code, scored inversely.

    Args:
        evidence (Evidence): The bundle for the branch under assessment.

    """

    NAME: str = "generative_comments"

    def __init__(self, evidence: Evidence) -> None:
        self.__files: list[FileInfo] = [
            file
            for file in evidence.diff.files
            if file.touched and Languages.get_marker(file.suffix)
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
