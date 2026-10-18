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

    UNCERTIFIED: str = (
        "Not certified: too little of this branch was generated to score."
    )

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
                f"head `{self.__document.head[:7]}`, "
                f"scored under {self.__document.rubrics_version}",
                "",
                *self._share(),
            ]
        )

    def _share(self) -> list[str]:
        snippets: CertificateSnippets = CertificateSnippets(self.__document)
        if not self.__document.site:
            return [
                "This certificate has no address, because the repository names "
                "no GitHub owner. Rescore with `--site-url` to publish it."
            ]
        return [
            "### To share",
            "",
            "As a commit trailer:",
            "",
            "```",
            snippets.get_trailer(),
            "```",
            "",
            "In a pull request:",
            "",
            "```markdown",
            snippets.get_summary(),
            "```",
        ]

    def _headline(self) -> str:
        if self.__document.score is None:
            return CertificateMarkdown.UNCERTIFIED
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


class CertificateSnippets:
    """Lines the author can paste wherever they want the score to appear.

    Args:
        document (CertificateDocument): The scored result for the branch.

    """

    BADGE: str = "https://img.shields.io/endpoint?url="

    def __init__(self, document: CertificateDocument) -> None:
        self.__document: CertificateDocument = document

    def get_trailer(self) -> str:
        """Return a git trailer, short enough for a commit message body.

        Returns:
            str: One line, within the 72 characters a body line allows.

        """
        return f"VibeCert: {self._score()} ({self.get_url()})"

    def get_summary(self) -> str:
        """Return a badge and a sentence, for a pull request description.

        Returns:
            str: Two lines of markdown.

        """
        return (
            f"[![VibeCert]({self.BADGE}{self.get_url()}/badge.json)]"
            f"({self.get_url()})\n\n"
            f"Vibe coding practices on this branch scored {self._score()} "
            f"with VibeCert: {self.get_url()}"
        )

    def get_url(self) -> str:
        """Return the address this certificate is served from.

        Returns:
            str: The certificate's address.

        """
        return f"{self.__document.site}/{self.__document.identifier}"

    def _score(self) -> str:
        return (
            "not certified"
            if self.__document.score is None
            else f"{self.__document.score}/3"
        )


class VerificationComment:
    """A pull request comment on the branch's certificate, or the lack of one.

    Args:
        document (CertificateDocument | None): The branch's certificate, if any.
        problems (list[str]): Every reason the certificate does not pass.
        generated (bool): Whether the branch's commits credit a generative tool.

    """

    ENCOURAGEMENT: str = (
        "This branch credits generative tooling but has no VibeCert certificate.\n"
        "[Score it with VibeCert](https://l.martinchapman.co.uk/vibecert) "
        "to show how that tooling was used."
    )

    def __init__(
        self, document: CertificateDocument | None, problems: list[str], generated: bool
    ) -> None:
        self.__document: CertificateDocument | None = document
        self.__problems: list[str] = problems
        self.__generated: bool = generated

    def render(self) -> str:
        """Return the comment, or nothing when there is nothing to say.

        Returns:
            str: Markdown, or an empty string.

        """
        if self.__document is None:
            return self.ENCOURAGEMENT if self.__generated else ""
        return "\n\n".join(
            [CertificateSnippets(self.__document).get_summary()]
            + (
                ["\n".join(f"- {problem}" for problem in self.__problems)]
                if self.__problems
                else []
            )
        )
