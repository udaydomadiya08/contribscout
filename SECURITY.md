# Security Policy

ContribScout takes security and developer privacy seriously.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Security Principles

- **No Secret Storage**: ContribScout never persists tokens, credentials, or keys to disk, history, or reports.
- **Untrusted Input**: All external issue descriptions and repository content are treated as untrusted and escaped.
- **Read-Only**: ContribScout performs only read operations against public APIs; it never writes to remote repositories or executes remote code.

## Reporting a Vulnerability

If you discover a security vulnerability in ContribScout:

1. **Do not open a public GitHub issue.**
2. Send an email to the repository maintainers with:
   - A description of the vulnerability.
   - Steps to reproduce or a proof of concept.
   - Potential impact.
3. Maintainers will acknowledge your report within 48 hours and work with you on a coordinated fix.
