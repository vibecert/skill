import pytest

from vibecert.json_values import Json


class TestJson:
    @pytest.mark.parametrize(
        "value,expected",
        [({"foo": 1}, {"foo": 1}), ("foo", {}), (None, {}), ([1], {})],
    )
    def test_as_dict_any_value_returns_mapping_or_empty(
        self, value: object, expected: dict[str, object]
    ) -> None:
        assert Json.as_dict(value) == expected

    @pytest.mark.parametrize(
        "value,expected", [([1, 2], [1, 2]), ("foo", []), (None, [])]
    )
    def test_as_list_any_value_returns_sequence_or_empty(
        self, value: object, expected: list[object]
    ) -> None:
        assert Json.as_list(value) == expected

    @pytest.mark.parametrize("value,expected", [("foo", "foo"), (1, ""), (None, "")])
    def test_as_text_any_value_returns_text_or_empty(
        self, value: object, expected: str
    ) -> None:
        assert Json.as_text(value) == expected
