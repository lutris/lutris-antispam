"""Tests for the scoring engine, using synthetic cases patterned on real spam."""

from lutris_antispam import MAX_CONFIDENCE, Verdict, assess


def test_disposable_domain_plus_keyword_is_spam_and_taunt_eligible():
    result = assess({"name": "Monkey Mart free", "user_email": "distant.pony@grr.la"})
    assert result.verdict is Verdict.SPAM
    assert result.score >= MAX_CONFIDENCE
    assert "email.disposable_domain" in result.matched_rules


def test_bare_domain_name_is_only_uncertain():
    # A domain-shaped name alone must NOT auto-ban: real games are named this
    # way (Agar.io, Diep.io, Krunker.io). It's flagged for a human instead.
    result = assess({"name": "Agar.io", "user_email": "player@gmail.com"})
    assert result.verdict is Verdict.UNCERTAIN
    assert "name.looks_like_domain" in result.matched_rules


def test_domain_name_with_spam_account_is_spam():
    # Domain-shaped name PLUS an unconfirmed account carrying a promo website
    # is the real backlink-spam shape and does reach the ban path.
    result = assess(
        {
            "name": "Summertimesaga.co.in",
            "user_email": "areebaz362@gmail.com",
            "email_confirmed": False,
            "profile_website": "https://summertimesaga.co.in",
        }
    )
    assert result.verdict is Verdict.SPAM
    assert "name.looks_like_domain" in result.matched_rules


def test_unconfirmed_account_with_website_and_keyword_is_spam():
    result = assess(
        {
            "name": "Slope Online",
            "user_email": "someone@gmail.com",
            "email_confirmed": False,
            "profile_website": "https://buy-cheap-stuff.example",
        }
    )
    assert result.verdict is Verdict.SPAM
    assert "account.unconfirmed_with_website" in result.matched_rules


def test_io_game_with_link_is_not_autobanned():
    # Veck.io-style: a domain-shaped .io name with a link in the description but
    # no disposable/actor signal must be flagged for review, never auto-banned.
    result = assess(
        {
            "name": "Veck.io",
            "user_email": "williamcorlin@gmail.com",
            "description": "A fun little browser game. Play it at https://veck.io",
        }
    )
    assert result.verdict is Verdict.UNCERTAIN
    assert result.score < 70


def test_domain_name_matching_email_localpart_is_spam():
    # Backlink spam where the email localpart IS the promoted domain stays on the
    # ban path even without a disposable address.
    result = assess(
        {
            "name": "SoundBoardW.net",
            "user_email": "soundboardw.net@gmail.com",
            "description": "Check it out at https://soundboardw.net",
        }
    )
    assert result.verdict is Verdict.SPAM
    assert "email.localpart_matches_name" in result.matched_rules


def test_coordinated_identity_is_spam():
    # name == username == email localpart -> account exists only to promote it.
    result = assess(
        {
            "name": "Maharana Cab",
            "username": "maharanacab",
            "user_email": "maharanacabs321@gmail.com",
        }
    )
    assert result.verdict is Verdict.SPAM
    assert "identity.coordinated" in result.matched_rules


def test_dotted_gmail_alias_alone_is_clean():
    # Many legitimate users use first.last.xx@gmail.com; a dotted alias with no
    # other signal stays below the review threshold so mods aren't buried.
    result = assess({"name": "Jojo no Kimyo na Boken", "user_email": "valent.pony.zgct@gmail.com"})
    assert result.verdict is Verdict.CLEAN
    assert result.score < 35


def test_name_ending_in_game_is_strong_flag():
    result = assess({"name": "Meowdoku Game", "user_email": "someone@gmail.com"})
    # 45 alone stays under the ban line -> flagged for review, not auto-banned.
    assert result.verdict is Verdict.UNCERTAIN
    assert "name.ends_free_or_game" in result.matched_rules


def test_name_ending_free_plus_disposable_is_spam():
    result = assess({"name": "Cookie Clicker Free", "user_email": "x@hidingmail.net"})
    assert result.verdict is Verdict.SPAM
    assert "name.ends_free_or_game" in result.matched_rules


