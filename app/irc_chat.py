import asyncio
import ssl
from datetime import datetime, timezone

import websockets

from app.chat import ChatMessage
from app.message_handler import handle_chat_message


IRC_URL = "wss://irc-ws.chat.twitch.tv:443"

# Twitch IRC tags and commands needed for role-aware chat processing.
CAPABILITIES = (
    "CAP REQ :twitch.tv/tags twitch.tv/commands"
)


def parse_irc_message(raw_message: str) -> dict:
    """Parse an IRC message into tags, prefix, command, and text."""

    tags = {}
    prefix = ""
    trailing = ""

    remaining = raw_message

    if remaining.startswith("@"):
        tag_section, remaining = remaining.split(" ", 1)

        for item in tag_section[1:].split(";"):
            if "=" in item:
                key, value = item.split("=", 1)
                tags[key] = value
            else:
                tags[item] = ""

    if remaining.startswith(":"):
        prefix, remaining = remaining[1:].split(" ", 1)

    if " :" in remaining:
        remaining, trailing = remaining.split(" :", 1)

    parts = remaining.split()
    command = parts[0] if parts else ""

    return {
        "tags": tags,
        "prefix": prefix,
        "command": command,
        "text": trailing,
    }


def build_chat_message(
    parsed: dict,
    broadcaster: dict,
) -> ChatMessage:
    """Convert a parsed Twitch IRC message to ChatMessage."""

    tags = parsed["tags"]

    sender_login = parsed["prefix"].split("!", 1)[0]

    badges = {
        badge
        for badge in tags.get("badges", "").split(",")
        if badge
    }

    sender_id = tags.get("user-id", "")

    # The broadcaster ID is authoritative when supplied by Twitch.
    is_broadcaster = (
        sender_id == str(broadcaster["id"])
        or "broadcaster/1" in badges
    )

    is_moderator = (
        tags.get("mod", "0") == "1"
        or "moderator/1" in badges
    )

    # Fail closed if IRC role metadata is incomplete.
    # Do not trust a missing user ID or a broadcaster badge alone
    # to turn an unidentified sender into an authorized moderator.
    if not sender_id:
        is_moderator = False

    return ChatMessage(
        event_id=tags.get("id", ""),
        broadcaster_id=str(broadcaster["id"]),
        broadcaster_login=broadcaster["login"],
        broadcaster_name=broadcaster["display_name"],
        chatter_id=sender_id,
        chatter_login=sender_login,
        chatter_name=tags.get("display-name", sender_login),
        text=parsed["text"],
        received_at=datetime.now(timezone.utc),
        is_moderator=is_moderator,
    )


async def listen_to_channel(
    access_token: str,
    channel_login: str,
    broadcaster: dict,
    username: str,
) -> None:
    """
    Read chat from one Twitch channel and pass messages
    through the existing handler.

    This function does not implement redemption itself.
    """

    channel_login = channel_login.lower().lstrip("@")

    print(f"[IRC] Connecting to #{channel_login}...")

    ssl_context = ssl.create_default_context()

    async with websockets.connect(
        IRC_URL,
        ssl=ssl_context,
        open_timeout=20,
        close_timeout=5,
        ping_interval=30,
        ping_timeout=20,
    ) as websocket:

        await websocket.send(f"PASS oauth:{access_token}")
        await websocket.send(f"NICK {username.lower()}")
        await websocket.send(CAPABILITIES)

        print(f"[IRC] Authentication request sent for #{channel_login}.")

        # Wait for Twitch to accept authentication before joining.
        authenticated = False

        async for raw_message in websocket:
            for line in raw_message.split("\r\n"):
                if not line:
                    continue

                if line.startswith("PING"):
                    await websocket.send("PONG :tmi.twitch.tv")
                    continue

                parsed = parse_irc_message(line)
                command = parsed["command"]

                if command == "001":
                    authenticated = True
                    await websocket.send(f"JOIN #{channel_login}")
                    print(f"[IRC] Authentication successful.")
                    print(f"[IRC] Joined #{channel_login}.")

                elif command == "NOTICE":
                    print(
                        f"[IRC NOTICE] "
                        f"#{channel_login}: {parsed['text']}"
                    )

                elif command == "PRIVMSG" and authenticated:
                    chat_message = build_chat_message(
                        parsed,
                        broadcaster,
                    )

                    # Ignore messages without an identifiable sender ID.
                    if not chat_message.chatter_id:
                        print(
                            "[IRC] Ignoring message with missing "
                            "sender ID."
                        )
                        continue

                    role = (
                        "BROADCASTER"
                        if chat_message.chatter_id
                        == chat_message.broadcaster_id
                        else "MODERATOR"
                        if chat_message.is_moderator
                        else "VIEWER"
                    )

                    print(
                        f"[IRC CHAT] #{channel_login} "
                        f"| {role} "
                        f"| {chat_message.chatter_login}: "
                        "[Message content omitted]"
                    )

                    await handle_chat_message(chat_message)

