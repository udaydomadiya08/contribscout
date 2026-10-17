# ContribScout — Troubleshooting & Common Issues

## Diagnostic Health Check

Always begin by running the built-in diagnostic doctor:

```bash
contribscout doctor
```

This tests:
1. Python runtime version ($\ge 3.10$).
2. Profile configuration presence and validity.
3. GitHub CLI (`gh`) presence and authentication status.
4. GitHub token detection (`GITHUB_TOKEN` or `GH_TOKEN`).
5. Live network connectivity to the GitHub REST API and remaining rate limits.

---

## GitHub API Rate Limits

### Symptom: `RateLimitExceededError: GitHub API rate limit exceeded`

**Explanation**:
GitHub imposes rate limits on API requests:
- **Unauthenticated requests**: 60 requests per hour per IP.
- **Authenticated requests (Personal Access Token or GitHub CLI)**: 5,000 requests per hour.

**Resolution**:
1. **Option A (Recommended)**: Set a personal access token via environment variable:
   ```bash
   export GITHUB_TOKEN="ghp_your_personal_access_token"
   ```
   *Required Scopes*: None for public repositories. A fine-grained token with "Public Repositories (read-only)" is ideal.

2. **Option B**: Authenticate with the official GitHub CLI:
   ```bash
   gh auth login
   ```
   ContribScout automatically detects your active `gh` session and uses it for discovery.

3. **Option C**: Lower discovery limits in your profile configuration:
   ```yaml
   max_candidates: 15
   api_budget_requests: 25
   rate_limit_pause_seconds: 2.0
   ```

---

## Configuration Validation Errors

### Symptom: `Profile configuration validation failed`

Run:
```bash
contribscout config validate
```

Common configuration errors:
- `experience_level`: Must be one of `beginner`, `intermediate`, `advanced`, `expert`.
- `hours_per_week`: Must be a positive number $\le 168$.
- `max_stars` cannot be lower than `min_stars`.
- Never include secrets, passwords, or tokens in your profile file.

---

## Clearing or Resetting Local History

If you want to clear previously seen opportunities:

```bash
contribscout history --clear
```

The history file is stored locally at `~/.config/contribscout/history.json`. Deleting this file will safely reset history to a clean state.
