from datetime import datetime, timezone

from app.chat import ChatMessage
from app.code_detector import detect_code
from app.deduplicator import CodeDeduplicator
from app.redemption.base import RedemptionJob
from app.redemption.queue import RedemptionQueue


# One deduplicator instance for the lifetime of the application.
#
# This is important:
# We want the cache to persist between incoming messages.
deduplicator = CodeDeduplicator()


# One redemption queue for the lifetime of the application.
redemption_queue = RedemptionQueue()


async def handle_chat_message(
    message: ChatMessage,
) -> None:
    """
    Process one normalized Twitch chat message.

    Only messages sent by the broadcaster are passed
    to the giveaway code detector.

    Newly detected codes are placed into the redemption
    queue without waiting for the redemption operation.
    """

    received_at = message.received_at

    timestamp = received_at.strftime(
        "%H:%M:%S.%f"
    )[:-3]

    print(
        f"[{timestamp}] "
        f"[{message.broadcaster_login}] "
        f"{message.chatter_name}: "
        f"{message.text}"
    )

    # ---------------------------------------------------------
    # Step 1: Ignore messages that were not sent by the streamer
    # ---------------------------------------------------------

    if message.chatter_id != message.broadcaster_id:
        return

    print(
        "[BROADCASTER] "
        "Message was sent by the streamer."
    )

    # ---------------------------------------------------------
    # Step 2: Detect platform + code
    # ---------------------------------------------------------

    detected_code = detect_code(message.text)

    if detected_code is None:
        return

    # ---------------------------------------------------------
    # Step 3: Check whether this code was already detected
    # ---------------------------------------------------------

    if deduplicator.is_duplicate(
        detected_code.code
    ):
        print(
            "[DUPLICATE] "
            f"Code already detected recently: "
            f"{detected_code.code}"
        )
        return

    # ---------------------------------------------------------
    # Step 4: Measure local detection latency
    # ---------------------------------------------------------

    detected_at = datetime.now(timezone.utc)

    detection_latency_ms = (
        detected_at - received_at
    ).total_seconds() * 1000

    # ---------------------------------------------------------
    # Step 5: Create redemption job
    # ---------------------------------------------------------

    job = RedemptionJob(
        platform=detected_code.platform,
        code=detected_code.code,
        streamer=message.broadcaster_login,
    )

    # ---------------------------------------------------------
    # Step 6: Queue redemption job
    # ---------------------------------------------------------

    await redemption_queue.put(job)

    # ---------------------------------------------------------
    # Step 7: Report newly detected code
    # ---------------------------------------------------------

    print()
    print("=" * 60)
    print("GIVEAWAY CODE DETECTED")
    print("=" * 60)
    print(
        f"Platform        : "
        f"{detected_code.platform}"
    )
    print(
        f"Code            : "
        f"{detected_code.code}"
    )
    print(
        f"Streamer        : "
        f"{message.broadcaster_login}"
    )
    print(
        f"Detection time  : "
        f"{detection_latency_ms:.3f} ms"
    )
    print(
        f"Queue size      : "
        f"{redemption_queue.size()}"
    )
    print("=" * 60)
    print()