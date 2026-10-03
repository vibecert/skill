import dataclasses


@dataclasses.dataclass
class Commit:
    sha: str
    timestamp: str
    subject: str


@dataclasses.dataclass
class FileDiff:
    path: str
    added: list[str]
    removed: int


@dataclasses.dataclass
class EditHunk:
    session: str
    timestamp: str
    channel: str
    path: str
    added: list[str]
    removed: int
    command: str


@dataclasses.dataclass
class Prompt:
    session: str
    timestamp: str
    text: str


@dataclasses.dataclass
class SessionSpan:
    identifier: str
    path: str
    start: str
    end: str


@dataclasses.dataclass
class CheckClass:
    name: str
    suffixes: frozenset[str]
    configs: dict[str, str]
    commands: frozenset[str]


@dataclasses.dataclass
class Band:
    metric: str
    score: int | None
    measure: float | None
    evidence: str
