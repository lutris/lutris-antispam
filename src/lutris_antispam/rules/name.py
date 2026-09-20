"""Rules on the submitted game name."""

from __future__ import annotations

import re
from collections.abc import Iterator

from lutris_antispam._util import DOMAIN_RE, URL_RE
from lutris_antispam.models import RuleHit, Submission

# Keywords that are strongly over-represented in SEO/backlink spam names.
# Matched as whole words (case-insensitive).
_SPAM_KEYWORDS = frozenset(
    {
        "free",
        "online",
        "unblocked",
        "apk",
        "mod",
        "modded",
        "crack",
        "cracked",
        "hack",
        "hacked",
        "cheats",
        "download",
        "unlimited",
        "generator",
        "redeem",
        "coupon",
        "promo",
    }
)

# A name ending in "free", "game" or "games" is a huge red flag ("Cookie Clicker
# Free", "Meowdoku Game", "Sprunki Games"). Weighted just under the ban line so it
# needs one more signal to auto-ban, keeping a rare legit "... Game" title in the
# review queue instead.
_STRONG_SUFFIX_RE = re.compile(r"\b(free|games?)\s*$", re.IGNORECASE)

# Weaker trailing marketing filler ("... Online/Unblocked/PC/IO/GG").
_SUFFIX_RE = re.compile(r"\b(online|unblocked|pc|io|gg)\s*$", re.IGNORECASE)


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _name_matches_username(name: str, username: str) -> bool:
    """True when the game name and the account name are ~the same thing.

    Spammers routinely register an account named after the site/game they are
    promoting (soundboardwnet -> "SoundBoardW.net", crossyroad1 -> "Crossy Road
    Game"). Matches on containment or a substantial shared prefix.
    """
    name_token = _normalize(name)
    user_token = _normalize(username)
    if len(name_token) < 4 or len(user_token) < 4:
        return False
    if name_token in user_token or user_token in name_token:
        return True
    prefix = 0
    for a, b in zip(name_token, user_token):
        if a != b:
            break
        prefix += 1
    return prefix >= 6 and prefix >= min(len(name_token), len(user_token)) // 2


def _name_matches_site(low_name: str, profile_website: str) -> bool:
    """True when the submitted name is what the profile website is named after."""
    if not profile_website:
        return False
    host = re.sub(r"^\w+://", "", profile_website.strip().lower()).split("/")[0]
    host = host.removeprefix("www.")
    host_token = re.sub(r"[^a-z0-9]", "", host.split(".")[0])
    name_token = re.sub(r"[^a-z0-9]", "", low_name)
    if len(name_token) < 5 or len(host_token) < 5:
        return False
    return name_token in host_token or host_token in name_token


def check(sub: Submission) -> Iterator[RuleHit]:
    name = sub.name.strip()
    if not name:
        return
    low = name.lower()
    is_domain = bool(URL_RE.search(name) or DOMAIN_RE.search(low))

    strong = _STRONG_SUFFIX_RE.search(low) if not is_domain else None
    if strong:
        yield RuleHit("name.ends_free_or_game", 35, strong.group(1))

    words = set(re.findall(r"[a-z]+", low))
    if strong:
        # Don't also count the trailing word under the generic keyword rule.
        words.discard(strong.group(1))
    matched = sorted(words & _SPAM_KEYWORDS)
    if matched:
        # Cap so a keyword-stuffed name doesn't overflow on this rule alone.
        yield RuleHit("name.spam_keyword", min(25, 20 * len(matched)), ",".join(matched))

    if is_domain:
        # The name is (or contains) a domain / URL — pure backlink bait. Skips the
        # suffix rules so a ".io"/".gg" TLD isn't scored twice: real games are named
        # that way (Agar.io) and must not be auto-banned on shape alone.
        yield RuleHit("name.looks_like_domain", 35, name[:60])
    elif not strong:
        suffix = _SUFFIX_RE.search(name)
        if suffix:
            yield RuleHit("name.marketing_suffix", 20, suffix.group(0).strip())

    if _name_matches_username(name, sub.username):
        yield RuleHit("name.matches_username", 45, sub.username[:40])

    if _name_matches_site(low, sub.profile_website):
        # Tempting as a spam signal, but on the real corpus every hit was an indie
        # developer whose profile site *is* the game they submitted (Valyria Tear,
        # Coreball). Kept only as a hint for the reviewer.
        yield RuleHit("identity.name_matches_profile_site", 10, sub.profile_website[:80])
