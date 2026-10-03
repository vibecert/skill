from vibecert.certificate import Certificate
from vibecert.vibecert_types import ScoredMetric


class CertificateMarkdown:
    """The certificate as markdown.

    Args:
        certificate (Certificate): The scored result for the branch.

    """

    def __init__(self, certificate: Certificate) -> None:
        self.__certificate: Certificate = certificate

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
                *(self._row(metric) for metric in self.__certificate.get_metrics()),
                "",
                self._weights(),
            ]
        )

    def _headline(self) -> str:
        return (
            f"**{self.__certificate.get_score()}/3**"
            if self.__certificate.get_score() is not None
            else "Not certified: too little of this branch was generated to score."
        )

    def _branch(self) -> str:
        evidence = self.__certificate.get_evidence()
        return (
            f"`{evidence.branch.name}`, {len(evidence.branch.commits)} commits, "
            f"{evidence.diff.changed} changed lines, "
            f"{evidence.attribution.touched_proportion:.0%} generated"
        )

    @staticmethod
    def _row(metric: ScoredMetric) -> str:
        return (
            f"| {metric.number}. {metric.title} "
            f"| {'n/a' if metric.raw is None else f'{metric.raw}/3'} "
            f"| {'n/a' if metric.adjusted is None else f'{metric.adjusted}/3'} "
            f"| {metric.evidence} |"
        )

    def _weights(self) -> str:
        weights = self.__certificate.get_weights()
        return (
            f"Weight {weights.get_weight()}: length {weights.get_length()}, "
            f"criticality {weights.get_criticality()}, risk {weights.get_risk()}."
        )
