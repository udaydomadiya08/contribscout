"""Deterministic, explainable 0-10 scoring engine for open-source opportunities."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from contribscout.analysis.difficulty import estimate_difficulty, generate_investigation_plan
from contribscout.analysis.repository_health import calculate_repository_health
from contribscout.models import Opportunity, OpportunityScore, UserProfile

DEFAULT_WEIGHTS = {
    "practical_usefulness": 0.25,
    "feasibility": 0.20,
    "technical_depth": 0.20,
    "maintainer_responsiveness": 0.15,
    "learning_and_portfolio": 0.10,
    "repository_health": 0.10,
}


def score_practical_usefulness(opportunity: Opportunity) -> Tuple[float, str]:
    """Score practical usefulness and potential impact (0.0 to 10.0)."""
    score = 6.0
    labels_lower = [lbl.lower() for lbl in opportunity.labels]
    title_lower = opportunity.title.lower()

    if opportunity.inferred_type == "bug":
        score += 2.0
        reason = "Addresses a concrete functional bug impacting users."
    elif opportunity.inferred_type == "performance":
        score += 2.5
        reason = "Performance optimization directly improves efficiency and latency."
    elif opportunity.inferred_type == "testing":
        score += 1.5
        reason = "Improves test coverage and prevents regressions."
    elif opportunity.inferred_type == "dx":
        score += 1.5
        reason = "Enhances developer experience and contributor workflow."
    elif opportunity.inferred_type == "documentation":
        if "typo" in title_lower:
            score = 2.0
            reason = "Minor typo fix; low functional impact."
        else:
            score = 4.5
            reason = "Documentation improvement clarifies usage for community."
    else:
        reason = "General feature or improvement proposal."

    # Community signals
    if opportunity.comments_count >= 5:
        score += 1.0
        reason += f" High community interest ({opportunity.comments_count} comments)."

    clamped = max(0.0, min(10.0, round(score, 1)))
    return clamped, reason


def score_feasibility(
    opportunity: Opportunity,
    profile: UserProfile,
    difficulty_category: str,
) -> Tuple[float, str]:
    """Score feasibility for user's skills and available time (0.0 to 10.0)."""
    score = 5.0
    reasons = []

    repo_lang = (
        opportunity.repository.primary_language.lower()
        if opportunity.repository and opportunity.repository.primary_language
        else ""
    )

    # Language match
    if repo_lang in profile.languages:
        prof = profile.languages[repo_lang].lower()
        if prof in ("advanced", "expert"):
            score += 3.0
            reasons.append(f"Strong language proficiency match ({repo_lang}: {prof}).")
        elif prof == "intermediate":
            score += 2.0
            reasons.append(f"Good language match ({repo_lang}: intermediate).")
        else:
            score += 1.0
            reasons.append(f"Basic language familiarity ({repo_lang}: beginner).")
    elif not repo_lang:
        score += 0.5
        reasons.append("Primary language unknown.")
    else:
        score -= 2.0
        reasons.append(f"Language '{repo_lang}' is not listed in user profile.")

    # Framework match
    text = (opportunity.title + " " + opportunity.body).lower()
    matched_fws = [fw for fw in profile.frameworks if fw.lower() in text]
    if matched_fws:
        score += 1.5
        reasons.append(f"Matches familiar technologies ({', '.join(matched_fws[:3])}).")

    # Time / effort compatibility
    if profile.hours_per_week < 3.0 and difficulty_category in ("Advanced", "Expert"):
        score -= 2.0
        reasons.append(f"Requires high effort, but user has limited weekly budget ({profile.hours_per_week}h).")
    elif difficulty_category == "Beginner" and profile.experience_level == "beginner":
        score += 1.0
        reasons.append("Beginner-friendly scope aligns well with profile.")

    clamped = max(0.0, min(10.0, round(score, 1)))
    return clamped, " ".join(reasons)


