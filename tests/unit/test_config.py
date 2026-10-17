"""Unit tests for ContribScout configuration loading, validation, and initialization."""

from pathlib import Path
import pytest
import yaml

from contribscout.config import (
    ConfigError,
    find_profile_path,
    init_profile,
    load_profile,
    load_scoring_weights,
    validate_profile_dict,
)
from contribscout.models import UserProfile


def test_validate_profile_dict_valid():
    data = {
        "languages": {"python": "advanced", "javascript": "intermediate"},
        "experience_level": "intermediate",
        "hours_per_week": 10.0,
        "preferred_duration": "medium",
        "desired_difficulty": "intermediate",
        "min_stars": 100,
        "max_stars": 5000,
        "maturity": "growing",
    }
    errors = validate_profile_dict(data)
    assert errors == []


def test_validate_profile_dict_invalid_fields():
    data = {
        "experience_level": "grandmaster",  # Invalid
        "hours_per_week": -5,  # Negative
        "preferred_duration": "forever",  # Invalid
        "desired_difficulty": "impossible",  # Invalid
        "min_stars": 500,
        "max_stars": 100,  # max < min
        "token": "ghp_secret_12345",  # Secret in profile
    }
    errors = validate_profile_dict(data)
    assert any("experience_level" in e for e in errors)
    assert any("hours_per_week" in e for e in errors)
    assert any("preferred_duration" in e for e in errors)
    assert any("desired_difficulty" in e for e in errors)
    assert any("smaller than 'min_stars'" in e for e in errors)
    assert any("Secrets must NOT be stored" in e for e in errors)


def test_load_profile_defaults(tmp_path):
    # None should return default UserProfile
    profile = load_profile(None)
    assert isinstance(profile, UserProfile)
    assert "python" in profile.languages

    # Explicit non-existent path should raise FileNotFoundError
    with pytest.raises(FileNotFoundError):
        load_profile(tmp_path / "does_not_exist.yaml")


def test_load_profile_custom_yaml(tmp_path):
    custom_yaml = tmp_path / "custom.yaml"
    custom_yaml.write_text(
        yaml.dump({
            "languages": {"rust": "advanced"},
            "experience_level": "advanced",
            "hours_per_week": 15,
        }),
        encoding="utf-8",
    )
    profile = load_profile(custom_yaml)
    assert profile.experience_level == "advanced"
    assert profile.languages.get("rust") == "advanced"
    assert profile.hours_per_week == 15.0


def test_init_profile_preserves_existing(tmp_path):
    target = tmp_path / "my_profile.yaml"
    init_profile(target)
    assert target.exists()

    # Attempting without force must raise FileExistsError
    with pytest.raises(FileExistsError):
        init_profile(target, overwrite=False)

    # With force, succeeds
    init_profile(target, overwrite=True)
    assert target.exists()


def test_load_scoring_weights_normalization(tmp_path):
    scoring_file = tmp_path / "custom_scoring.yaml"
    # Weights sum to 2.0 and has a negative weight
    scoring_file.write_text(
        yaml.dump({
            "weights": {
                "practical_usefulness": 1.0,
                "feasibility": 1.0,
                "technical_depth": -0.5,
                "maintainer_responsiveness": 0.0,
                "learning_and_portfolio": 0.0,
                "repository_health": 0.0,
            }
        }),
        encoding="utf-8",
    )
    weights, warnings = load_scoring_weights(scoring_file)
    # Sum should be normalized to 1.0
    assert abs(sum(weights.values()) - 1.0) < 1e-4
    assert weights["practical_usefulness"] == 0.5
    assert weights["feasibility"] == 0.5
    assert weights["technical_depth"] == 0.0  # Clamped
    assert len(warnings) > 0


def test_load_profile_corrupted_syntax(tmp_path):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("languages: [invalid yaml: {unclosed", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_profile(bad_yaml)


def test_validate_profile_non_dict():
    errors = validate_profile_dict(["not", "a", "dict"])
    assert any("mapping/dictionary" in e for e in errors)
