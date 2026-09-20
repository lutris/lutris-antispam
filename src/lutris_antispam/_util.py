"""Shared helpers for rule modules."""

from __future__ import annotations

import math
import re
from functools import lru_cache
from importlib import resources

# A loose pattern that matches "looks like a domain / TLD in the text", e.g.
# "summertimesaga.co.in", "build now .gg", "site.io". We keep the TLD set small
# and spam-relevant to avoid matching ordinary words with dots.
_TLD = (
    r"com|net|org|io|gg|co|in|ru|xyz|info|biz|app|online|site|shop|club|vip|top|"
    r"live|store|fun|link|click|me|us|uk"
)
DOMAIN_RE = re.compile(rf"\b[a-z0-9-]+\.(?:{_TLD})\b(?:\.[a-z]{{2}})?", re.IGNORECASE)
URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)


@lru_cache(maxsize=1)
def disposable_domains() -> frozenset[str]:
    """Load the bundled disposable-domain blocklist."""
    text = (
        resources.files("lutris_antispam.data")
        .joinpath("disposable_domains.txt")
        .read_text(encoding="utf-8")
    )
    domains = set()
    for raw in text.splitlines():
        line = raw.strip().lower()
        if line and not line.startswith("#"):
            domains.add(line)
    return frozenset(domains)


@lru_cache(maxsize=1)
def shared_hosting_domains() -> frozenset[str]:
    """Load the bundled list of hosts anyone can publish a page on."""
    text = (
        resources.files("lutris_antispam.data")
        .joinpath("shared_hosting_domains.txt")
        .read_text(encoding="utf-8")
    )
    domains = set()
    for raw in text.splitlines():
        line = raw.strip().lower()
        if line and not line.startswith("#"):
            domains.add(line)
    return frozenset(domains)


def is_shared_host(domain: str) -> bool:
    """Whether a domain is a host anyone can publish a page on.

    The website calls this before recording a domain as spam, so that banning a
    spammer who used a shared host cannot taint everyone else hosted there.
    """
    domain = (domain or "").strip().lower().removeprefix("www.")
    if not domain:
        return False
    hosts = shared_hosting_domains()
    if domain in hosts:
        return True
    # Catches user.itch.io without matching notitch.io
    return any(domain.endswith("." + host) for host in hosts)


def email_parts(address: str) -> tuple[str, str]:
    """Return ``(localpart, domain)`` lowercased, or ``("", "")`` if invalid."""
    address = (address or "").strip().lower()
    if address.count("@") != 1:
        return "", ""
    local, domain = address.split("@")
    return local, domain


def shannon_entropy(text: str) -> float:
    """Bits-per-character entropy; higher means more random-looking."""
    if not text:
        return 0.0
    counts: dict[str, int] = {}
    for ch in text:
        counts[ch] = counts.get(ch, 0) + 1
    length = len(text)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())


def looks_random(token: str) -> bool:
    """Heuristic for a random-looking alphanumeric token (domain label or
    email suffix): reasonably long, high entropy, and lacking vowels or full
    of digit/consonant runs."""
    token = re.sub(r"[^a-z0-9]", "", token.lower())
    if len(token) < 5:
        return False
    vowels = sum(token.count(v) for v in "aeiou")
    vowel_ratio = vowels / len(token)
    return shannon_entropy(token) >= 3.0 and vowel_ratio < 0.30
