import asyncio
from datetime import datetime, timezone

from app.chat import ChatMessage
from app.message_handler import (
    handle_chat_message,
    redemption_queue,
)
from app.redemption.fake_adapters import (
    FakeSteamAdapter,
    FakeBattleNetAdapter,
)
from app.redemption.worker import RedemptionWorker


def create_message(
    text: str,
    chatter_id: str = "123",
    broadcaster_id: str = "123",
) -> ChatMessage:

    return ChatMessage(
        event_id="test-event",
        broadcaster_id=broadcaster_id,
        broadcaster_login="teststreamer",
        broadcaster_name="Test Streamer",
        chatter_id=chatter_id,
        chatter_login="teststreamer",
        chatter_name="Test Streamer",
        text=text,
        received_at=datetime.now(timezone.utc),
    )


async def main():

    print()
    print("=" * 60)
    print("HANDLER + REDEMPTION WORKER INTEGRATION TEST")
    print("=" * 60)

    # ---------------------------------------------------------
    # Create worker
    # ---------------------------------------------------------

    worker = RedemptionWorker(
        queue=redemption_queue,
        adapters={
            "steam": FakeSteamAdapter(),
            "battle.net": FakeBattleNetAdapter(),
        },
    )

    worker_task = asyncio.create_task(
        worker.run()
    )

    # ---------------------------------------------------------
    # Send Steam code
    # ---------------------------------------------------------

    print()
    print("TEST 1: Steam code")
    print("-" * 60)

    await handle_chat_message(
        create_message(
            "Steam:ABCD-EFGH-IJKL-MNOP"
        )
    )

    # ---------------------------------------------------------
    # Send Battle.net code
    # ---------------------------------------------------------

    print()
    print("TEST 2: Battle.net code")
    print("-" * 60)

    await handle_chat_message(
        create_message(
            "Battle.net:QRST-UVWX-YZ12-3456"
        )
    )

    # ---------------------------------------------------------
    # Wait until both jobs are processed
    # ---------------------------------------------------------

    await redemption_queue._queue.join()

    print()
    print("=" * 60)
    print("ALL JOBS PROCESSED")
    print("=" * 60)

    # ---------------------------------------------------------
    # Stop worker
    # ---------------------------------------------------------

    worker_task.cancel()

    try:
        await worker_task
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    asyncio.run(main())