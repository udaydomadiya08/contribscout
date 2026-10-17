# Changelog

All notable changes to **ContribScout** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-17

### Added
- **Core CLI**:
  - `contribscout init`: Guided and non-interactive profile initialization with explanatory comments and `--force` protection.
  - `contribscout scan`: Multi-query discovery, filtering, explainable scoring, ranking, and report generation.
  - `contribscout explain`: In-depth terminal evaluation and 10-point investigation plan for any GitHub issue URL.
  - `contribscout doctor`: Environment diagnostics testing Python version, Git, GitHub CLI, API connectivity, and rate limits.
  - `contribscout config validate`: Strict schema validation with actionable error messages indicating exact fields.
  - `contribscout history`: Local persistent history tracking `[NEW]`, `[SEEN]`, and `[UPDATED]` status deltas.
  - `contribscout show`: Summary display of current active developer profile.
  - `contribscout version`: Version printer.
- **Explainable 0–10 Scoring Engine**:
  - Six weighted criteria: Practical Usefulness (25%), Feasibility (20%), Technical Depth (20%), Maintainer Responsiveness (15%), Learning & Portfolio (10%), Repository Health (10%).
  - Deterministic evaluation: identical inputs and configuration produce identical scores.
  - Evidence density and confidence score adjustment to prevent inflating poorly-specified issues.
  - Protection against trivial tasks: well-defined engineering bug fixes decisively outrank typo fixes.
- **Actionable 10-Point Investigation Plans**:
  - Problem summary, importance, reading recommendations, evidence-based likely file extraction, reproduction steps, marked hypothesis, tests & regressions, maintainer questions, risks, and suggested first action.
- **Discovery Engine**:
  - Direct GitHub REST API backend with rate limit tracking (`X-RateLimit-Remaining`, `Reset`), exponential backoff retries, and in-memory repository metadata caching.
  - GitHub CLI (`gh api`) backend integration.
  - Support for `GITHUB_TOKEN` environment variable or authenticated `gh` session.
- **Reporting**:
  - GitHub Flavored Markdown reports with summary tables and shortlist plans.
  - Structured JSON reports with stable schema for integrations.
  - Responsive standalone dark-mode HTML reports with zero CDN dependencies and strict XSS escaping.
- **Testing & Benchmarking**:
  - Unit test suite with mock fixtures covering 100% of core analysis modules.
  - Reproducible benchmark script (`benchmark.py`) testing synthetic scoring at 3,000+ opps/sec with <6 MB RAM overhead.
  - Cross-platform GitHub Actions workflow for Ubuntu, macOS, and Windows on Python 3.10, 3.11, and 3.12.
