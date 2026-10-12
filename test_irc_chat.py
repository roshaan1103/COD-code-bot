from app.irc_chat import parse_irc_message, build_chat_message


BROADCASTER = {
    "id": "1547458395",
    "login": "whyisitmealways1",
    "display_name": "whyisitmealways1",
}


def test_parse_irc_message():
    raw = (
        "@badge-info=;badges=moderator/1;client-nonce=abc123;"
        "color=;display-name=willycantplay;emotes=;"
        "first-msg=0;flags=;id=message123;mod=1;room-id=1547458395;"
        "subscriber=0;tmi-sent-ts=1720000000000;user-id=815998094;"
        "user-type=mod :willycantplay!willycantplay@willycantplay.tmi.twitch.tv "
        "PRIVMSG #whyisitmealways1 :Hello from a moderator"
    )

    parsed = parse_irc_message(raw)

    assert parsed["command"] == "PRIVMSG"
    assert parsed["text"] == "Hello from a moderator"
    assert parsed["tags"]["user-id"] == "815998094"
    assert parsed["tags"]["mod"] == "1"

    print("[PASS] IRC message parsing")


def test_moderator_message():
    parsed = parse_irc_message(
        "@badges=moderator/1;display-name=willycantplay;"
        "id=message123;mod=1;user-id=815998094 "
        ":willycantplay!willycantplay@willycantplay.tmi.twitch.tv "
        "PRIVMSG #whyisitmealways1 :Hello"
    )

    message = build_chat_message(parsed, BROADCASTER)

    assert message.is_moderator is True
    assert message.chatter_id == "815998094"
    assert message.broadcaster_id == "1547458395"

    print("[PASS] Moderator identification")


def test_broadcaster_message():
    parsed = parse_irc_message(
        "@badges=broadcaster/1;display-name=whyisitmealways1;"
        "id=message456;mod=0;user-id=1547458395 "
        ":whyisitmealways1!whyisitmealways1@whyisitmealways1.tmi.twitch.tv "
        "PRIVMSG #whyisitmealways1 :Hello"
    )

    message = build_chat_message(parsed, BROADCASTER)

    assert message.chatter_id == message.broadcaster_id
    assert message.is_moderator is False

    print("[PASS] Broadcaster identification")


def test_viewer_message():
    parsed = parse_irc_message(
        "@badges=;display-name=willycantplay;"
        "id=message789;mod=0;user-id=815998094 "
        ":willycantplay!willycantplay@willycantplay.tmi.twitch.tv "
        "PRIVMSG #whyisitmealways1 :Hello"
    )

    message = build_chat_message(parsed, BROADCASTER)

    assert message.is_moderator is False
    assert message.chatter_id != message.broadcaster_id

    print("[PASS] Ordinary viewer remains unauthorized")


if __name__ == "__main__":
    test_parse_irc_message()
    test_moderator_message()
    test_broadcaster_message()
    test_viewer_message()

    print("\nAll IRC adapter tests passed.")