def test_name_matches_username_is_spam_with_suffix():
    # Account named after the promoted game + a "... Game" ending -> ban path.
    result = assess(
        {"name": "Slope Rider Game", "username": "sloperider", "user_email": "a@gmail.com"}
    )
    assert result.verdict is Verdict.SPAM
    assert "name.matches_username" in result.matched_rules


def test_name_matches_username_by_prefix():
    result = assess(
        {"name": "Crossy Road Game", "username": "crossyroad1", "user_email": "a@gmail.com"}
    )
    assert "name.matches_username" in result.matched_rules


def test_unrelated_username_does_not_match():
    result = assess(
        {"name": "The Witcher 3", "username": "geralt_fan_88", "user_email": "a@gmail.com"}
    )
    assert "name.matches_username" not in result.matched_rules


def test_name_ending_in_games_plural_is_flagged():
    result = assess({"name": "Sprunki Games", "user_email": "a@gmail.com"})
    assert "name.ends_free_or_game" in result.matched_rules


def test_retro_platform_is_a_red_flag():
    # Obscure retro platform alone -> flagged for review, not auto-banned.
    result = assess(
        {"name": "Some Retro Title", "user_email": "a@gmail.com", "platforms": ["Amstrad CPC 464"]}
    )
    assert "platform.implausible" in result.matched_rules
    assert result.verdict is Verdict.UNCERTAIN


def test_io_game_on_retro_platform_is_spam():
    # The platform red flag disambiguates a real .io game (Web/none) from spam
    # claiming an implausible platform.
    result = assess(
        {
            "name": "Veck.io",
            "user_email": "williamcorlin@gmail.com",
            "description": "Play at https://veck.io",
            "platforms": ["Amstrad CPC 464"],
        }
    )
    assert result.verdict is Verdict.SPAM
    assert "platform.implausible" in result.matched_rules


def test_normal_platform_is_not_flagged():
    result = assess(
        {"name": "Half-Life 2", "user_email": "a@gmail.com", "platforms": ["Linux", "Windows"]}
    )
    assert "platform.implausible" not in result.matched_rules


def test_legit_submission_is_clean():
    result = assess(
        {
            "name": "The Witcher 3: Wild Hunt",
            "user_email": "jane.doe@gmail.com",
            "email_confirmed": True,
            "library_game_count": 143,
            "account_age_days": 900,
        }
    )
    assert result.verdict is Verdict.CLEAN
    assert result.score == 0


def test_from_dict_ignores_unknown_and_null_fields():
    result = assess({"name": None, "website": None, "user_email": None, "bogus": 1})
    assert result.verdict is Verdict.CLEAN


def test_promo_language_in_description():
    result = assess(
        {
            "name": "Adventure Quest",
            "user_email": "user@gmail.com",
            "description": "Best casino bonus, click here to visit our site!",
        }
    )
    assert "content.promo_language" in result.matched_rules
    assert "content.contains_url" not in result.matched_rules  # no actual URL


def test_as_dict_shape():
    payload = assess({"name": "test free", "user_email": "x@grr.la"}).as_dict()
    assert set(payload) == {"verdict", "score", "matched_rules"}
    assert isinstance(payload["matched_rules"], list)


def test_known_spam_domain_reaches_the_ban_path():
    # The website has already banned a submission pushing this domain, which is
    # a moderator's decision rather than a guess about the text.
    result = assess(
        {
            "name": "Some Puzzle Adventure",
            "user_email": "player@gmail.com",
            "website": "https://slope-rider.io",
            "website_seen_in_spam": True,
            "account_age_days": 0.1,
            "library_game_count": 0,
        }
    )
    assert result.verdict is Verdict.SPAM
    assert "history.known_spam_domain" in result.matched_rules


def test_unseen_domain_does_not_fire_the_history_rule():
    result = assess(
        {
            "name": "Some Puzzle Adventure",
            "user_email": "player@gmail.com",
            "website": "https://some-puzzle-game.example",
        }
    )
    assert "history.known_spam_domain" not in result.matched_rules
    assert result.verdict is Verdict.CLEAN
