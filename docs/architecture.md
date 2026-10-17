# ContribScout — System Architecture

ContribScout is a local-first, privacy-conscious open-source contribution discovery agent built in Python.

It operates without any mandatory cloud backend, database server, or paid AI service.

```mermaid
graph TD
    User([Developer / CLI]) --> CLI[ContribScout CLI]
    CLI --> Config[Config Loader & Validator]
    Config --> Profile[(UserProfile)]

    CLI --> Discovery[Discovery Engine]
    Discovery --> Queries[Query Builder]
    Queries --> GHAPI[GitHub REST API]
    Queries --> GHCLI[GitHub CLI (gh)]

    GHAPI & GHCLI --> RawData[Raw Issue & Repo Metadata]
    RawData --> Normalizer[Data Normalizer & Sanitizer]
    Normalizer --> Dedup[Deduplication Layer]

    Dedup --> Eligibility[Eligibility & Diagnostic Filter]
    Eligibility -- Ineligible --> ExcludedLog[Diagnostic Exclusions]
    Eligibility -- Eligible --> Analysis[Analysis Pipeline]

    Analysis --> RepoHealth[Repository Health Assessment]
    Analysis --> Difficulty[Difficulty & 10-Point Plan Generator]
    Analysis --> Scoring[Explainable 0-10 Scoring Engine]

    Scoring --> AI[Optional AI Provider Interface]
    AI --> ScoredOpps[(Scored & Ranked Opportunities)]

    ScoredOpps --> History[Local History Tracker (history.json)]
    ScoredOpps --> Reports[Report Generators]
    Reports --> MarkdownReport[Markdown Report]
    Reports --> JSONReport[JSON Report]
    Reports --> HTMLReport[Standalone HTML Report]
```

## Architectural Principles

1. **Deterministic Baseline**:
   The authoritative scoring and ranking engine is 100% deterministic and mathematical. Given identical profile settings and issue metadata, it generates identical scores and rankings every time.

2. **Zero Mandatory Paid APIs**:
   ContribScout operates entirely on GitHub's public REST APIs or the official GitHub CLI. Optional AI integrations are strictly additive and guardrailed.

3. **Untrusted Data Hygiene**:
   All issue titles, descriptions, comments, and repository metadata fetched from external sources are treated as untrusted data:
   - Filepaths and module names are extracted using strict boundary matching; arbitrary paths are never hallucinated.
   - HTML reports sanitize and escape all external strings using `html.escape` to prevent XSS.
   - Fetched code is never executed locally during discovery.

4. **Modular Separation**:
   Each subsystem is decoupled with clear typed contracts:
   - `contribscout.discovery`: GitHub API and CLI query execution, rate limit tracking, and pagination.
   - `contribscout.analysis`: Eligibility filtering, repository health scoring, difficulty estimation, and 0-10 scoring.
   - `contribscout.storage`: Atomic persistent local history tracking.
   - `contribscout.reports`: Multi-format rendering (Markdown, JSON, HTML).
   - `contribscout.ai`: Provider-independent interface for optional hypothesis enrichment.

5. **Resource Efficiency**:
   - Repository metadata is cached in-memory during scans to eliminate duplicate API requests.
   - Evaluates up to 3,000+ opportunities per second in Python with less than 6 MB RAM overhead.
