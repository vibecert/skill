from pydantic import BaseModel


class MetricResult(BaseModel):
    number: int
    name: str
    title: str
    state: str
    raw: int | None
    adjusted: int | None
    evidence: str


class WeightResult(BaseModel):
    length: int
    criticality: int
    risk: int
    applied: int


class CertificateDocument(BaseModel):
    schema_version: str
    rubrics_version: str
    issued_at: str
    identifier: str
    private: bool
    repository: str | None
    branch: str | None
    commits: int
    changed_lines: int
    generative_proportion: float
    certified: bool
    score: float | None
    scored: int
    applicable: int
    weights: WeightResult
    metrics: list[MetricResult]
    findings: list[str]
