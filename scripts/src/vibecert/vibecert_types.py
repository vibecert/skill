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
