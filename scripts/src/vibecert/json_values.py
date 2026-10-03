class Json:
    """Narrowing of decoded JSON, whose members are only known at runtime."""

    @staticmethod
    def as_dict(value: object) -> dict[str, object]:
        """Return a value as a mapping.

        Args:
            value (object): A decoded JSON value.

        Returns:
            dict[str, object]: The mapping, or an empty one when it is not a mapping.

        """
        return (
            {str(key): item for key, item in value.items()}
            if isinstance(value, dict)
            else {}
        )

    @staticmethod
    def as_list(value: object) -> list[object]:
        """Return a value as a sequence.

        Args:
            value (object): A decoded JSON value.

        Returns:
            list[object]: The sequence, or an empty one when it is not a sequence.

        """
        return list(value) if isinstance(value, list) else []

    @staticmethod
    def as_text(value: object) -> str:
        """Return a value as text.

        Args:
            value (object): A decoded JSON value.

        Returns:
            str: The text, or an empty string when it is not text.

        """
        return value if isinstance(value, str) else ""
