import asyncio
from datetime import datetime, timezone

import pytchat

from app.config import YOUTUBE_VIDEO_ID
from app.chat import ChatMessage
from app.message_handler import handle_chat_message


# YouTube video ID is configured through .env.
VIDEO_ID = YOUTUBE_VIDEO_ID

# Stable identifier for the configured YouTube stream.
YOUTUBE_BROADCASTER_ID = (
    f"youtube-video:{VIDEO_ID}"
    if VIDEO_ID
    else None
)

# Delay between polling attempts when no messages are available.
POLL_INTERVAL_SECONDS = 1


def _get_message_timestamp(item) -> datetime:
    """Convert the message timestamp to a timezone-aware UTC datetime."""

    timestamp_ms = getattr(item, "timestamp", None)

    if timestamp_ms is None:
        return datetime.now(timezone.utc)

    return datetime.fromtimestamp(
        timestamp_ms / 1000,
        tz=timezone.utc,
    )


def _normalize_youtube_message(
    item,
    video_id: str = VIDEO_ID,
) -> ChatMessage | None:
    """
    Convert an authorized YouTube owner/moderator message
    into the application's normalized ChatMessage format.

    Return None for ordinary viewers or messages lacking
    required identity metadata.
    """

    if not video_id:
        return None

    author = item.author

    channel_id = getattr(author, "channelId", "")
    author_name = getattr(
        author,
        "name",
        "Unknown YouTube user",
    )

    is_owner = bool(
        getattr(author, "isChatOwner", False)
    )

    is_moderator = bool(
        getattr(author, "isChatModerator", False)
    )

    # Ordinary viewers must never enter the processing pipeline.
    if not is_owner and not is_moderator:
        return None

    message_id = getattr(item, "id", None)
    message_text = getattr(item, "message", "")

    if not message_id or not channel_id:
        return None

    if not isinstance(message_text, str):
        return None

    broadcaster_id = f"youtube-video:{video_id}"

    return ChatMessage(
        event_id=f"youtube:{message_id}",

        broadcaster_id=broadcaster_id,

        broadcaster_login=f"youtube:{video_id}",
        broadcaster_name=f"YouTube video {video_id}",

        # The existing handler identifies the broadcaster by ID.
        chatter_id=(
            broadcaster_id
            if is_owner
            else channel_id
        ),

        chatter_login=author_name,
        chatter_name=author_name,

        text=message_text,
        received_at=_get_message_timestamp(item),

        is_moderator=is_moderator,
    )


async def listen_to_youtube_chat(
    video_id: str = VIDEO_ID,
) -> None:
    """
    Read YouTube live chat without blocking the event loop
    during synchronous polling operations.
    """

    if not video_id:
        raise RuntimeError(
            "YouTube video ID is not configured. "
            "Set YOUTUBE_VIDEO_ID in .env."
        )

    chat = None

    try:
        print("[YOUTUBE] Connecting to live chat...")

        # pytchat registers signal handlers during initialization,
        # so create the client on the main thread.
        chat = pytchat.create(
            video_id=video_id,
            interruptable=False,
        )

        print("[YOUTUBE] Chat client created.")
        print(f"[YOUTUBE] Video ID: {video_id}")

        while True:
            alive = await asyncio.to_thread(chat.is_alive)

            if not alive:
                print("[YOUTUBE] Chat reader is no longer alive.")
                break

            data = await asyncio.to_thread(chat.get)
            items = data.sync_items()

            for item in items:
                normalized_message = _normalize_youtube_message(
                    item,
                    video_id=video_id,
                )

                if normalized_message is None:
                    continue

                await handle_chat_message(normalized_message)

            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    except asyncio.CancelledError:
        print("[YOUTUBE] Shutdown requested.")
        raise

    except Exception as exc:
        print(
            f"[YOUTUBE ERROR] {type(exc).__name__}: {exc}"
        )
        raise

    finally:
        if chat is not None:
            try:
                await asyncio.to_thread(chat.terminate)
            except Exception as exc:
                print(
                    f"[YOUTUBE] Error while terminating chat client: "
                    f"{type(exc).__name__}: {exc}"
                )

        print("[YOUTUBE] Chat listener stopped.")