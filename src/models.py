"""
Typed data contracts shared across the pipeline.
Keeping these in one place is what lets the eval engine, storage layer,
and report generator all agree on shape without guessing.
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Category(str, Enum):
    billing = "billing"
    technical = "technical"
    account = "account"
    general = "general"


class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class FewShotExample(BaseModel):
    input: str
    output: str


class PromptConfig(BaseModel):
    """The 'code' under test. Loaded from /prompts/<version>.yaml"""
    version: str
    timestamp: str
    model: str = "gpt-4o-mini"
    provider: str = "openai"  # openai | anthropic | gemini
    system_prompt: str
    few_shot_examples: list[FewShotExample] = Field(default_factory=list)
    notes: Optional[str] = None


class ClassifierOutput(BaseModel):
    """Structured output contract for the email classifier feature."""
    category: Category
    summary: str
    confidence: float = 0.0  # model's self-reported confidence, 0-100


class TestCase(BaseModel):
    id: str
    input: str
    expected_category: Category
    expected_summary: str
    expected_difficulty: Difficulty
    notes: str = ""


class CaseResult(BaseModel):
    """Result of running ONE test case through ONE prompt version."""
    case_id: str
    input: str
    expected_category: Category
    actual_category: Optional[Category]
    expected_summary: str
    actual_summary: Optional[str]
    expected_difficulty: Difficulty = Difficulty.medium
    category_match: bool
    summary_score: float  # 1-5, LLM-as-judge
    judge_rationale: Optional[str] = None
    semantic_similarity: Optional[float] = None  # 0-1, embeddings cosine sim (or token-overlap fallback)
    semantic_similarity_is_real: bool = False  # False if the fallback approximation was used
    confidence: float = 0.0  # model's self-reported confidence, 0-100
    latency_ms: float
    tokens_used: int
    passed: bool  # category_match AND summary_score >= 3
    error: Optional[str] = None


class EvalRun(BaseModel):
    """Metadata + aggregate scores for a single evaluation run."""
    run_id: str
    prompt_version: str
    model: str
    provider: str = "openai"
    baseline_run_id: Optional[str]
    timestamp: str
    total_cases: int
    overall_accuracy: float
    category_accuracy: dict[str, float]
    difficulty_breakdown: dict[str, dict[str, int]] = Field(default_factory=dict)  # {"easy": {"passed": 21, "total": 22}, ...}
    avg_summary_relevance: float
    avg_semantic_similarity: Optional[float] = None
    avg_latency_ms: float
    avg_tokens: float
    avg_cost_usd: float = 0.0
    status: str  # PASS | WARNING | FAIL
    regressions: int = 0
    improvements: int = 0
    no_change: int = 0
    p_value: Optional[float] = None
    statistically_significant: bool = False

    @staticmethod
    def new_id() -> str:
        return datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")
