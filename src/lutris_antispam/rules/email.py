"""Email-based rules — the strongest spam signals in the observed corpus."""

from __future__ import annotations

import re
from collections.abc import Iterator

from lutris_antispam._util import disposable_domains, email_parts, looks_random
from lutris_antispam.models import RuleHit, Submission

# Free providers where the domain itself carries no signal; we look at the
# localpart shape instead.
_FREE_PROVIDERS = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "outlook.com",
        "hotmail.com",
        "live.com",
        "yahoo.com",
        "proton.me",
        "protonmail.com",
        "icloud.com",
    }
)

# "word.word.randsuffix" — the Gmail dot-alias pattern seen repeatedly, e.g.
# distant.pony.zgct@, metropolitan.fish.kkhl@, conceptual.dinosaur.aisi@.
_DOTTED_ALIAS_RE = re.compile(r"^[a-z]{3,}\.[a-z]{3,}\.[a-z0-9]{3,6}$")


def check(sub: Submission) -> Iterator[RuleHit]:
    local, domain = email_parts(sub.user_email)
    if not domain:
        return

    if domain in disposable_domains():
        yield RuleHit("email.disposable_domain", 60, domain)
    elif domain not in _FREE_PROVIDERS and looks_random(domain.split(".")[0]):
        # Random-looking uncommon domain (ozsaip.com, synsky.com, toaik.com…).
        yield RuleHit("email.random_domain", 25, domain)

    if domain in _FREE_PROVIDERS:
        if _DOTTED_ALIAS_RE.match(local):
            yield RuleHit("email.dotted_alias", 25, local)
        elif looks_random(local):
            yield RuleHit("email.random_localpart", 15, local)

    # Localpart echoes the submission name (subwaysurferspc@, sloperider2org@).
    name_token = re.sub(r"[^a-z0-9]", "", sub.name.lower())
    local_token = re.sub(r"[^a-z0-9]", "", local)
    if name_token and len(name_token) >= 5 and name_token in local_token:
        yield RuleHit("email.localpart_matches_name", 20, local)
