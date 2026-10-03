import pytest

from tests.conftest import evidence_of, file_of
from vibecert.bundle_types import CommitInfo, GuidelineInfo, PromptInfo
from vibecert.evidence import EvidenceProjection


def projection() -> EvidenceProjection:
    bundle = evidence_of([file_of("foo.py", ".py", 10)])
    bundle.prompts = [
        PromptInfo(session="s", timestamp="01", text="why line 41?", generated_lines=4),
        PromptInfo(session="s", timestamp="02", text="add a test", generated_lines=40),
    ]
    bundle.activity.guidelines = [
        GuidelineInfo(path="/rules/python.md", applies=True, in_context=False),
        GuidelineInfo(path="/rules/js.md", applies=False, in_context=False),
    ]
    bundle.branch.commits = [
        CommitInfo(sha="abc", timestamp="01", subject="feat: add foo")
    ]
    return EvidenceProjection(bundle)


class TestEvidenceProjection:
    def test_project_follow_up_questions_returns_numbered_prompts(self) -> None:
        assert projection().project("follow_up_questions") == (
            "1. why line 41?\n2. add a test"
        )

    def test_project_coding_guidelines_reports_applicability_and_context(self) -> None:
        assert "/rules/python.md (applies, never read)" in projection().project(
            "coding_guidelines"
        )

    def test_project_coding_guidelines_includes_commit_subjects(self) -> None:
        assert "- feat: add foo" in projection().project("coding_guidelines")

    def test_project_prompt_granularity_reports_median_and_each_prompt(self) -> None:
        assert (
            projection()
            .project("prompt_granularity")
            .startswith("Median generated lines per producing prompt: 22")
        )

    def test_project_no_prompts_reports_zero_median(self) -> None:
        assert "Median generated lines per producing prompt: 0" in EvidenceProjection(
            evidence_of([])
        ).project("prompt_granularity")

    def test_project_prompt_granularity_excludes_prompts_producing_nothing(
        self,
    ) -> None:
        bundle = evidence_of([])
        bundle.prompts = [
            PromptInfo(session="s", timestamp="01", text="a", generated_lines=0),
            PromptInfo(session="s", timestamp="02", text="b", generated_lines=60),
        ]
        assert (
            EvidenceProjection(bundle)
            .project("prompt_granularity")
            .startswith(
                "Median generated lines per producing prompt: 60\nPrompts producing "
                "output: 1 of 2"
            )
        )

    def test_project_unknown_metric_raises(self) -> None:
        with pytest.raises(ValueError):
            projection().project("output_amendments")
