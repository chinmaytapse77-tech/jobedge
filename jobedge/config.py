"""Configuration loading for JobEdge: profiles, locations, and pipeline settings."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

DEFAULT_MIN_FIT_SCORE = 50
DEFAULT_REQUEST_DELAY_SECONDS = 2.0
DEFAULT_DB_PATH = "jobedge.db"
DEFAULT_SOURCES = ["job_bank", "company_pages", "eluta"]

REQUIRED_PROFILE_FIELDS = (
    "name",
    "target_titles",
    "keywords",
    "my_skills",
    "experience_years",
    "resume_path",
)


class ConfigError(Exception):
    """Raised when config.yaml is missing or a profile is malformed."""


@dataclass
class Profile:
    name: str
    target_titles: list[str]
    keywords: list[str]
    my_skills: list[str]
    experience_years: int
    resume_path: str
    keywords_fr: list[str] = field(default_factory=list)


@dataclass
class Config:
    profiles: list[Profile]
    target_locations: list[dict[str, str]]
    db_path: str = DEFAULT_DB_PATH
    min_fit_score: int = DEFAULT_MIN_FIT_SCORE
    sources: list[str] = field(default_factory=lambda: list(DEFAULT_SOURCES))
    request_delay_seconds: float = DEFAULT_REQUEST_DELAY_SECONDS
    use_mock_fetcher: bool = True


def _build_profile(raw: dict, index: int) -> Profile:
    missing = [key for key in REQUIRED_PROFILE_FIELDS if key not in raw]
    if missing:
        raise ConfigError(
            f"profiles[{index}] ('{raw.get('name', '?')}') is missing required "
            f"field(s): {', '.join(missing)}"
        )
    return Profile(
        name=raw["name"],
        target_titles=list(raw["target_titles"]),
        keywords=list(raw["keywords"]),
        my_skills=list(raw["my_skills"]),
        experience_years=int(raw["experience_years"]),
        resume_path=raw["resume_path"],
        keywords_fr=list(raw.get("keywords_fr", [])),
    )


def load_config(path: str | Path = "config.yaml") -> Config:
    """Load and validate Config from a YAML file.

    Raises ConfigError if the file is missing, empty, or a profile/location
    block is malformed. Fails clearly rather than silently defaulting.
    """
    load_dotenv()  # the one place secrets are loaded, per steering rule 4/14
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"config.yaml not found at {config_path.resolve()}")

    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    raw_profiles = raw.get("profiles")
    if not raw_profiles:
        raise ConfigError("config.yaml must define at least one profile under 'profiles:'")
    profiles = [_build_profile(entry, i) for i, entry in enumerate(raw_profiles)]

    target_locations = raw.get("target_locations")
    if not target_locations:
        raise ConfigError(
            "config.yaml must define at least one location under 'target_locations:'"
        )
    for i, loc in enumerate(target_locations):
        if "city" not in loc or "province" not in loc:
            raise ConfigError(f"target_locations[{i}] must have 'city' and 'province'")

    return Config(
        profiles=profiles,
        target_locations=list(target_locations),
        db_path=raw.get("db_path", DEFAULT_DB_PATH),
        min_fit_score=int(raw.get("min_fit_score", DEFAULT_MIN_FIT_SCORE)),
        sources=list(raw.get("sources", DEFAULT_SOURCES)),
        request_delay_seconds=float(
            raw.get("request_delay_seconds", DEFAULT_REQUEST_DELAY_SECONDS)
        ),
        use_mock_fetcher=bool(raw.get("use_mock_fetcher", True)),
    )
