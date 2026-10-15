import asyncio

from app.youtube_chat import listen_to_youtube_chat


async def heartbeat():
    """Show that the asyncio event loop remains responsive."""
    for count in range(1, 11):
        print(f"[HEARTBEAT] Event loop responsive: {count}/10")
        await asyncio.sleep(1)


async def main():
    print("[TEST] Starting YouTube listener and heartbeat.")

    youtube_task = asyncio.create_task(
        listen_to_youtube_chat(),
        name="youtube-test-listener",
    )

    heartbeat_task = asyncio.create_task(
        heartbeat(),
        name="heartbeat",
    )

    try:
        await heartbeat_task
    finally:
        print("[TEST] Cancelling YouTube listener.")
        youtube_task.cancel()

        try:
            await asyncio.wait_for(youtube_task, timeout=5)
        except asyncio.CancelledError:
            print("[TEST] YouTube listener cancelled successfully.")
        except asyncio.TimeoutError:
            print(
                "[TEST WARNING] Listener did not stop within "
                "5 seconds."
            )

    print("[TEST] Responsiveness test finished.")


if __name__ == "__main__":
    asyncio.run(main())