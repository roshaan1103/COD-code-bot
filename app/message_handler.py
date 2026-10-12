from datetime import datetime, timezone

from app.chat import ChatMessage
from app.code_detector import detect_codes
from app.deduplicator import CodeDeduplicator
from app.redemption.base import RedemptionJob
from app.redemption.queue import RedemptionQueue


# One deduplicator instance for the lifetime of the application.
# Its cache persists between incoming messages.
deduplicator = CodeDeduplicator()


# One redemption queue for the lifetime of the application.
redemption_queue = RedemptionQueue()


async def handle_chat_message(
    message: ChatMessage,
) -> None:
    """
    Process one normalized Twitch chat message.

    Only messages from the broadcaster or an authorized
    moderator are considered for giveaway code detection.

    Each newly detected platform/code pair is independently
    checked for duplicates and placed into the redemption queue.
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
    # Step 1: Authorize the broadcaster or a moderator
    # ---------------------------------------------------------

    is_broadcaster = (
        message.chatter_id == message.broadcaster_id
    )

    if not is_broadcaster and not message.is_moderator:
        print(
            "[IGNORED] "
            "Message sender is neither the broadcaster "
            "nor an authorized moderator."
        )
        return

    if is_broadcaster:
        print(
            "[BROADCASTER] "
            "Message was sent by the streamer."
        )
    else:
        print(
            "[MODERATOR] "
            "Message was sent by a moderator."
        )

    # ---------------------------------------------------------
    # Step 2: Detect all platform/code pairs in the message
    # ---------------------------------------------------------

    detected_codes = detect_codes(message.text)

    if not detected_codes:
        return

    # ---------------------------------------------------------
    # Step 3: Process each detected code independently
    # ---------------------------------------------------------

    for detected_code in detected_codes:

        # -----------------------------------------------------
        # Step 3a: Check for duplicates
        # -----------------------------------------------------

        if deduplicator.is_duplicate(detected_code.code):
            print(
                "[DUPLICATE] "
                f"Code already detected recently: "
                f"{detected_code.code}"
            )
            continue

        # -----------------------------------------------------
        # Step 3b: Measure detection latency
        # -----------------------------------------------------

        detected_at = datetime.now(timezone.utc)

        detection_latency_ms = (
            detected_at - received_at
        ).total_seconds() * 1000

        # -----------------------------------------------------
        # Step 3c: Create the redemption job
        # -----------------------------------------------------

        job = RedemptionJob(
            platform=detected_code.platform,
            code=detected_code.code,
            streamer=message.broadcaster_login,
        )

        # -----------------------------------------------------
        # Step 3d: Add the job to the queue
        # -----------------------------------------------------

        await redemption_queue.put(job)

        # -----------------------------------------------------
        # Step 3e: Report the detected code
        # -----------------------------------------------------

        print()
        print("=" * 60)
        print("GIVEAWAY CODE DETECTED")
        print("=" * 60)
        print(f"Platform        : {detected_code.platform}")
        print(f"Code            : {detected_code.code}")
        print(f"Streamer        : {message.broadcaster_login}")
        print(f"Detection time  : {detection_latency_ms:.3f} ms")
        print(f"Queue size      : {redemption_queue.size()}")
        print("=" * 60)
        print()