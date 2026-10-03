class Thresholds:
    """Band boundaries, fixed from published measurement."""

    AMENDMENT_LOW: float = 0.05
    AMENDMENT_HIGH: float = 0.15
    COMMENT_LOW: float = 0.10
    COMMENT_HIGH: float = 0.20
    GATE: float = 0.25
    LENGTH_LOW: int = 200
    LENGTH_HIGH: int = 800
    PROMPT_LOW: int = 50
    PROMPT_HIGH: int = 200
    FAN_IN_LOW: int = 1
    FAN_IN_HIGH: int = 5

    LOOKUP: dict[tuple[int, int], int] = {
        (1, 1): 2,
        (1, 2): 1,
        (1, 3): 1,
        (2, 1): 3,
        (2, 2): 2,
        (2, 3): 1,
        (3, 1): 3,
        (3, 2): 3,
        (3, 3): 3,
    }
