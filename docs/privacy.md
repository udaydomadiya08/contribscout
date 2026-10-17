# ContribScout — Privacy & Security Guarantees

ContribScout is built on **privacy-by-default** and **security-first** principles.

## 1. Zero Telemetry & Local-First Processing
- ContribScout contains **zero telemetry**, analytics, phone-home beacons, or usage tracking.
- Your developer profile, search queries, historical scan records, and generated reports remain strictly on your local filesystem.
- No user data is ever uploaded to remote servers or third-party cloud services.

## 2. Strict Secret Hygiene
- ContribScout **never writes credentials or tokens to reports, history files, or logs**.
- Personal Access Tokens are read in-memory from standard environment variables (`GITHUB_TOKEN`, `GH_TOKEN`) or the system `gh auth token` helper.
- The configuration validator explicitly rejects profile configuration files containing fields named `token`, `secret`, `password`, or `api_key`.

## 3. Untrusted External Data Handling
All GitHub issue titles, descriptions, comments, and README content fetched from public repositories are treated as **untrusted external data**:
- **Zero Automatic Code Execution**: ContribScout never clones or executes code discovered in repositories.
- **XSS & Injection Protection**: HTML report generation passes all external strings through `html.escape`. Control characters and raw markdown injections are sanitized.
- **Prompt Injection Defense**: When optional AI integration is enabled, instructions in external issue text that attempt to override system rules or request sensitive environment information are strictly ignored by prompt boundaries.

## 4. Non-Intrusive Operation
- ContribScout is strictly a **read-only discovery agent**.
- It will never automatically post comments, star repositories, open issues, fork repositories, or submit pull requests. All actions require deliberate developer agency.

## 5. Responsible Disclosure
If you discover a security vulnerability in ContribScout, please report it according to our [Security Policy](../SECURITY.md).
