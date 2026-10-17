"""Configuration management and profile validation for ContribScout."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yaml

from contribscout.models import UserProfile

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "contribscout"
DEFAULT_PROFILE_PATH = DEFAULT_CONFIG_DIR / "profile.yaml"
WORKSPACE_PROFILE_NAMES = ["profile.yaml", "contribscout.yaml", ".contribscout.yaml"]

# Valid options for constrained profile fields
VALID_EXPERIENCE_LEVELS = {"beginner", "intermediate", "advanced", "expert"}
VALID_DURATIONS = {"quick", "medium", "deep", "any"}
VALID_DIFFICULTIES = {"beginner", "intermediate", "advanced", "expert", "any"}
VALID_MATURITIES = {"emerging", "growing", "mature", "any"}
VALID_CONTRIBUTION_TYPES = {
    "bug",
    "feature",
    "documentation",
    "performance",
    "testing",
    "dx",
    "refactoring",
    "good-first-issue",
}

DEFAULT_WEIGHTS = {
    "practical_usefulness": 0.25,
    "feasibility": 0.20,
    "technical_depth": 0.20,
    "maintainer_responsiveness": 0.15,
    "learning_and_portfolio": 0.10,
    "repository_health": 0.10,
}


class ConfigError(Exception):
    """Raised when configuration file is invalid or cannot be parsed."""

    def __init__(self, message: str, field_name: Optional[str] = None):
        super().__init__(message)
        self.field_name = field_name


def find_profile_path(explicit_path: Optional[str] = None) -> Optional[Path]:
    """Resolve active profile path with precedence: explicit > workspace > user home."""
    if explicit_path:
        p = Path(explicit_path).expanduser().resolve()
        if p.exists():
            return p
        raise FileNotFoundError(f"Specified profile configuration file does not exist: {p}")

    # Check current directory
    cwd = Path.cwd()
    for name in WORKSPACE_PROFILE_NAMES:
        candidate = cwd / name
        if candidate.exists():
            return candidate

    # Check ~/.config/contribscout/profile.yaml
    if DEFAULT_PROFILE_PATH.exists():
        return DEFAULT_PROFILE_PATH

    return None


def validate_profile_dict(data: Dict[str, Any]) -> List[str]:
    """
    Validate raw dictionary against profile schema.
    Returns a list of human-readable error messages.
    """
    errors: List[str] = []

    if not isinstance(data, dict):
        return ["Profile configuration must be a mapping/dictionary."]

    # 1. Languages validation
    langs = data.get("languages")
    if langs is not None:
        if isinstance(langs, dict):
            for lang, prof in langs.items():
                if not isinstance(lang, str) or not lang.strip():
                    errors.append("Field 'languages': Language names must be non-empty strings.")
                if str(prof).lower() not in VALID_EXPERIENCE_LEVELS:
                    errors.append(
                        f"Field 'languages.{lang}': Invalid proficiency '{prof}'. "
                        f"Must be one of: {', '.join(sorted(VALID_EXPERIENCE_LEVELS))}."
                    )
        elif isinstance(langs, list):
            for item in langs:
                if not isinstance(item, str) or not item.strip():
                    errors.append("Field 'languages': Language items must be non-empty strings.")
        else:
            errors.append("Field 'languages': Must be a dictionary of language -> proficiency or list of languages.")

    # 2. Experience level validation
    exp = data.get("experience_level")
    if exp is not None:
        if str(exp).lower() not in VALID_EXPERIENCE_LEVELS:
            errors.append(
                f"Field 'experience_level': '{exp}' is not valid. "
                f"Must be one of: {', '.join(sorted(VALID_EXPERIENCE_LEVELS))}."
            )

    # 3. Hours per week
    hpw = data.get("hours_per_week")
    if hpw is not None:
        try:
            val = float(hpw)
            if val <= 0:
                errors.append(f"Field 'hours_per_week': Value must be positive, got {hpw}.")
            elif val > 168:
                errors.append(f"Field 'hours_per_week': Cannot exceed 168 hours in a week, got {hpw}.")
        except (ValueError, TypeError):
            errors.append(f"Field 'hours_per_week': Must be a numeric value, got '{hpw}'.")

    # 4. Preferred duration
    dur = data.get("preferred_duration")
    if dur is not None and str(dur).lower() not in VALID_DURATIONS:
        errors.append(
            f"Field 'preferred_duration': '{dur}' is not valid. "
            f"Must be one of: {', '.join(sorted(VALID_DURATIONS))}."
        )

    # 5. Desired difficulty
    diff = data.get("desired_difficulty")
    if diff is not None and str(diff).lower() not in VALID_DIFFICULTIES:
        errors.append(
            f"Field 'desired_difficulty': '{diff}' is not valid. "
            f"Must be one of: {', '.join(sorted(VALID_DIFFICULTIES))}."
        )

    # 6. Maturity
    mat = data.get("maturity")
    if mat is not None and str(mat).lower() not in VALID_MATURITIES:
        errors.append(
            f"Field 'maturity': '{mat}' is not valid. "
            f"Must be one of: {', '.join(sorted(VALID_MATURITIES))}."
        )

    # 7. Star limits
    min_stars = data.get("min_stars")
    max_stars = data.get("max_stars")
    if min_stars is not None:
        try:
            if int(min_stars) < 0:
                errors.append("Field 'min_stars': Cannot be negative.")
        except (ValueError, TypeError):
            errors.append(f"Field 'min_stars': Must be an integer, got '{min_stars}'.")

    if max_stars is not None:
        try:
            if int(max_stars) < 0:
                errors.append("Field 'max_stars': Cannot be negative.")
            elif min_stars is not None and int(max_stars) < int(min_stars):
                errors.append(
                    f"Field 'max_stars' ({max_stars}) cannot be smaller than 'min_stars' ({min_stars})."
                )
        except (ValueError, TypeError):
            errors.append(f"Field 'max_stars': Must be an integer or null, got '{max_stars}'.")

    # 8. Secret fields check (security requirement)
    for forbidden in ["token", "github_token", "api_key", "password", "secret"]:
        if forbidden in data:
            errors.append(
                f"Field '{forbidden}': Secrets must NOT be stored in profile files. "
                "Use the GITHUB_TOKEN environment variable instead."
            )

    return errors


def load_profile(path: Optional[Path] = None) -> UserProfile:
    """Load and validate UserProfile from disk or return default profile."""
    resolved_path = find_profile_path(str(path) if path else None)
    if not resolved_path:
        return UserProfile()

    try:
        content = resolved_path.read_text(encoding="utf-8")
        if resolved_path.suffix.lower() == ".json":
            raw_data = json.loads(content)
        else:
            raw_data = yaml.safe_load(content) or {}
    except Exception as exc:
        raise ConfigError(f"Failed to read or parse configuration file at {resolved_path}: {exc}")

    errors = validate_profile_dict(raw_data)
    if errors:
        error_lines = "\n  - " + "\n  - ".join(errors)
        raise ConfigError(
            f"Profile configuration validation failed for {resolved_path}:{error_lines}"
        )

    return UserProfile.from_dict(raw_data)


def load_scoring_weights(config_path: Optional[Path] = None) -> Tuple[Dict[str, float], List[str]]:
    """
    Load scoring weights from file or return normalized defaults.
    Validates non-negative weights and normalizes sum to 1.0.
    Returns (normalized_weights, normalization_warnings).
    """
    weights = dict(DEFAULT_WEIGHTS)
    warnings: List[str] = []

    target = config_path or Path("config/scoring.yaml")
    if target.exists():
        try:
            content = target.read_text(encoding="utf-8")
            data = yaml.safe_load(content) or {}
            custom_weights = data.get("weights", {})
            if isinstance(custom_weights, dict):
                for k, v in custom_weights.items():
                    try:
                        val = float(v)
                        if val < 0:
                            warnings.append(f"Scoring weight '{k}' is negative ({val}). Clamped to 0.0.")
                            val = 0.0
                        weights[k] = val
                    except (ValueError, TypeError):
                        warnings.append(f"Invalid weight for '{k}': '{v}'. Using default.")
        except Exception as exc:
            warnings.append(f"Could not load custom scoring weights from {target}: {exc}. Using defaults.")

    # Normalize weights so sum is 1.0
    total = sum(weights.values())
    if total <= 0:
        warnings.append("Total sum of scoring weights was zero or negative. Resetting to defaults.")
        weights = dict(DEFAULT_WEIGHTS)
        total = sum(weights.values())

    if abs(total - 1.0) > 1e-4:
        warnings.append(f"Weights sum to {total:.3f}. Automatically normalizing to 1.0.")
        weights = {k: v / total for k, v in weights.items()}

    return weights, warnings


def init_profile(target_path: Optional[Path] = None, overwrite: bool = False) -> Path:
    """
    Create a new user profile with sensible defaults and explanatory comments.
    Guarantees existing file is never overwritten unless overwrite=True.
    """
    out_path = target_path or Path("profile.yaml")
    if out_path.exists() and not overwrite:
        raise FileExistsError(
            f"Configuration file already exists at {out_path}. "
            "Use --force to overwrite if intended."
        )

    # Ensure parent directory exists
    out_path.parent.mkdir(parents=True, exist_ok=True)

    template_path = Path(__file__).resolve().parent.parent.parent / "config" / "profile.example.yaml"
    if template_path.exists():
        template_content = template_path.read_text(encoding="utf-8")
    else:
        # Fallback inline template
        profile = UserProfile()
        template_content = yaml.dump(profile.to_dict(), default_flow_style=False)

    out_path.write_text(template_content, encoding="utf-8")
    return out_path