def score_technical_depth(
    opportunity: Opportunity,
    difficulty_category: str,
) -> Tuple[float, str]:
    """Score technical depth and engineering value (0.0 to 10.0)."""
    title_lower = opportunity.title.lower()
    labels_lower = [lbl.lower() for lbl in opportunity.labels]

    # Explicit handling of trivial tasks vs solid engineering
    if "typo" in title_lower or (opportunity.inferred_type == "documentation" and len(opportunity.body) < 100):
        return 1.5, "Trivial textual or typo edit; minimal engineering depth."

    if opportunity.inferred_type == "performance":
        return 8.5, "High engineering depth involving profiling, latency, or memory optimization."

    if opportunity.inferred_type == "testing":
        return 7.0, "Substantial engineering value in mocking, test fixtures, and test coverage."

    if difficulty_category == "Expert":
        return 9.0, "High architectural complexity and subsystem depth."
    elif difficulty_category == "Advanced":
        return 8.0, "Multi-component logic and non-trivial state or error handling."
    elif difficulty_category == "Intermediate":
        return 6.5, "Standard engineering problem requiring debugging and regression testing."
    else:
        return 4.0, "Accessible scope with modest technical complexity."


def score_maintainer_responsiveness(
    opportunity: Opportunity,
    repo_health: float = 5.0,
) -> Tuple[float, str]:
    """Score maintainer responsiveness and acceptance prospects (0.0 to 10.0)."""
    score = 6.0
    reasons = []

    repo = opportunity.repository
    if repo:
        if repo.stars >= 500:
            score += 1.0
            reasons.append("Active maintainer base with substantial project adoption.")
        if repo.open_issues_count > 1000:
            score -= 1.0
            reasons.append("High issue backlog; maintainer review response may be delayed.")
        if repo_health >= 8.0:
            score += 1.0
            reasons.append("Repository exhibits recent commits and continuous maintenance.")

    if opportunity.comments_count > 0:
        score += 0.5
        reasons.append("Issue has existing discussion context.")
    else:
        score -= 0.5
        reasons.append("No comments recorded yet on this issue.")

    clamped = max(0.0, min(10.0, round(score, 1)))
    return clamped, " ".join(reasons) if reasons else "Standard maintainer review responsiveness expected."


def score_learning_and_portfolio(
    opportunity: Opportunity,
    profile: UserProfile,
) -> Tuple[float, str]:
    """Score learning and portfolio value (0.0 to 10.0)."""
    score = 5.0
    reasons = []

    text = (opportunity.title + " " + opportunity.body).lower()

    # Learning goals
    matched_goals = [g for g in profile.learning_goals if any(word in text for word in g.lower().split())]
    if matched_goals:
        score += 2.5
        reasons.append(f"Advances learning goals: {', '.join(matched_goals[:2])}.")

    # Portfolio value: established repository
    repo = opportunity.repository
    if repo:
        if repo.stars >= 1000:
            score += 2.5
            reasons.append(f"High portfolio visibility in prominent project ({repo.stars:,} stars).")
        elif repo.stars >= 100:
            score += 1.5
            reasons.append(f"Solid portfolio credibility in established repo ({repo.stars} stars).")

    # Inferred type value
    if opportunity.inferred_type in ("bug", "performance", "feature"):
        score += 0.5
        reasons.append("Demonstrates concrete problem-solving in code.")

    clamped = max(0.0, min(10.0, round(score, 1)))
    return clamped, " ".join(reasons) if reasons else "Moderate general learning and portfolio value."


def evaluate_confidence(
    opportunity: Opportunity,
) -> Tuple[float, str, List[str], List[str]]:
    """
    Calculate confidence score (0.0 - 1.0) and identify missing information.
    Returns: (confidence_score, confidence_label, evidence, missing_info)
    """
    confidence = 0.85
    evidence: List[str] = []
    missing_info: List[str] = []

    if len(opportunity.body.strip()) >= 200:
        confidence += 0.1
        evidence.append("Comprehensive issue description provided.")
    elif len(opportunity.body.strip()) < 50:
        confidence -= 0.3
        missing_info.append("Issue body is sparse (< 50 characters).")

    if opportunity.repository:
        evidence.append(f"Repository metadata verified ({opportunity.repository.stars} stars, {opportunity.repository.license or 'no license'}).")
        if not opportunity.repository.license:
            confidence -= 0.1
            missing_info.append("Repository license is unverified.")
    else:
        confidence -= 0.25
        missing_info.append("Repository metadata could not be retrieved.")

    clamped_conf = max(0.2, min(1.0, round(confidence, 2)))
    if clamped_conf >= 0.75:
        label = "High"
    elif clamped_conf >= 0.50:
        label = "Medium"
    else:
        label = "Low"

    return clamped_conf, label, evidence, missing_info


