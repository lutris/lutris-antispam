"""Scoring engine: run every rule, sum the weights, map to a verdict.

Thresholds are deliberately conservative on the destructive side. The website
only hard-deletes + bans on a ``SPAM`` verdict, and only sends the taunt email
when ``score >= MAX_CONFIDENCE``; everything in between is left for a human.
"""

from __future__ import annotations

from lutris_antispam.models import Assessment, RuleHit, Submission, Verdict
from lutris_antispam.rules import ALL_CHECKS

# Score thresholds (0-100).
SPAM_THRESHOLD = 70
UNCERTAIN_THRESHOLD = 35
# At or above this, the website may send the "stupid prizes" email.
MAX_CONFIDENCE = 90


def _verdict_for(score: int) -> Verdict:
    if score >= SPAM_THRESHOLD:
        return Verdict.SPAM
    if score >= UNCERTAIN_THRESHOLD:
        return Verdict.UNCERTAIN
    return Verdict.CLEAN


def assess(submission: Submission | dict) -> Assessment:
    """Score a submission and return an :class:`Assessment`.

    Accepts either a :class:`Submission` or a plain dict (the website passes a
    dict across the package boundary).
    """
    if not isinstance(submission, Submission):
        submission = Submission.from_dict(submission)

    hits = []
    for check in ALL_CHECKS:
        hits.extend(check(submission))

    hits.extend(_synergies(hits))

    score = min(100, sum(hit.weight for hit in hits))
    return Assessment(verdict=_verdict_for(score), score=score, hits=hits)


def _synergies(hits):
    """Bonuses for combinations that are far more damning together than apart."""
    fired = {hit.rule for hit in hits}
    # Coordinated identity: the game name, the account username, and the email
    # localpart are all the same promoted entity — the account exists only to
    # advertise it. Each match is weak alone; together they mean a spam account.
    if {"name.matches_username", "email.localpart_matches_name"} <= fired:
        yield RuleHit("identity.coordinated", 15, "name==username==email")
