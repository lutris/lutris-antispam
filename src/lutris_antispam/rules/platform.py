"""Rules on the declared platform(s).

Spammers submitting browser/casual games pick an obscure retro platform (or
none) to dodge a naive "browser game = spam" filter. A handful of platforms are
near-never legitimately chosen for the kind of games being spammed, so their
presence is a strong red flag. Weighted so it needs one corroborating signal to
reach the ban line — a genuine retro-game entry alone is only flagged.
"""

from __future__ import annotations

from collections.abc import Iterator

from lutris_antispam.models import RuleHit, Submission

# Matched as a case-insensitive substring of the platform name, so "Amstrad"
# covers "Amstrad CPC", "Amstrad CPC 464", etc.
_REDFLAG_PLATFORMS = ("acorn", "amstrad", "3do", "zx spectrum")


def check(sub: Submission) -> Iterator[RuleHit]:
    for platform in sub.platforms:
        low = platform.lower()
        if any(flag in low for flag in _REDFLAG_PLATFORMS):
            yield RuleHit("platform.implausible", 35, platform)
            return
