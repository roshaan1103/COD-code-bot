import asyncio
from datetime import datetime, timezone

import app.message_handler as handler

from app.chat import ChatMessage
from app.deduplicator import CodeDeduplicator
from app.redemption.queue import RedemptionQueue


# ---------------------------------------------------------
# Isolate this test from the application's normal queue.
# No redemption worker will be started.
# ---------------------------------------------------------

handler.redemption_queue = RedemptionQueue()
handler.deduplicator = CodeDeduplicator()


BROADCASTER_ID = "youtube-video:TEST_VIDEO"
BROADCASTER_LOGIN = "youtube:TEST_VIDEO"


def create_message(
    *,
    chatter_id: str,
    chatter_name: str,
    text: str,
    is_moderator: bool = False,
) -> ChatMessage:
    """Create a synthetic YouTube message for testing."""

    return ChatMessage(
        event_id=f"test:{chatter_name}:{text}",
        broadcaster_id=BROADCASTER_ID,
        broadcaster_login=BROADCASTER_LOGIN,
        broadcaster_name="Test YouTube Stream",
        chatter_id=chatter_id,
        chatter_login=chatter_name,
        chatter_name=chatter_name,
        text=text,
        received_at=datetime.now(timezone.utc),
        is_moderator=is_moderator,
    )


async def main():
    queue = handler.redemption_queue

    # -----------------------------------------------------
    # Test 1: An ordinary viewer must not enqueue a code.
    # -----------------------------------------------------

    print("\n--- TEST 1: Unauthorized viewer ---")

    viewer_message = create_message(
        chatter_id="youtube-viewer-123",
        chatter_name="TestViewer",
        text="Steam: TEST-CODE-123",
    )

    await handler.handle_chat_message(viewer_message)

    assert queue.size() == 0, (
        "FAIL: An unauthorized viewer's message was queued."
    )

    print("PASS: Unauthorized viewer was ignored.")

    # -----------------------------------------------------
    # Test 2: An authorized moderator can enqueue a code.
    # -----------------------------------------------------

    print("\n--- TEST 2: Authorized moderator ---")

    moderator_message = create_message(
        chatter_id="youtube-moderator-456",
        chatter_name="TestModerator",
        text="Steam: TEST-CODE-123",
        is_moderator=True,
    )

    await handler.handle_chat_message(moderator_message)

    assert queue.size() == 1, (
        "FAIL: The moderator's code was not queued."
    )

    print("PASS: Moderator's code was queued.")

    # -----------------------------------------------------
    # Test 3: A duplicate code must not be queued twice.
    # -----------------------------------------------------

    print("\n--- TEST 3: Duplicate code ---")

    duplicate_message = create_message(
        chatter_id="youtube-moderator-456",
        chatter_name="TestModerator",
        text="Steam: TEST-CODE-123",
        is_moderator=True,
    )

    await handler.handle_chat_message(duplicate_message)

    assert queue.size() == 1, (
        "FAIL: A duplicate code was queued."
    )

    print("PASS: Duplicate code was rejected.")

    # -----------------------------------------------------
    # Test 4: Inspect the queued job.
    # -----------------------------------------------------

    print("\n--- TEST 4: Queued job contents ---")

    job = await queue.get()

    assert job.platform == "steam", (
        f"Unexpected platform: {job.platform}"
    )

    assert job.code == "TEST-CODE-123", (
        f"Unexpected test code: {job.code}"
    )

    assert job.streamer == BROADCASTER_LOGIN, (
        f"Unexpected streamer: {job.streamer}"
    )

    queue.task_done()

    assert queue.size() == 0, (
        "FAIL: The test queue should now be empty."
    )

    print("PASS: Queued job fields are correct.")
    print("\nALL MESSAGE-HANDLER TESTS PASSED.")


if __name__ == "__main__":
    asyncio.run(main())