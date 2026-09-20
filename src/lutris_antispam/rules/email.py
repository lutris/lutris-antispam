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


# Alias/forwarding services, as opposed to throwaway inboxes: a real person with
# a durable address behind them.
_RELAY_PROVIDERS = frozenset(
    {
        "simplelogin.com",
        "relay.firefox.com",
        "mozmail.com",
        "duck.com",
        "anonaddy.me",
        "anonaddy.com",
        "dralias.com",
        "addy.io",
    }
)


def check(sub: Submission) -> Iterator[RuleHit]:
    local, domain = email_parts(sub.user_email)
    if not domain:
        return

    if domain in _RELAY_PROVIDERS:
        # Forwarding/alias services (Firefox Relay, SimpleLogin, DuckDuckGo...).
        # Privacy-conscious Linux users use these constantly: measured on the real
        # corpus, 8 of 10 SimpleLogin submissions were accepted by a moderator.
        # Noted for the reviewer, never scored like a throwaway inbox.
        yield RuleHit("email.relay_provider", 5, domain)
    elif domain in disposable_domains():
        yield RuleHit("email.disposable_domain", 60, domain)
    elif domain not in _FREE_PROVIDERS and looks_random(domain.split(".")[0]):
        # Random-looking uncommon domain (ozsaip.com, synsky.com, toaik.com…).
        yield RuleHit("email.random_domain", 10, domain)

    if domain in _FREE_PROVIDERS:
        if _DOTTED_ALIAS_RE.match(local):
            yield RuleHit("email.dotted_alias", 5, local)
        elif looks_random(local):
            yield RuleHit("email.random_localpart", 5, local)

    # Localpart echoes the submission name (subwaysurferspc@, sloperider2org@).
    name_token = re.sub(r"[^a-z0-9]", "", sub.name.lower())
    local_token = re.sub(r"[^a-z0-9]", "", local)
    if name_token and len(name_token) >= 5 and name_token in local_token:
        yield RuleHit("email.localpart_matches_name", 35, local)
