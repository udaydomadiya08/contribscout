# Contributing to ContribScout

Thank you for your interest in contributing to **ContribScout**! ContribScout is an open-source project designed to make discovering meaningful GitHub contributions accessible, transparent, and privacy-conscious.

## Code of Conduct

All contributors and maintainers are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## Getting Started

### 1. Prerequisites
- Python 3.10, 3.11, or 3.12.
- Git.
- Optional: GitHub CLI (`gh`).

### 2. Local Setup
```bash
# Clone the repository
git clone https://github.com/udaydomadiya08/contribscout.git
cd contribscout

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode with development dependencies
pip install -e ".[dev]"
```

### 3. Verify Setup
```bash
contribscout doctor
pytest
```

---

## Development Guidelines

1. **Keep it Lightweight**: Prefer the standard library wherever possible. Do not introduce heavy dependencies (e.g. big frameworks, databases, or local ML models).
2. **Determinism**: The scoring engine in `src/contribscout/analysis/scoring.py` must remain strictly deterministic.
3. **Security First**: Never log or print tokens, never auto-execute external code, and always escape external strings in HTML reports.
4. **Comprehensive Tests**: Add automated unit tests for every new feature or bug fix.

### Running Tests
```bash
# Run unit tests with coverage
pytest --cov=contribscout tests/

# Run performance benchmark
python benchmark.py
```

---

## Submitting a Pull Request

1. Create a descriptive feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes and ensure all tests pass:
   ```bash
   pytest
   ```
3. Commit your changes with clear commit messages.
4. Push your branch and open a Pull Request against `main`.
