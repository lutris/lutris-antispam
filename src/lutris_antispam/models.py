"""Public data structures for the anti-spam engine.

These are intentionally plain dataclasses with no Django dependency so the
package can be imported and unit-tested in isolation. The website builds a
``Submission`` from a request and receives an ``Assessment`` back.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Verdict(str, Enum):
    """Outcome of scoring a submission."""

    CLEAN = "clean"
    UNCERTAIN = "uncertain"
    SPAM = "spam"


@dataclass(frozen=True)
class Submission:
    """Everything the engine is allowed to look at.

    All fields are optional so the caller can pass whatever it has; missing
    signals simply don't contribute to the score. ``account_age_days`` and
    ``library_game_count`` describe the submitting account.
    """

    name: str = ""
    description: str = ""
    website: str = ""
    reason: str = ""
    user_email: str = ""
    username: str = ""
    email_confirmed: bool = True
    profile_website: str = ""
    account_age_days: float | None = None
    library_game_count: int | None = None
    platforms: tuple[str, ...] = ()
    # Set by the website when this submission's website is a domain it has
    # already banned a submission over.
    website_seen_in_spam: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "Submission":
        """Build a Submission from a plain dict, ignoring unknown keys and
        coercing ``None`` text fields to empty strings."""
        known = {f: data.get(f) for f in cls.__dataclass_fields__}  # noqa: no-member
        for text_field in (
            "name",
            "description",
            "website",
            "reason",
            "user_email",
            "username",
            "profile_website",
        ):
            if known.get(text_field) is None:
                known[text_field] = ""
        if known.get("email_confirmed") is None:
            known["email_confirmed"] = True
        known["website_seen_in_spam"] = bool(known.get("website_seen_in_spam"))
        known["platforms"] = tuple(known.get("platforms") or ())
        return cls(**known)


@dataclass(frozen=True)
class RuleHit:
    """A single rule that matched, with the points it contributes."""

    rule: str
    weight: int
    detail: str = ""


@dataclass
class Assessment:
    """Result returned to the website. ``score`` is clamped to 0-100."""

    verdict: Verdict
    score: int
    hits: list[RuleHit] = field(default_factory=list)

    @property
    def matched_rules(self) -> list[str]:
        return [h.rule for h in self.hits]

    def as_dict(self) -> dict:
        return {
            "verdict": self.verdict.value,
            "score": self.score,
            "matched_rules": [
                {"rule": h.rule, "weight": h.weight, "detail": h.detail} for h in self.hits
            ],
        }
