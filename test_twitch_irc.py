import asyncio
import json
import os
import ssl

import websockets

from app.config import TWITCH_CLIENT_ID


IRC_URL = "wss://irc-ws.chat.twitch.tv:443"
CHANNEL = "whyisitmealways1"


def load_access_token() -> str:
    """Load the existing Twitch access token without printing it."""
    token_file = "twitch_tokens.json"

    if not os.path.exists(token_file):
        raise FileNotFoundError(
            f"{token_file} was not found in the project root."
        )

    with open(token_file, "r", encoding="utf-8") as file:
        tokens = json.load(file)

    access_token = tokens.get("access_token")

    if not access_token:
        raise RuntimeError(
            "No access_token was found in twitch_tokens.json."
        )

    return access_token.removeprefix("oauth:")


def parse_irc_message(raw_message: str) -> dict:
    """Extract tags, sender, command, and message text from an IRC line."""
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


async def main():
    access_token = load_access_token()

    if not TWITCH_CLIENT_ID:
        raise RuntimeError(
            "TWITCH_CLIENT_ID is missing from your application configuration."
        )

    print("=" * 60)
    print("Twitch IRC Connectivity Test")
    print("=" * 60)
    print(f"Channel: #{CHANNEL}")
    print("Connecting to Twitch IRC...")
    print("No codes will be queued or redeemed.")
    print("Press Ctrl+C to stop.")
    print()

    ssl_context = ssl.create_default_context()

    async with websockets.connect(
        IRC_URL,
        ssl=ssl_context,
        open_timeout=20,
        close_timeout=5,
        ping_interval=30,
        ping_timeout=20,
    ) as websocket:

        # Authenticate with the existing OAuth access token.
        await websocket.send("PASS oauth:" + access_token)
        await websocket.send("NICK dominent_orion")

        # Request role and message metadata.
        await websocket.send("CAP REQ :twitch.tv/tags twitch.tv/commands")

        # Join the selected public channel.
        await websocket.send(f"JOIN #{CHANNEL}")

        print("Connected. Waiting for Twitch responses...")
        print()

        async for raw_message in websocket:
            for line in raw_message.split("\r\n"):
                if not line:
                    continue

                if line.startswith("PING"):
                    await websocket.send("PONG :tmi.twitch.tv")
                    print("[KEEPALIVE] Responded to Twitch ping.")
                    continue

                parsed = parse_irc_message(line)
                command = parsed["command"]
                tags = parsed["tags"]

                if command == "001":
                    print("[SUCCESS] Twitch IRC authentication accepted.")

                elif command == "CAP":
                    print("[CAPABILITIES] Twitch responded to metadata request.")

                elif command == "JOIN":
                    print(f"[SUCCESS] Joined #{CHANNEL}.")

                elif command == "NOTICE":
                    # Display Twitch's diagnostic message without credentials.
                    print(f"[NOTICE] {parsed['text']}")

                elif command == "PRIVMSG":
                    sender = parsed["prefix"].split("!", 1)[0]
                    badges = tags.get("badges", "")
                    moderator_flag = tags.get("mod", "0")

                    is_broadcaster = "broadcaster/1" in badges.split(",")
                    is_moderator = (
                        moderator_flag == "1"
                        or "moderator/1" in badges.split(",")
                    )

                    if is_broadcaster:
                        role = "BROADCASTER"
                    elif is_moderator:
                        role = "MODERATOR"
                    else:
                        role = "VIEWER/UNKNOWN"

                    # Show chat text and role metadata only.
                    print(f"[CHAT] {role} | {sender}: {parsed['text']}")
                    print(
                        f"       user-id={tags.get('user-id', 'unavailable')} "
                        f"| mod={moderator_flag} "
                        f"| badges={badges or 'none'}"
                    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nIRC test stopped.")
    except Exception as exc:
        print(f"\nIRC test failed: {type(exc).__name__}: {exc}")