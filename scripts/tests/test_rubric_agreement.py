import pathlib
import re

import pytest

from vibecert.rubric import Thresholds

RUBRICS: pathlib.Path = pathlib.Path(__file__).parents[2] / "references" / "rubrics.md"


class TestRubricAgreement:
    @pytest.mark.parametrize(
        "value",
        [
            Thresholds.AMENDMENT_LOW,
            Thresholds.AMENDMENT_HIGH,
            Thresholds.COMMENT_LOW,
            Thresholds.COMMENT_HIGH,
            Thresholds.GATE,
            Thresholds.LENGTH_LOW,
            Thresholds.LENGTH_HIGH,
            Thresholds.PROMPT_LOW,
            Thresholds.PROMPT_HIGH,
            Thresholds.FAN_IN_LOW,
            Thresholds.FAN_IN_HIGH,
        ],
    )
    def test_thresholds_prose_rubric_states_every_value(
        self, value: float | int
    ) -> None:
        assert float(value) in {
            float(number) for number in re.findall(r"\d+\.\d+|\d+", RUBRICS.read_text())
        }, f"{value} is not stated in references/rubrics.md"
