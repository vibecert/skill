from statistics import median

from vibecert.bundle_types import Evidence, PromptInfo


class EvidenceProjection:
    """The slice of a bundle one metric is scored from.

    Args:
        evidence (Evidence): The bundle for the branch under assessment.

    """

    METRICS: tuple[str, ...] = (
        "follow_up_questions",
        "coding_guidelines",
        "prompt_granularity",
    )

    def __init__(self, evidence: Evidence) -> None:
        self.__evidence: Evidence = evidence

    def project(self, metric: str) -> str:
        """Return the evidence for one metric, and nothing else.

        Args:
            metric (str): One of the names in METRICS.

        Returns:
            str: The evidence, ready to hand to whoever scores that metric.

        Raises:
            ValueError: If the metric is not one this projects.

        """
        if metric not in self.METRICS:
            raise ValueError(f"{metric} is not one of {', '.join(self.METRICS)}")
        return {
            "follow_up_questions": self._follow_up_questions,
            "coding_guidelines": self._coding_guidelines,
            "prompt_granularity": self._prompt_granularity,
        }[metric]()

    def _follow_up_questions(self) -> str:
        return "\n".join(
            f"{number}. {prompt.text}"
            for number, prompt in enumerate(self.__evidence.prompts, 1)
        )

    def _coding_guidelines(self) -> str:
        return "\n".join(
            [
                "## Guidelines",
                *(
                    f"- {guideline.path} "
                    f"({'applies' if guideline.applies else 'does not apply'}, "
                    f"{'in context' if guideline.in_context else 'never read'})"
                    for guideline in self.__evidence.activity.guidelines
                ),
                "",
                "## Changed files",
                *(f"- {file.path}" for file in self.__evidence.diff.files),
                "",
                "## Commit subjects",
                *(f"- {commit.subject}" for commit in self.__evidence.branch.commits),
            ]
        )

    def _prompt_granularity(self) -> str:
        return "\n".join(
            [
                f"Median generated lines per producing prompt: {self._median()}",
                f"Prompts producing output: {len(self._producing())} "
                f"of {len(self.__evidence.prompts)}",
                "",
                *(
                    f"{prompt.generated_lines} lines: {prompt.text}"
                    for prompt in self._producing()
                ),
            ]
        )

    def _producing(self) -> list[PromptInfo]:
        return [prompt for prompt in self.__evidence.prompts if prompt.generated_lines]

    def _median(self) -> int:
        return (
            int(median([prompt.generated_lines for prompt in self._producing()]))
            if self._producing()
            else 0
        )
