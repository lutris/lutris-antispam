"""Rules on what moderators have already seen.

The website records the domain of every submission a moderator banned, and tells
us whether this submission's website is one of them. That makes it the only
signal here grounded in a human decision rather than in the shape of the text,
which is why it is trusted enough to reach the ban path.

The website only ever records domains from confirmed bans, never from this
package's own verdicts: a rule that learned from its own output would simply
agree with itself, and one bad ban would compound.
"""

from __future__ import annotations

from collections.abc import Iterator

from lutris_antispam.models import RuleHit, Submission


def check(sub: Submission) -> Iterator[RuleHit]:
    if sub.website_seen_in_spam:
        # Deliberately short of the ban threshold on its own: it takes any other
        # signal to push a resubmission of a banned domain over the line, so a
        # single mistaken ban can't turn into an automatic one next time.
        yield RuleHit("history.known_spam_domain", 55, "domain seen in banned submissions")
