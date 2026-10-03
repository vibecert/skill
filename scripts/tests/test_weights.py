import pytest

from tests.conftest import evidence_of, file_of
from vibecert.weights import Weights


def weighted(
    changed: int = 0,
    fan_in: int = 0,
    risk: list[str] | None = None,
    touched: int = 100,
    distribution: list[int] | None = None,
) -> Weights:
    bundle = evidence_of(
        [file_of("foo.py", ".py", changed, fan_in=fan_in, risk_signals=risk)],
        fan_in_distribution=(
            [0, 0, 1, 2, 3, 4, 5, 9, 20, 40] if distribution is None else distribution
        ),
    )
    bundle.diff.changed = changed
    bundle.attribution.touched_proportion = touched / 100
    return Weights(bundle)


class TestWeights:
    @pytest.mark.parametrize(
        "changed,expected", [(199, 1), (200, 2), (800, 2), (801, 3)]
    )
    def test_get_length_changed_lines_returns_banded_score(
        self, changed: int, expected: int
    ) -> None:
        assert weighted(changed).get_length() == expected

    @pytest.mark.parametrize("fan_in,expected", [(0, 1), (3, 2), (9, 2), (40, 3)])
    def test_get_criticality_fan_in_rank_returns_banded_score(
        self, fan_in: int, expected: int
    ) -> None:
        assert weighted(fan_in=fan_in).get_criticality() == expected

    def test_get_criticality_same_fan_in_in_a_larger_repository_ranks_lower(
        self,
    ) -> None:
        assert weighted(fan_in=5, distribution=[5] + [9] * 19).get_criticality() == 1

    def test_get_criticality_no_distribution_returns_one(self) -> None:
        assert weighted(fan_in=40, distribution=[]).get_criticality() == 1

    @pytest.mark.parametrize(
        "risk,expected",
        [
            ([], 1),
            (["S113: requests call without timeout"], 2),
            (["S602: subprocess call with shell=True"], 3),
            (["S105: possible hardcoded password"], 3),
            (["personal data referenced"], 3),
        ],
    )
    def test_get_risk_findings_returns_banded_score(
        self, risk: list[str], expected: int
    ) -> None:
        assert weighted(risk=risk).get_risk() == expected

    def test_get_weight_several_dimensions_returns_highest(self) -> None:
        assert weighted(100, 40, []).get_weight() == 3

    def test_get_weight_nothing_demanding_returns_one(self) -> None:
        assert weighted(100, 0, []).get_weight() == 1

    @pytest.mark.parametrize("touched,expected", [(24, False), (25, True), (99, True)])
    def test_is_certifiable_generative_proportion_decides(
        self, touched: int, expected: bool
    ) -> None:
        assert weighted(touched=touched).is_certifiable() is expected
