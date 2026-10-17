"""Command Line Interface (CLI) for ContribScout."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
import sys
from typing import List, Optional
import urllib.parse

from contribscout import __version__
from contribscout.ai.optional_provider import get_ai_provider
from contribscout.analysis.deduplication import deduplicate_opportunities
from contribscout.analysis.eligibility import evaluate_eligibility
from contribscout.analysis.scoring import calculate_opportunity_score
from contribscout.config import (
    ConfigError,
    find_profile_path,
    init_profile,
    load_profile,
    load_scoring_weights,
    validate_profile_dict,
)
from contribscout.discovery.coordinator import DiscoveryEngine, normalize_issue, normalize_repository
from contribscout.discovery.github_api import GitHubAPIClient, resolve_github_token
from contribscout.discovery.github_cli import GitHubCLIClient
from contribscout.models import Opportunity, ScanReport, ScoredOpportunity
from contribscout.reports.html_report import generate_html_report
from contribscout.reports.json_report import generate_json_report
from contribscout.reports.markdown_report import generate_markdown_report
from contribscout.storage.history import HistoryTracker

logger = logging.getLogger("contribscout")


def setup_logging(verbose: bool) -> None:
    """Configure terminal logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s" if not verbose else "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def cmd_version(args: argparse.Namespace) -> int:
    """Print version information."""
    print(f"ContribScout v{__version__}")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize a new developer profile configuration file."""
    target = Path(args.path) if args.path else Path("profile.yaml")
    try:
        out_path = init_profile(target, overwrite=args.force)
        print(f"✓ Created developer profile configuration at: {out_path.resolve()}")
        print("  Edit this file to customize your programming languages, frameworks, and contribution interests.")
        print("  Next, run: contribscout scan")
        return 0
    except FileExistsError as fee:
        print(f"Error: {fee}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error initializing profile: {exc}", file=sys.stderr)
        return 1


def cmd_config_validate(args: argparse.Namespace) -> int:
    """Validate a profile configuration file and report exact errors."""
    try:
        resolved = find_profile_path(args.profile)
        if not resolved:
            print("Error: No profile configuration file found to validate.", file=sys.stderr)
            print("Run 'contribscout init' to create one.", file=sys.stderr)
            return 1

        import yaml
        content = resolved.read_text(encoding="utf-8")
        data = yaml.safe_load(content) or {}
        errors = validate_profile_dict(data)

        if errors:
            print(f"✗ Profile validation failed for {resolved}:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            return 1

        print(f"✓ Configuration file {resolved} is valid.")
        return 0
    except Exception as exc:
        print(f"Error validating configuration: {exc}", file=sys.stderr)
        return 1


def cmd_doctor(args: argparse.Namespace) -> int:
    """Verify local environment, tools, network, and GitHub authentication."""
    print("=== ContribScout Diagnostic Health Check ===")
    all_ok = True

    # 1. Python runtime
    py_ver = sys.version.split()[0]
    print(f"✓ Python runtime: {py_ver} (>= 3.10 required)")

    # 2. Profile configuration
    profile_path = find_profile_path(args.profile)
    if profile_path:
        print(f"✓ Profile configuration found: {profile_path}")
    else:
        print("! Profile configuration: None found in workspace (run 'contribscout init')")

    # 3. GitHub CLI availability
    if GitHubCLIClient.is_available():
        if GitHubCLIClient.is_authenticated():
            print("✓ GitHub CLI (gh): Installed and authenticated")
        else:
            print("! GitHub CLI (gh): Installed but not authenticated (run 'gh auth login')")
    else:
        print("i GitHub CLI (gh): Not installed (REST API backend will be used)")

    # 4. Authentication Token
    token = resolve_github_token()
    if token:
        masked = token[:4] + "..." + token[-4:] if len(token) > 8 else "***"
        print(f"✓ GitHub Token: Detected ({masked})")
    else:
        print("! GitHub Token: None detected (rate limits limited to 60 req/hr; set GITHUB_TOKEN for 5,000 req/hr)")

    # 5. Network connectivity & API rate limits
    client = GitHubAPIClient(token=token)
    try:
        limits = client.get_rate_limit()
        core_rem = limits.get("core_remaining")
        core_lim = limits.get("core_limit")
        search_rem = limits.get("search_remaining")
        print(f"✓ GitHub API Connectivity: Connected successfully")
        print(f"  - Core API Rate Limit: {core_rem} / {core_lim} remaining")
        print(f"  - Search API Rate Limit: {search_rem} remaining")
    except Exception as exc:
        print(f"✗ GitHub API Connectivity failed: {exc}", file=sys.stderr)
        all_ok = False

    print("============================================")
    return 0 if all_ok else 1


def cmd_show(args: argparse.Namespace) -> int:
    """Display active profile summary or status."""
    try:
        if getattr(args, "last_report", False):
            tracker = HistoryTracker()
            entries = tracker.get_all_entries()
            if not entries:
                print("No recent scan reports or opportunities recorded. Run 'contribscout scan' first.")
                return 0
            print(f"=== Last Scan Summary ({len(entries)} recorded opportunities) ===")
            print(f"{'ID':<30} {'SCORE':<7} {'STATE':<7} {'LAST SEEN':<22} TITLE")
            print("-" * 90)
            for e in entries[:10]:
                title = e.title[:30] + "..." if len(e.title) > 30 else e.title
                print(f"{e.opportunity_id:<30} {e.last_score:<7.1f} {e.state:<7} {e.last_seen_at:<22} {title}")
            return 0

        profile = load_profile(Path(args.profile) if args.profile else None)
        path = find_profile_path(args.profile)
        print(f"Active Profile: {path or 'Default In-Memory'}")
        print(f"Experience Level : {profile.experience_level}")
        print(f"Hours / Week     : {profile.hours_per_week}")
        print(f"Preferred Duration: {profile.preferred_duration}")
        print(f"Languages        : {', '.join(f'{k} ({v})' for k, v in profile.languages.items())}")
        print(f"Interests        : {', '.join(profile.interests) or 'None'}")
        print(f"Contribution Types: {', '.join(profile.contribution_types)}")
        print(f"Star Limits      : Min {profile.min_stars}, Max {profile.max_stars or 'None'}")
        return 0
    except Exception as exc:
        print(f"Error displaying profile: {exc}", file=sys.stderr)
        return 1


def cmd_history(args: argparse.Namespace) -> int:
    """View or clear previously scanned opportunities."""
    tracker = HistoryTracker()
    if args.clear:
        tracker.clear()
        print("✓ Local history cleared.")
        return 0

    entries = tracker.get_all_entries()
    if not entries:
        print("No historical scans recorded yet. Run 'contribscout scan' to discover opportunities.")
        return 0

    limit = args.limit or 20
    print(f"Recorded Opportunities ({len(entries)} total, showing up to {limit}):\n")
    print(f"{'ID':<30} {'SCORE':<7} {'STATE':<7} {'LAST SEEN':<22} TITLE")
    print("-" * 90)
    for e in entries[:limit]:
        title = e.title[:30] + "..." if len(e.title) > 30 else e.title
        print(f"{e.opportunity_id:<30} {e.last_score:<7.1f} {e.state:<7} {e.last_seen_at:<22} {title}")
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    """Fetch and evaluate a specific issue URL and generate a contribution plan."""
    issue_url = args.issue_url.strip()
    match = re.search(r"github\.com/([^/]+)/([^/]+)/issues/(\d+)", issue_url)
    if not match:
        print(f"Error: Invalid GitHub issue URL: '{issue_url}'.", file=sys.stderr)
        print("Expected format: https://github.com/owner/repo/issues/123", file=sys.stderr)
        return 1

    owner, repo, number_str = match.groups()
    number = int(number_str)

    try:
        profile = load_profile(Path(args.profile) if args.profile else None)
        client = GitHubAPIClient()

        print(f"Fetching {owner}/{repo}#{number}...")
        raw_issue = client.get_issue(owner, repo, number)
        if not raw_issue:
            print(f"Error: Could not retrieve issue #{number} from {owner}/{repo}.", file=sys.stderr)
            return 1

        raw_repo = client.get_repository(owner, repo)
        repo_model = normalize_repository(raw_repo, f"{owner}/{repo}")
        opportunity = normalize_issue(raw_issue, repo_model)

        eligibility = evaluate_eligibility(opportunity, profile)
        score = calculate_opportunity_score(opportunity, profile)

        # Print terminal explanation
        print("\n" + "=" * 80)
        print(f"CONTRIBSCOUT EXPLANATION: {opportunity.repo_full_name}#{opportunity.number}")
        print("=" * 80)
        print(f"Title     : {opportunity.title}")
        print(f"URL       : {opportunity.url}")
        print(f"Type      : {opportunity.inferred_type}")
        print(f"State     : {opportunity.state}")
        print(f"Eligible  : {'Yes' if eligibility.is_eligible else 'No'}")
        if not eligibility.is_eligible:
            print("Exclusion Reasons:")
            for r in eligibility.reasons:
                print(f"  - {r}")

        print(f"\nFinal Score       : {score.final_score} / 10.0")
        print(f"Confidence        : {score.confidence} ({score.confidence_score*100:.0f}%)")
        print(f"Estimated Difficulty: {score.estimated_difficulty}")
        print(f"Estimated Effort  : {score.estimated_effort_hours}")
        print(f"Match Summary     : {score.why_matched}")

        print("\nCriterion Scores:")
        for crit, val in score.score_breakdown.items():
            print(f"  - {crit:<28}: {val:>4.1f}/10  ({score.justifications.get(crit, '')})")

        if score.plan:
            plan = score.plan
            print("\nActionable Investigation Plan:")
            print(f"  1. Problem: {plan.problem_summary}")
            print(f"  2. Importance: {plan.importance}")
            print(f"  3. Read First: {', '.join(plan.what_to_read_first)}")
            print(f"  4. Likely Files: {', '.join(plan.likely_files_or_subsystems)}")
            print(f"  5. Hypothesis: {plan.implementation_hypothesis}")
            print(f"  6. First Action: {plan.suggested_first_action}")

        print("=" * 80 + "\n")
        return 0
    except Exception as exc:
        print(f"Error explaining issue: {exc}", file=sys.stderr)
        return 1


def cmd_scan(args: argparse.Namespace) -> int:
    """Discover, filter, score, rank, and report contribution opportunities."""
    setup_logging(args.verbose)

    try:
        profile = load_profile(Path(args.profile) if args.profile else None)
        weights, weight_warnings = load_scoring_weights()
    except ConfigError as ce:
        print(f"Configuration Error: {ce}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error loading configuration: {exc}", file=sys.stderr)
        return 1

    limit = args.limit or profile.max_candidates
    min_score = args.min_score if args.min_score is not None else 4.0

    print(f"🔍 ContribScout scanning GitHub for opportunities (target: up to {limit})...")
    discovery = DiscoveryEngine(backend=args.backend)

    raw_candidates, discovery_warnings, rate_limit_info = discovery.discover(
        profile=profile,
        max_candidates=limit * 2,  # Fetch pool to allow for eligibility filtering
    )

    all_warnings = weight_warnings + discovery_warnings
    deduped = deduplicate_opportunities(raw_candidates)

    eligible_opps: List[Opportunity] = []
    excluded_count = 0

    for opp in deduped:
        verdict = evaluate_eligibility(opp, profile)
        if verdict.is_eligible:
            eligible_opps.append(opp)
        else:
            excluded_count += 1
            if args.verbose:
                logger.debug(f"Excluded {opp.id}: {', '.join(verdict.reasons)}")

    # Score eligible opportunities
    history_tracker = HistoryTracker()
    scored_list: List[ScoredOpportunity] = []
    ai_provider = get_ai_provider("none" if not args.ai else "openai")

    for opp in eligible_opps:
        score = calculate_opportunity_score(opp, profile, weights=weights)
        if score.final_score >= min_score:
            if args.ai and score.plan:
                score.plan = ai_provider.enrich_plan(opp, profile, score.plan)

            badge, _ = history_tracker.record_scan(opp, score)
            scored_list.append(ScoredOpportunity(opportunity=opp, score=score, status_badge=badge))

    # Sort descending by final_score
    scored_list.sort(key=lambda s: s.score.final_score, reverse=True)
    # Assign ranks
    for rank_idx, item in enumerate(scored_list[:limit], start=1):
        item.rank = rank_idx

    final_opps = scored_list[:limit]
    history_tracker.save()

    report = ScanReport(
        timestamp_utc=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        profile_summary=profile.to_dict(),
        search_scope={
            "languages": list(profile.languages.keys()),
            "interests": profile.interests,
            "min_stars": profile.min_stars,
            "backend": discovery.active_backend,
        },
        stats={
            "candidates_found": len(raw_candidates),
            "candidates_excluded": excluded_count,
            "candidates_deduplicated": len(raw_candidates) - len(deduped),
            "candidates_scored": len(final_opps),
        },
        opportunities=final_opps,
        warnings=all_warnings,
        discovery_backend=discovery.active_backend,
        rate_limit_info=rate_limit_info,
    )

    # Format output
    fmt = (args.format or "markdown").lower()
    if fmt == "json":
        output_content = generate_json_report(report)
    elif fmt == "html":
        output_content = generate_html_report(report)
    else:
        output_content = generate_markdown_report(report)

    # Write or print report
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_content, encoding="utf-8")
        print(f"\n✓ Generated {fmt.upper()} report saved to: {out_path.resolve()}")
    else:
        print("\n" + output_content)

    print(
        f"\n✓ Scan complete: {len(raw_candidates)} found, "
        f"{excluded_count} excluded, {len(final_opps)} ranked."
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build root CLI argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="contribscout",
        description="ContribScout — Personalized Open-Source Contribution Discovery Agent.",
    )
    parser.add_argument("-v", "--version", action="store_true", help="Show ContribScout version")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # init
    p_init = subparsers.add_parser("init", help="Create a user profile configuration file")
    p_init.add_argument("--path", type=str, default="profile.yaml", help="Path to save configuration")
    p_init.add_argument("--force", "-f", action="store_true", help="Overwrite existing configuration file")

    # scan
    p_scan = subparsers.add_parser("scan", help="Discover and rank contribution opportunities")
    p_scan.add_argument("--profile", "-p", type=str, help="Path to custom profile configuration")
    p_scan.add_argument("--limit", "-l", type=int, help="Maximum opportunities to rank")
    p_scan.add_argument("--format", choices=["markdown", "json", "html"], default="markdown", help="Output report format")
    p_scan.add_argument("--output", "-o", type=str, help="Save report to specified file path")
    p_scan.add_argument("--verbose", action="store_true", help="Enable verbose diagnostic output")
    p_scan.add_argument("--backend", choices=["auto", "api", "gh"], default="auto", help="GitHub discovery backend")
    p_scan.add_argument("--min-score", type=float, default=4.0, help="Minimum score threshold (0-10)")
    p_scan.add_argument("--ai", action="store_true", help="Enable optional AI hypothesis enrichment")

    # explain
    p_explain = subparsers.add_parser("explain", help="Evaluate and plan for a specific GitHub issue URL")
    p_explain.add_argument("issue_url", type=str, help="Full GitHub issue URL")
    p_explain.add_argument("--profile", "-p", type=str, help="Path to custom profile configuration")
    p_explain.add_argument("--verbose", action="store_true", help="Enable verbose diagnostics")

    # show
    p_show = subparsers.add_parser("show", help="Display active profile summary or last scan report")
    p_show.add_argument("--profile", "-p", type=str, help="Path to custom profile configuration")
    p_show.add_argument("--last-report", action="store_true", help="Display summary of the most recently discovered opportunities")

    # config validate
    p_val = subparsers.add_parser("config", help="Configuration utilities")
    val_sub = p_val.add_subparsers(dest="config_subcommand")
    p_val_val = val_sub.add_parser("validate", help="Validate profile configuration file")
    p_val_val.add_argument("--profile", "-p", type=str, help="Path to custom profile configuration")

    # doctor
    p_doc = subparsers.add_parser("doctor", help="Check local environment, tools, and GitHub connection")
    p_doc.add_argument("--profile", "-p", type=str, help="Path to custom profile configuration")

    # history
    p_hist = subparsers.add_parser("history", help="View or clear local historical discovery records")
    p_hist.add_argument("--limit", "-l", type=int, default=20, help="Limit number of entries displayed")
    p_hist.add_argument("--clear", action="store_true", help="Clear historical records")

    # version
    subparsers.add_parser("version", help="Show ContribScout version")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        return cmd_version(args)

    if not args.command:
        parser.print_help()
        return 0

    command_handlers = {
        "init": cmd_init,
        "scan": cmd_scan,
        "explain": cmd_explain,
        "show": cmd_show,
        "config": cmd_config_validate,
        "doctor": cmd_doctor,
        "history": cmd_history,
        "version": cmd_version,
    }

    handler = command_handlers.get(args.command)
    if handler:
        try:
            return handler(args)
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.", file=sys.stderr)
            return 130
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
