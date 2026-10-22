import asyncio
import re
import subprocess
import winsound

import app.irc_chat as twitch_chat
import app.youtube_chat as youtube_chat

from app.auth import load_tokens
from app.twitch_api import get_user_by_login


# ============================================================
# CONFIGURATION
# ============================================================

# Twitch channel logins: no @ symbol or URL.
TWITCH_CHANNELS = [
    "your_first_test_channel",
    # "your_second_test_channel",
]

# Set to False if you want to monitor YouTube only.
ENABLE_TWITCH = True

# Set to False if you want to monitor Twitch only.
ENABLE_YOUTUBE = True

# YouTube livestream video ID.
# This uses the VIDEO_ID already configured in app.youtube_chat.
YOUTUBE_VIDEO_ID = youtube_chat.VIDEO_ID


# ============================================================
# CODE DETECTION
# ============================================================

# Four characters, dash, five characters, dash, four characters.
CODE_PATTERN = re.compile(
    r"(?<![A-Z0-9])"
    r"([A-Z0-9]{4}-[A-Z0-9]{5}-[A-Z0-9]{4})"
    r"(?![A-Z0-9])",
    re.IGNORECASE,
)


# ============================================================
# SHARED STATE
# ============================================================

code_queue = asyncio.Queue()

# Shared across Twitch and YouTube.
seen_codes = set()

# Keep track of the code currently displayed to the user.
current_code = None


# ============================================================
# CLIPBOARD AND ALERT
# ============================================================

def copy_code_to_clipboard(code: str) -> None:
    """
    Copy a code to the Windows clipboard using clip.exe.
    No additional clipboard package is required.
    """
    subprocess.run(
        ["clip.exe"],
        input=code,
        text=True,
        check=True,
        timeout=5,
    )


def play_alert() -> None:
    """Play a Windows system alert sound."""
    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)


# ============================================================
# CHAT MESSAGE HANDLER
# ============================================================

async def handle_cod_message(chat_message) -> None:
    """
    Receive messages forwarded by the existing Twitch/YouTube
    listeners, detect COD codes, and queue new codes.

    The existing listeners' broadcaster/moderator filtering
    must remain in place.
    """
    text = getattr(chat_message, "text", "")

    if not text:
        return

    matches = CODE_PATTERN.findall(text.upper())

    for code in matches:
        if code in seen_codes:
            continue

        seen_codes.add(code)

        print()
        print("[COD] New code detected!")
        print(f"[COD] Channel : "
              f"{getattr(chat_message, 'broadcaster_login', 'YouTube/Twitch')}")
        print(f"[COD] Code    : {code}")

        await code_queue.put(code)


# ============================================================
# CODE QUEUE WORKER
# ============================================================

async def process_codes() -> None:
    """
    Display one code at a time.

    Additional codes wait in the queue until the user presses
    Enter to advance.
    """
    global current_code

    print()
    print("=" * 60)
    print("CALL OF DUTY CODE MONITOR")
    print("=" * 60)
    print("Waiting for an eligible chat message...")
    print("Press Ctrl+C to stop.")
    print("=" * 60)

    while True:
        code = await code_queue.get()

        try:
            current_code = code

            copy_code_to_clipboard(code)
            play_alert()

            print()
            print("!" * 60)
            print("[COD] CODE COPIED TO CLIPBOARD")
            print(f"[COD] {code}")
            print("Paste it into the redemption page manually.")
            print(
                "After handling this code, press Enter to "
                "advance to the next queued code."
            )
            print("!" * 60)

            await asyncio.to_thread(
                input,
                "Press Enter for the next code... ",
            )

        except (OSError, subprocess.SubprocessError) as exc:
            print(f"[COD] Clipboard/alert error: {exc}")

        finally:
            current_code = None
            code_queue.task_done()


# ============================================================
# LISTENER SETUP
# ============================================================

async def run_twitch() -> None:
    """Start a listener for each configured Twitch channel."""
    tokens = load_tokens()

    access_token = tokens["access_token"]

    # The Twitch listener uses the authenticated chat account's
    # username. Support the common token-file field names.
    username = (
        tokens.get("username")
        or tokens.get("login")
        or tokens.get("user_login")
    )

    if not username:
        raise RuntimeError(
            "Could not find the authenticated Twitch username "
            "in load_tokens(). Check app/auth.py and your token file."
        )

    tasks = []

    for channel_login in TWITCH_CHANNELS:
        channel_login = channel_login.strip().lower()

        if not channel_login:
            continue

        broadcaster = get_user_by_login(
            access_token,
            channel_login,
        )

        print(
            f"[COD] Twitch channel configured: "
            f"#{broadcaster['login']}"
        )

        tasks.append(
            asyncio.create_task(
                twitch_chat.listen_to_channel(
                    access_token=access_token,
                    channel_login=channel_login,
                    broadcaster=broadcaster,
                    username=username,
                )
            )
        )

    if not tasks:
        print("[COD] No Twitch channels configured.")
        return

    await asyncio.gather(*tasks)


async def run_youtube() -> None:
    """Start the existing YouTube livestream listener."""
    if not YOUTUBE_VIDEO_ID:
        raise RuntimeError(
            "YOUTUBE_VIDEO_ID is empty. Configure it in "
            "app.youtube_chat or disable YouTube monitoring."
        )

    print(f"[COD] YouTube video ID: {YOUTUBE_VIDEO_ID}")

    await youtube_chat.listen_to_youtube_chat(
        video_id=YOUTUBE_VIDEO_ID
    )


# ============================================================
# MAIN
# ============================================================

async def main() -> None:
    # Redirect the existing listeners' handler references.
    # This affects only this Python process; irc_runner.py
    # remains unchanged when run separately.
    twitch_chat.handle_chat_message = handle_cod_message
    youtube_chat.handle_chat_message = handle_cod_message

    tasks = [
        asyncio.create_task(process_codes())
    ]

    if ENABLE_TWITCH and TWITCH_CHANNELS:
        tasks.append(asyncio.create_task(run_twitch()))

    if ENABLE_YOUTUBE:
        tasks.append(asyncio.create_task(run_youtube()))

    if len(tasks) == 1:
        raise RuntimeError(
            "No chat sources enabled. Configure Twitch or YouTube."
        )

    try:
        await asyncio.gather(*tasks)

    finally:
        for task in tasks:
            task.cancel()

        await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[COD] Monitor stopped.")