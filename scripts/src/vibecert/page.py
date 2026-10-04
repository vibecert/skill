import html
import importlib.resources

from vibecert.certificate_types import CertificateDocument, MetricResult


class Stylesheet:
    """The stylesheet both pages share."""

    PATH: str = "assets/certificate.css"

    @classmethod
    def read(cls) -> str:
        """Return the stylesheet, for inlining into a page.

        Returns:
            str: The CSS, so a published page needs no external request.

        """
        return importlib.resources.files("vibecert").joinpath(cls.PATH).read_text()


class CertificatePage:
    """The certificate as a self-contained HTML page.

    Args:
        document (CertificateDocument): The scored result for the branch.

    """

    ABOUT: str = "https://l.martinchapman.co.uk/vibecert"
    STATES: dict[str, str] = {"not_applicable": "n/a", "not_scored": "missing"}

    def __init__(self, document: CertificateDocument) -> None:
        self.__document: CertificateDocument = document

    def render(self) -> str:
        """Return the page, ready to write.

        Returns:
            str: A complete HTML document with no external dependencies.

        """
        return "\n".join(
            [
                "<!doctype html>",
                '<html lang="en">',
                "<head>",
                '<meta charset="utf-8">',
                '<meta name="viewport" content="width=device-width, initial-scale=1">',
                f"<title>VibeCert {self._subject_text()}</title>",
                f"<style>{Stylesheet.read()}</style>",
                "</head>",
                "<body>",
                "<main>",
                "<h1>VibeCert</h1>",
                self._score(),
                self._subject(),
                self._table(),
                self._weights(),
                *self._findings(),
                self._footer(),
                "</main>",
                "</body>",
                "</html>",
            ]
        )

    def _score(self) -> str:
        if self.__document.score is None:
            return (
                '<p class="score">Not certified</p>'
                '<p class="caveat">Too little of this branch was '
                "generated to score.</p>"
            )
        return f'<p class="score">{self.__document.score}<small>/3</small></p>' + (
            ""
            if self.__document.scored == self.__document.applicable
            else f'<p class="caveat">Scored over only {self.__document.scored} '
            f"of {self.__document.applicable} metrics that apply.</p>"
        )

    def _subject_text(self) -> str:
        return (
            "private repository"
            if self.__document.private
            else f"{self.__document.repository} {self.__document.branch}"
        )

    def _subject(self) -> str:
        subject: str = (
            "A private repository"
            if self.__document.private
            else f"<code>{html.escape(str(self.__document.repository))}</code>, "
            f"<code>{html.escape(str(self.__document.branch))}</code>"
        )
        return (
            f'<p class="subject">{subject} &middot; '
            f"{self.__document.commits} commits &middot; "
            f"{self.__document.changed_lines} changed lines &middot; "
            f"{self.__document.generative_proportion:.0%} generated</p>"
        )

    def _table(self) -> str:
        return "\n".join(
            [
                "<table>",
                "<thead><tr><th>Metric</th><th>Score</th><th>Adjusted</th>"
                '<th class="evidence">Evidence</th></tr></thead>',
                "<tbody>",
                *(self._row(metric) for metric in self.__document.metrics),
                "</tbody>",
                "</table>",
            ]
        )

    def _row(self, metric: MetricResult) -> str:
        return (
            f"<tr><td>{metric.number}. {html.escape(metric.title)}</td>"
            f'<td class="band">{self._band(metric.state, metric.raw)}</td>'
            f'<td class="band">{self._band(metric.state, metric.adjusted)}</td>'
            f'<td class="evidence">{html.escape(metric.evidence)}</td></tr>'
        )

    def _band(self, state: str, score: int | None) -> str:
        return self.STATES.get(state, f"{score}/3")

    def _weights(self) -> str:
        weights = self.__document.weights
        return (
            '<div class="panel"><h2>Weight</h2>'
            f"<p>Carried weight {weights.applied}, being the highest of "
            f"length {weights.length}, criticality {weights.criticality} "
            f"and risk {weights.risk}.</p></div>"
        )

    def _findings(self) -> list[str]:
        return (
            [
                '<div class="panel"><h2>Security findings</h2><ul>'
                + "".join(
                    f"<li>{html.escape(finding)}</li>"
                    for finding in self.__document.findings
                )
                + "</ul></div>"
            ]
            if self.__document.findings
            else []
        )

    def _footer(self) -> str:
        return (
            "<footer>"
            f"<p><code>{html.escape(self.__document.identifier)}</code> &middot; "
            f"issued {html.escape(self.__document.issued_at[:10])} &middot; "
            f"scored under {html.escape(self.__document.rubrics_version)}</p>"
            "<p>A VibeCert score is self-assessed. It records how generative tooling "
            "was used on one branch, not that the code is correct. "
            f'<a href="{self.ABOUT}">What this measures</a>.</p>'
            "</footer>"
        )


class SiteIndex:
    """The page served at the root of the certificate site.

    It explains what a certificate is and does not list them. A certificate is
    found by its link, so one belonging to a private repository stays
    unlisted even though the site is public.
    """

    @classmethod
    def render(cls) -> str:
        """Return the root page, ready to write.

        Returns:
            str: A complete HTML document with no external dependencies.

        """
        return "\n".join(
            [
                "<!doctype html>",
                '<html lang="en">',
                "<head>",
                '<meta charset="utf-8">',
                '<meta name="viewport" content="width=device-width, initial-scale=1">',
                "<title>VibeCert</title>",
                f"<style>{Stylesheet.read()}</style>",
                "</head>",
                "<body>",
                "<main>",
                "<h1>VibeCert</h1>",
                "<p>A VibeCert certificate records how generative tooling was used "
                "to produce one branch of one repository, scored against a published "
                "rubric.</p>",
                "<p>It says nothing about whether the code is correct. It is "
                "self-assessed, and nothing stops an author fabricating the evidence "
                "it reads.</p>",
                "<p>Certificates are not listed here. Each one is reached by its own "
                "address, which its author chooses whether to share.</p>",
                "<footer>",
                f'<p><a href="{CertificatePage.ABOUT}">What this measures, and why</a>'
                "</p>",
                "</footer>",
                "</main>",
                "</body>",
                "</html>",
            ]
        )
