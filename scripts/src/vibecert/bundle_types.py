from pydantic import BaseModel


class RepositoryInfo(BaseModel):
    root: str
    name: str
    remote: str
    comment_density: float


class CommitInfo(BaseModel):
    sha: str
    timestamp: str
    subject: str


class WindowInfo(BaseModel):
    start: str
    end: str


class BranchInfo(BaseModel):
    name: str
    base: str
    merge_base: str
    commits: list[CommitInfo]
    includes_uncommitted: bool
    window: WindowInfo


class FileInfo(BaseModel):
    path: str
    suffix: str
    added: int
    removed: int
    generated: int
    human: int
    touched: bool
    comments: int
    code: int


class DiffInfo(BaseModel):
    files: list[FileInfo]
    added: int
    removed: int
    changed: int


class AttributionInfo(BaseModel):
    added: int
    generated: int
    human: int
    generative_proportion: float
    touched: int
    touched_proportion: float
    revised: int
    revised_proportion: float


class SessionInfo(BaseModel):
    identifier: str
    path: str
    start: str
    end: str


class PromptInfo(BaseModel):
    session: str
    timestamp: str
    text: str


class ActivityInfo(BaseModel):
    human_messages: int
    tool_counts: dict[str, int]
    bash_commands: list[str]
    guidelines_in_context: list[str]
    check_configs: dict[str, list[str]]


class Evidence(BaseModel):
    schema_version: str
    collected_at: str
    repository: RepositoryInfo
    branch: BranchInfo
    diff: DiffInfo
    sessions: list[SessionInfo]
    prompts: list[PromptInfo]
    attribution: AttributionInfo
    activity: ActivityInfo
