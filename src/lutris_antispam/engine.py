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


# Rules specific enough to justify the destructive path. Measured against the
# real submission corpus, each of these fires overwhelmingly on submissions no
# moderator ever accepted. Everything else (a website on the submission, a new
# account, an empty library, a random-looking address) describes an ordinary
# first-time submitter just as well as a spammer, so a pile of those can reach
# the score threshold but can never on its own ban anyone.
STRONG_SIGNALS = frozenset(
    {
        "identity.coordinated",
        "name.matches_username",
        "email.localpart_matches_name",
        "account.unconfirmed_with_website",
        "identity.throwaway_promoting_name",
        "identity.backlink_on_retro_platform",
    }
)


def _verdict_for(score: int, fired: set[str]) -> Verdict:
    if score >= SPAM_THRESHOLD and fired & STRONG_SIGNALS:
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
    return Assessment(verdict=_verdict_for(score, {hit.rule for hit in hits}), score=score, hits=hits)


# Name shapes that mean the submission is promoting something.
_PROMOTED_NAME_SIGNALS = frozenset(
    {
        "name.matches_username",
        "email.localpart_matches_name",
        "name.ends_free_or_game",
        "name.spam_keyword",
        "name.marketing_suffix",
        "name.looks_like_domain",
    }
)


def _synergies(hits):
    """Bonuses for combinations that are far more damning together than apart."""
    fired = {hit.rule for hit in hits}
    # Coordinated identity: the game name, the account username, and the email
    # localpart are all the same promoted entity — the account exists only to
    # advertise it. Each match is weak alone; together they mean a spam account.
    if {"name.matches_username", "email.localpart_matches_name"} <= fired:
        yield RuleHit("identity.coordinated", 15, "name==username==email")

    # A domain-shaped name is how real .io games are named, and an obscure retro
    # platform alone is just a retro game. Together they are backlink bait hiding
    # behind a platform nobody checks: the name sells a site the "Amstrad CPC"
    # game could not possibly run on.
    # A throwaway inbox is not enough on its own: 59% of submissions from one were
    # accepted by a moderator. Promoting a spammy *name* from one is a different
    # thing entirely, and only 12% of those were accepted.
    if "email.disposable_domain" in fired and fired & _PROMOTED_NAME_SIGNALS:
        yield RuleHit("identity.throwaway_promoting_name", 15, "throwaway inbox + promoted name")

    if {"name.looks_like_domain", "platform.implausible"} <= fired:
        yield RuleHit("identity.backlink_on_retro_platform", 15, "domain name on retro platform")
