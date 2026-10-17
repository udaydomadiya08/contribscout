"""Data models for ContribScout."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class UserProfile:
    """User preferences, skills, and constraints for contribution discovery."""

    languages: Dict[str, str] = field(default_factory=lambda: {"python": "intermediate"})
    frameworks: List[str] = field(default_factory=list)
    interests: List[str] = field(default_factory=list)
    contribution_types: List[str] = field(
        default_factory=lambda: ["bug", "feature", "documentation", "good-first-issue"]
    )
    experience_level: str = "intermediate"  # beginner, intermediate, advanced, expert
    hours_per_week: float = 5.0
    preferred_duration: str = "medium"  # quick (<3h), medium (3-10h), deep (10h+), any
    desired_difficulty: str = "intermediate"  # beginner, intermediate, advanced, any
    learning_goals: List[str] = field(default_factory=list)
    portfolio_goals: List[str] = field(default_factory=list)
    min_stars: int = 50
    max_stars: Optional[int] = None
    maturity: str = "any"  # emerging, growing, mature, any
    priority_repos: List[str] = field(default_factory=list)
    priority_orgs: List[str] = field(default_factory=list)
    exclude_repos: List[str] = field(default_factory=list)
    exclude_orgs: List[str] = field(default_factory=list)
    exclude_topics: List[str] = field(default_factory=list)
    exclude_labels: List[str] = field(
        default_factory=lambda: ["wontfix", "invalid", "duplicate", "question"]
    )
    min_recent_activity_days: int = 90
    max_candidates: int = 30
    api_budget_requests: int = 60
    rate_limit_pause_seconds: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to serializable dict without any secret fields."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> UserProfile:
        """Create a UserProfile from a raw dictionary, casting and validating defaults."""
        data = data or {}
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}

        # Normalize languages mapping
        raw_langs = filtered.get("languages", {})
        if isinstance(raw_langs, list):
            # If user specified as list of strings, default to intermediate
            filtered["languages"] = {str(lang).lower(): "intermediate" for lang in raw_langs}
        elif isinstance(raw_langs, dict):
            filtered["languages"] = {str(k).lower(): str(v).lower() for k, v in raw_langs.items()}

        # Normalize list fields
        for list_field in [
            "frameworks",
            "interests",
            "contribution_types",
            "learning_goals",
            "portfolio_goals",
            "priority_repos",
            "priority_orgs",
            "exclude_repos",
            "exclude_orgs",
            "exclude_topics",
            "exclude_labels",
        ]:
            val = filtered.get(list_field, [])
            if isinstance(val, list):
                filtered[list_field] = [str(item).strip() for item in val if str(item).strip()]
            elif isinstance(val, str):
                filtered[list_field] = [val.strip()]
            else:
                filtered[list_field] = []

        return cls(**filtered)


@dataclass
class Repository:
    """GitHub repository metadata and health indicators."""

    owner: str
    name: str
    full_name: str
    description: str = ""
    url: str = ""
    primary_language: str = ""
    topics: List[str] = field(default_factory=list)
    stars: int = 0
    forks: int = 0
    open_issues_count: int = 0
    license: Optional[str] = None
    is_archived: bool = False
    is_fork: bool = False
    created_at: str = ""
    pushed_at: str = ""
    updated_at: str = ""
    has_contributing_guide: bool = False
    health_score: float = 5.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Repository:
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class Opportunity:
    """A GitHub issue or actionable engineering opportunity."""

    id: str  # Format: "owner/repo#number"
    repo_full_name: str
    number: int
    title: str
    body: str = ""
    url: str = ""
    state: str = "open"  # open, closed
    labels: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    comments_count: int = 0
    assignees: List[str] = field(default_factory=list)
    has_pull_request: bool = False
    is_locked: bool = False
    repository: Optional[Repository] = None
    inferred_type: str = "bug"  # bug, feature, documentation, performance, testing, dx, refactoring, other

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        if self.repository:
            res["repository"] = self.repository.to_dict()
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Opportunity:
        data = dict(data)
        repo_data = data.pop("repository", None)
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        opp = cls(**filtered)
        if repo_data and isinstance(repo_data, dict):
            opp.repository = Repository.from_dict(repo_data)
        return opp


@dataclass
class EligibilityResult:
    """Eligibility check verdict and diagnostic reasons."""

    is_eligible: bool
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    penalties: Dict[str, float] = field(default_factory=dict)


@dataclass
class InvestigationPlan:
    """Structured 10-point initial contribution plan for an opportunity."""

    problem_summary: str
    importance: str
    what_to_read_first: List[str]
    likely_files_or_subsystems: List[str]
    reproduction_steps: List[str]
    implementation_hypothesis: str
    test_and_regression_checks: List[str]
    questions_for_maintainers: List[str]
    risks_and_blockers: List[str]
    suggested_first_action: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InvestigationPlan:
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class OpportunityScore:
    """Explainable multi-criteria score breakdown for an opportunity."""

    opportunity_id: str
    final_score: float  # Normalized 0.0 - 10.0
    practical_usefulness: float  # 0.0 - 10.0
    feasibility: float  # 0.0 - 10.0
    technical_depth: float  # 0.0 - 10.0
    maintainer_responsiveness: float  # 0.0 - 10.0
    learning_and_portfolio: float  # 0.0 - 10.0
    repository_health: float  # 0.0 - 10.0
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    justifications: Dict[str, str] = field(default_factory=dict)
    confidence: str = "Medium"  # High, Medium, Low
    confidence_score: float = 0.7  # 0.0 - 1.0
    evidence: List[str] = field(default_factory=list)
    negative_signals: List[str] = field(default_factory=list)
    missing_information: List[str] = field(default_factory=list)
    estimated_difficulty: str = "Intermediate"  # Beginner, Intermediate, Advanced, Expert
    estimated_effort_hours: str = "4-8 hours"
    why_matched: str = ""
    plan: Optional[InvestigationPlan] = None

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        if self.plan:
            res["plan"] = self.plan.to_dict()
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> OpportunityScore:
        data = dict(data)
        plan_data = data.pop("plan", None)
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        score = cls(**filtered)
        if plan_data and isinstance(plan_data, dict):
            score.plan = InvestigationPlan.from_dict(plan_data)
        return score


@dataclass
class ScoredOpportunity:
    """Combined model linking an opportunity to its score, ranking, and history status."""

    opportunity: Opportunity
    score: OpportunityScore
    rank: int = 1
    status_badge: str = "NEW"  # NEW, UPDATED, SEEN

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "status_badge": self.status_badge,
            "opportunity": self.opportunity.to_dict(),
            "score": self.score.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ScoredOpportunity:
        opp = Opportunity.from_dict(data["opportunity"])
        sc = OpportunityScore.from_dict(data["score"])
        return cls(
            opportunity=opp,
            score=sc,
            rank=data.get("rank", 1),
            status_badge=data.get("status_badge", "NEW"),
        )


@dataclass
class ScanReport:
    """Full scan output report containing results and metadata."""

    timestamp_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    )
    profile_summary: Dict[str, Any] = field(default_factory=dict)
    search_scope: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, int] = field(
        default_factory=lambda: {
            "candidates_found": 0,
            "candidates_excluded": 0,
            "candidates_deduplicated": 0,
            "candidates_scored": 0,
        }
    )
    opportunities: List[ScoredOpportunity] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    discovery_backend: str = "github_api"
    rate_limit_info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp_utc": self.timestamp_utc,
            "profile_summary": self.profile_summary,
            "search_scope": self.search_scope,
            "stats": self.stats,
            "opportunities": [opp.to_dict() for opp in self.opportunities],
            "warnings": self.warnings,
            "discovery_backend": self.discovery_backend,
            "rate_limit_info": self.rate_limit_info,
        }


@dataclass
class HistoryEntry:
    """Historical tracking entry for an opportunity seen in a past scan."""

    opportunity_id: str
    title: str
    url: str
    repo_full_name: str
    first_seen_at: str
    last_seen_at: str
    last_score: float
    state: str = "open"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HistoryEntry:
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)