def calculate_opportunity_score(
    opportunity: Opportunity,
    profile: UserProfile,
    weights: Optional[Dict[str, float]] = None,
) -> OpportunityScore:
    """
    Compute deterministic weighted score (0.0 - 10.0) with detailed explainability.
    """
    active_weights = dict(weights or DEFAULT_WEIGHTS)
    total_w = sum(active_weights.values())
    if total_w <= 0:
        active_weights = dict(DEFAULT_WEIGHTS)
        total_w = sum(active_weights.values())
    if abs(total_w - 1.0) > 1e-4:
        active_weights = {k: v / total_w for k, v in active_weights.items()}

    # 1. Difficulty & Plan
    diff_cat, effort_hours, diff_factors = estimate_difficulty(opportunity, profile)
    plan = generate_investigation_plan(opportunity, profile, diff_cat)

    # 2. Individual criteria scores
    repo_health, health_evidence, health_negatives = calculate_repository_health(opportunity.repository)
    usefulness, use_reason = score_practical_usefulness(opportunity)
    feasibility, feas_reason = score_feasibility(opportunity, profile, diff_cat)
    technical_depth, tech_reason = score_technical_depth(opportunity, diff_cat)
    maintainer, maint_reason = score_maintainer_responsiveness(opportunity, repo_health=repo_health)
    learning, learn_reason = score_learning_and_portfolio(opportunity, profile)

    # 3. Weighted raw calculation
    raw_score = (
        usefulness * active_weights.get("practical_usefulness", 0.25)
        + feasibility * active_weights.get("feasibility", 0.20)
        + technical_depth * active_weights.get("technical_depth", 0.20)
        + maintainer * active_weights.get("maintainer_responsiveness", 0.15)
        + learning * active_weights.get("learning_and_portfolio", 0.10)
        + repo_health * active_weights.get("repository_health", 0.10)
    )

    # 4. Confidence and evidence
    conf_score, conf_label, evidence_items, missing_items = evaluate_confidence(opportunity)

    # Apply confidence adjustment: if confidence is low, scale raw score down
    # (prevents poorly documented/unverified issues from scoring top rank)
    confidence_factor = 0.7 + 0.3 * conf_score
    adjusted_score = round(raw_score * confidence_factor, 1)
    final_score = max(0.0, min(10.0, adjusted_score))

    justifications = {
        "practical_usefulness": use_reason,
        "feasibility": feas_reason,
        "technical_depth": tech_reason,
        "maintainer_responsiveness": maint_reason,
        "learning_and_portfolio": learn_reason,
        "repository_health": f"Health score {repo_health}/10 based on commit recency and adoption.",
    }

    evidence_items.extend(health_evidence)
    negative_signals = list(health_negatives)
    if conf_label == "Low":
        negative_signals.append("Low overall evidence confidence; manual verification recommended.")

    why_matched = (
        f"Matches your proficiency in {opportunity.repository.primary_language if opportunity.repository else 'source'} "
        f"and your interest in {opportunity.inferred_type}s. "
        f"Difficulty estimated as {diff_cat} ({effort_hours})."
    )

    return OpportunityScore(
        opportunity_id=opportunity.id,
        final_score=final_score,
        practical_usefulness=usefulness,
        feasibility=feasibility,
        technical_depth=technical_depth,
        maintainer_responsiveness=maintainer,
        learning_and_portfolio=learning,
        repository_health=repo_health,
        score_breakdown={
            "practical_usefulness": usefulness,
            "feasibility": feasibility,
            "technical_depth": technical_depth,
            "maintainer_responsiveness": maintainer,
            "learning_and_portfolio": learning,
            "repository_health": repo_health,
        },
        justifications=justifications,
        confidence=conf_label,
        confidence_score=conf_score,
        evidence=evidence_items,
        negative_signals=negative_signals,
        missing_information=missing_items,
        estimated_difficulty=diff_cat,
        estimated_effort_hours=effort_hours,
        why_matched=why_matched,
        plan=plan,
    )
