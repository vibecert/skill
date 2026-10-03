from vibecert.certificate_types import CertificateDocument, MetricResult


class CertificateMarkdown:
    """The certificate as markdown.

    Args:
        document (CertificateDocument): The scored result for the branch.

    """

    STATES: dict[str, str] = {
        "not_applicable": "n/a",
        "not_scored": "missing",
    }

    def __init__(self, document: CertificateDocument) -> None:
        self.__document: CertificateDocument = document

    def render(self) -> str:
        """Return the certificate, ready to print.

        Returns:
            str: Markdown, with a table of metrics and the overall score.

        """
        return "\n".join(
            [
                "## VibeCert",
                "",
                self._headline(),
                "",
                self._branch(),
                "",
                "| Metric | Score | Adjusted | Evidence |",
                "| --- | --- | --- | --- |",
                *(self._row(metric) for metric in self.__document.metrics),
                "",
                self._weights(),
                *self._findings(),
                "",
                f"`{self.__document.identifier}`, "
                f"scored under {self.__document.rubrics_version}",
            ]
        )

    def _headline(self) -> str:
        if self.__document.score is None:
            return "Not certified: too little of this branch was generated to score."
        return f"**{self.__document.score}/3**" + (
            ""
            if self.__document.scored == self.__document.applicable
            else f", over only {self.__document.scored} of "
            f"{self.__document.applicable} metrics that apply"
        )

    def _branch(self) -> str:
        return (
            f"{self._name()}, {self.__document.commits} commits, "
            f"{self.__document.changed_lines} changed lines, "
            f"{self.__document.generative_proportion:.0%} generated"
        )

    def _name(self) -> str:
        return (
            "A private repository"
            if self.__document.private
            else f"`{self.__document.repository}`, `{self.__document.branch}`"
        )

    def _row(self, metric: MetricResult) -> str:
        return (
            f"| {metric.number}. {metric.title} "
            f"| {self._band(metric.state, metric.raw)} "
            f"| {self._band(metric.state, metric.adjusted)} "
            f"| {metric.evidence} |"
        )

    def _band(self, state: str, score: int | None) -> str:
        return self.STATES.get(state, f"{score}/3")

    def _weights(self) -> str:
        weights = self.__document.weights
        return (
            f"Weight {weights.applied}: length {weights.length}, "
            f"criticality {weights.criticality}, risk {weights.risk}."
        )

    def _findings(self) -> list[str]:
        return (
            ["", "Security findings: " + "; ".join(self.__document.findings)]
            if self.__document.findings
            else []
        )
