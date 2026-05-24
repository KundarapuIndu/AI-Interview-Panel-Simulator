from pydantic import BaseModel, Field
from typing import List, Optional
import json, re

class AgentScore(BaseModel):
    score: int = Field(ge=0, le=10)
    dimension: str
    reasoning: str
    follow_up: str

class ResumeAnalysis(BaseModel):
    skills: List[str]
    projects: List[str]
    experience: List[str]
    strengths: List[str]
    weak_areas: List[str]
    suspicious_claims: List[str]
    suggested_deep_dives: List[str]

class PanelStrategy(BaseModel):
    alex_focus: str
    sara_focus: str
    raj_targets: List[str]
    opening_theme: str

class JudgeVerdict(BaseModel):
    hire_decision: str
    technical_depth: float
    communication: float
    confidence: float
    problem_solving: float
    practical_knowledge: float
    ownership: float
    composite_score: float
    strengths: List[str]
    weaknesses: List[str]
    improvement_roadmap: List[str]
    summary: str
    rejection_reasons: List[str] = []


def _coerce_numeric_fields(data: dict, model) -> dict:
    """
    For any field annotated as float on JudgeVerdict / int on AgentScore,
    coerce the raw JSON value so Pydantic never chokes on 8.5 vs 8.
    """
    hints = model.__annotations__
    out = dict(data)
    for field, typ in hints.items():
        if field in out and out[field] is not None:
            if typ is float:
                try:
                    out[field] = float(out[field])
                except (TypeError, ValueError):
                    pass
            elif typ is int:
                try:
                    out[field] = int(round(float(out[field])))
                except (TypeError, ValueError):
                    pass
    return out


def parse_json_safely(raw, model):
    if hasattr(raw, 'content'):
        raw = raw.content
    if not raw or not raw.strip():
        raise ValueError(f"Empty response for {model.__name__}")
    clean = re.sub(r"```json|```", "", raw).strip()
    match = re.search(r'\{.*\}', clean, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON found in: {clean[:200]}")
    try:
        data = json.loads(match.group())
        data = _coerce_numeric_fields(data, model)
        return model(**data)
    except Exception as e:
        raise ValueError(f"Parse failed: {e}\nRaw: {clean[:300]}")