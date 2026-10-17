"""Lightweight local historical tracking for cross-run deduplication and status delta tracking."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from contribscout.models import HistoryEntry, Opportunity, OpportunityScore

logger = logging.getLogger(__name__)

DEFAULT_HISTORY_DIR = Path.home() / ".config" / "contribscout"
DEFAULT_HISTORY_FILE = DEFAULT_HISTORY_DIR / "history.json"


class HistoryTracker:
    """Manages persistent history of scanned opportunities with atomic writes and corruption recovery."""

    def __init__(self, filepath: Optional[Path] = None):
        self.filepath = filepath or DEFAULT_HISTORY_FILE
        self.entries: Dict[str, HistoryEntry] = {}
        self._load()

    def _load(self) -> None:
        """Load history from disk safely; recovers on corruption."""
        if not self.filepath.exists():
            self.entries = {}
            return

        try:
            content = self.filepath.read_text(encoding="utf-8")
            if not content.strip():
                self.entries = {}
                return
            raw_data = json.loads(content)
            self.entries = {
                k: HistoryEntry.from_dict(v)
                for k, v in raw_data.items()
                if isinstance(v, dict)
            }
        except Exception as exc:
            logger.warning(
                f"History file at {self.filepath} was unreadable or corrupted ({exc}). "
                "Reinitializing fresh local history."
            )
            self.entries = {}

    def save(self) -> None:
        """Save history atomically using a temporary file to prevent corruption."""
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.filepath.with_suffix(".tmp")
            data = {k: v.to_dict() for k, v in self.entries.items()}
            temp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            temp_path.replace(self.filepath)
        except Exception as exc:
            logger.error(f"Failed to persist history file: {exc}")

    def evaluate_status_badge(
        self,
        opp_id: str,
        current_score: float,
    ) -> str:
        """
        Determine whether opportunity is NEW, UPDATED, or SEEN.
        Score changes of >= 0.5 are flagged as UPDATED.
        """
        if opp_id not in self.entries:
            return "NEW"

        past_entry = self.entries[opp_id]
        if abs(past_entry.last_score - current_score) >= 0.5:
            return "UPDATED"

        return "SEEN"

    def record_scan(
        self,
        opportunity: Opportunity,
        score: OpportunityScore,
    ) -> Tuple[str, Optional[float]]:
        """
        Record or update an opportunity in history.
        Returns: (status_badge, previous_score)
        """
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        opp_id = opportunity.id

        badge = self.evaluate_status_badge(opp_id, score.final_score)
        prev_score = self.entries[opp_id].last_score if opp_id in self.entries else None

        if opp_id in self.entries:
            entry = self.entries[opp_id]
            entry.last_seen_at = now_str
            entry.last_score = score.final_score
            entry.state = opportunity.state
            entry.title = opportunity.title
        else:
            self.entries[opp_id] = HistoryEntry(
                opportunity_id=opp_id,
                title=opportunity.title,
                url=opportunity.url,
                repo_full_name=opportunity.repo_full_name,
                first_seen_at=now_str,
                last_seen_at=now_str,
                last_score=score.final_score,
                state=opportunity.state,
            )

        return badge, prev_score

    def get_all_entries(self) -> List[HistoryEntry]:
        """Return all historical records sorted by last_seen_at desc."""
        return sorted(
            self.entries.values(),
            key=lambda e: e.last_seen_at,
            reverse=True,
        )

    def clear(self) -> None:
        """Clear all historical records."""
        self.entries = {}
        if self.filepath.exists():
            try:
                self.filepath.unlink()
            except Exception:
                pass
