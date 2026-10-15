import asyncio
import json
from collections import deque
from datetime import datetime, timezone
import httpx
import websockets

from app.auth import load_tokens
from app.chat import ChatMessage
from app.config import TWITCH_CLIENT_ID
from app.message_handler import (
    handle_chat_message,
    redemption_queue,
)
from app.browser.manager import BrowserManager
from app.redemption.battlenet import BattleNetAdapter
from app.redemption.steam import SteamAdapter
from app.redemption.worker import RedemptionWorker
from app.twitch_api import get_user_by_login


EVENTSUB_URL = "wss://eventsub.wss.twitch.tv/ws"

# Twitch channels to monitor.
# Add channel login names, without @ or Twitch URLs.
CHANNEL_LOGINS = [
    "dominent_orion",
    "whyisitmealways1"
    # "another_channel",
    # "third_channel",
]


async def create_chat_subscription(
    access_token: str,
    session_id: str,
    broadcaster_user_id: str,
    user_id: str,
) -> dict:
    """Create a channel.chat.message EventSub subscription."""

    url = "https://api.twitch.tv/helix/eventsub/subscriptions"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-Id": TWITCH_CLIENT_ID,
        "Content-Type": "application/json",
    }

    payload = {
        "type": "channel.chat.message",
        "version": "1",
        "condition": {
            "broadcaster_user_id": broadcaster_user_id,
            "user_id": user_id,
        },
        "transport": {
            "method": "websocket",
            "session_id": session_id,
        },
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            url,
            headers=headers,
            json=payload,
        )

    if response.status_code != 202:
        raise RuntimeError(
            "EventSub subscription failed: "
            f"{response.status_code} - {response.text}"
        )

    return response.json()


def build_chat_message(event: dict) -> ChatMessage:
    """Convert a raw Twitch chat event to our internal format."""

    return ChatMessage(
        event_id=event["message_id"],
        broadcaster_id=event["broadcaster_user_id"],
        broadcaster_login=event["broadcaster_user_login"],
        broadcaster_name=event["broadcaster_user_name"],
        chatter_id=event["chatter_user_id"],
        chatter_login=event["chatter_user_login"],
        chatter_name=event["chatter_user_name"],
        text=event["message"]["text"],
        received_at=datetime.now(timezone.utc),
    )


async def subscribe(
    access_token: str,
    session_id: str,
    broadcaster_user_id: str,
    broadcaster_login: str,
    user_id: str,
) -> bool:
    """Subscribe to one broadcaster's chat."""

    print()
    print(
        f"Creating chat subscription for "
        f"#{broadcaster_login}..."
    )

    try:
        result = await create_chat_subscription(
            access_token=access_token,
            session_id=session_id,
            broadcaster_user_id=broadcaster_user_id,
            user_id=user_id,
        )

        subscription = result["data"][0]

        print(
            f"[SUBSCRIBED] #{broadcaster_login} "
            f"| Status: {subscription['status']} "
            f"| ID: {subscription['id']}"
        )

        return True

    except Exception as exc:
        print(
            f"[SUBSCRIPTION ERROR] "
            f"#{broadcaster_login}: {exc}"
        )

        return False


def schedule_message_handler(
    chat_message: ChatMessage,
    tasks: set[asyncio.Task],
) -> None:
    """Schedule a handler without blocking the WebSocket listener."""

    task = asyncio.create_task(
        handle_chat_message(chat_message)
    )

    tasks.add(task)

    def on_task_done(completed_task: asyncio.Task) -> None:
        tasks.discard(completed_task)

        if completed_task.cancelled():
            return

        exception = completed_task.exception()

        if exception is not None:
            print(
                "[HANDLER ERROR] "
                f"Chat handler failed: {exception}"
            )

    task.add_done_callback(on_task_done)


async def run():
    tokens = load_tokens()

    browser = BrowserManager()
    worker_task = None
    message_handler_tasks: set[asyncio.Task] = set()

    try:
        await browser.start()

        steam_adapter = SteamAdapter(
            browser=browser,
            dry_run=True,
        )

        battlenet_adapter = BattleNetAdapter(
            browser=browser,
            dry_run=True,
        )

        await steam_adapter.prepare()
        await battlenet_adapter.prepare()

        worker = RedemptionWorker(
            queue=redemption_queue,
            adapters={
                "steam": steam_adapter,
                "battle.net": battlenet_adapter,
            },
        )

        worker_task = asyncio.create_task(worker.run())

        access_token = tokens["access_token"]
        user_id = tokens["user_id"]

        print()
        print("=" * 60)
        print("COD LIVE CODE MONITOR - EVENTSUB LISTENER")
        print("=" * 60)
        print()

        print("Configured channels:")
        for channel_login in CHANNEL_LOGINS:
            print(f"  - {channel_login}")

        # Resolve each configured channel to its Twitch user record.
        broadcasters = []

        print()
        print("Looking up Twitch channels...")

        for channel_login in CHANNEL_LOGINS:
            try:
                broadcaster = get_user_by_login(
                    access_token,
                    channel_login,
                )

                broadcasters.append(broadcaster)

                print(
                    f"[CHANNEL FOUND] "
                    f"{broadcaster['display_name']} "
                    f"(@{broadcaster['login']}) "
                    f"| ID: {broadcaster['id']}"
                )

            except Exception as exc:
                print(
                    f"[CHANNEL ERROR] "
                    f"Could not look up "
                    f"'{channel_login}': {exc}"
                )

        if not broadcasters:
            raise RuntimeError(
                "None of the configured Twitch channels "
                "could be resolved."
            )

        print()
        print(f"Channels resolved: {len(broadcasters)}")
        print(f"Chat user ID     : {user_id}")

        # Keep a bounded history of EventSub message IDs.
        from collections import deque

        MAX_PROCESSED_MESSAGE_IDS = 1000

        processed_message_ids = set()
        processed_message_order = deque()

        websocket_url = EVENTSUB_URL

        # Twitch transfers existing subscriptions when we use
        # the reconnect URL it provides.
        reuse_subscriptions = False

        while True:
            try:
                print()
                print("Connecting to Twitch EventSub...")
                print(websocket_url)

                async with websockets.connect(
                    websocket_url,
                    ping_interval=20,
                    ping_timeout=20,
                ) as websocket:

                    print("WebSocket connected.")
                    print("Waiting for session welcome...")

                    raw_message = await websocket.recv()
                    message = json.loads(raw_message)

                    message_type = message["metadata"]["message_type"]

                    if message_type != "session_welcome":
                        raise RuntimeError(
                            "Expected session_welcome, "
                            f"got {message_type}"
                        )

                    session = message["payload"]["session"]
                    session_id = session["id"]

                    print()
                    print("EventSub session established.")
                    print(f"Session ID: {session_id}")

                    # Twitch transfers subscriptions during a requested reconnect.
                    # Only create subscriptions for a new EventSub session.
                    if reuse_subscriptions:
                        print(
                            "[RECONNECT] Existing subscriptions were transferred "
                            "to the replacement session."
                        )

                        successful_subscriptions = len(broadcasters)
                        reuse_subscriptions = False

                    else:
                        # Create one subscription per resolved broadcaster.
                        successful_subscriptions = 0

                        for broadcaster in broadcasters:
                            subscribed = await subscribe(
                                access_token=access_token,
                                session_id=session_id,
                                broadcaster_user_id=broadcaster["id"],
                                broadcaster_login=broadcaster["login"],
                                user_id=user_id,
                            )

                            if subscribed:
                                successful_subscriptions += 1

                        if successful_subscriptions == 0:
                            raise RuntimeError(
                                "No channel subscriptions succeeded. "
                                "Check Twitch permissions and API errors."
                            )

                    print()
                    print("=" * 60)
                    print("EVENTSUB CHAT MONITOR ACTIVE")
                    print(
                        f"Successful subscriptions: "
                        f"{successful_subscriptions}/"
                        f"{len(broadcasters)}"
                    )
                    print("Waiting for chat messages...")
                    print("Press Ctrl+C to stop.")
                    print("=" * 60)
                    print()

                    while True:
                        raw_message = await websocket.recv()
                        message = json.loads(raw_message)

                        metadata = message["metadata"]
                        message_type = metadata["message_type"]
                        message_id = metadata.get("message_id")

                        # Deduplicate notifications, but do not discard
                        # messages that have no message_id metadata.
                        # Deduplicate EventSub messages using a bounded history.
                        if message_id:
                            if message_id in processed_message_ids:
                                print(
                                    "[DUPLICATE] "
                                    f"Ignoring message {message_id}"
                                )
                                continue

                            processed_message_ids.add(message_id)
                            processed_message_order.append(message_id)

                            if (
                                    len(processed_message_order)
                                    > MAX_PROCESSED_MESSAGE_IDS
                            ):
                                oldest_message_id = processed_message_order.popleft()
                                processed_message_ids.discard(oldest_message_id)

                        if message_type == "notification":
                            subscription_type = (
                                message["payload"]
                                ["subscription"]
                                ["type"]
                            )

                            if subscription_type == "channel.chat.message":
                                event = (
                                    message["payload"]["event"]
                                )

                                chat_message = build_chat_message(event)

                                print(
                                    f"[CHAT] "
                                    f"#{chat_message.broadcaster_login} "
                                    f"| {chat_message.chatter_login}: "
                                    "[Message content omitted]"
                                )

                                schedule_message_handler(
                                    chat_message,
                                    message_handler_tasks,
                                )

                                continue

                        if message_type == "session_keepalive":
                            print(
                                "[KEEPALIVE] "
                                "EventSub connection healthy."
                            )
                            continue

                        if message_type == "session_reconnect":
                            reconnect_url = (
                                message["payload"]
                                ["session"]
                                ["reconnect_url"]
                            )

                            print(
                                "Twitch requested a reconnect. "
                                "Switching to reconnect URL..."
                            )

                            websocket_url = reconnect_url
                            reuse_subscriptions = True
                            break

                        if message_type == "revocation":
                            subscription = (
                                message["payload"]["subscription"]
                            )

                            print(
                                "[REVOCATION] Twitch revoked "
                                "an EventSub subscription."
                            )
                            print(f"Type: {subscription['type']}")
                            print(f"Status: {subscription['status']}")

                            raise RuntimeError(
                                "EventSub subscription was revoked."
                            )

                        print(
                            "[EVENTSUB] Unhandled message type: "
                            f"{message_type}"
                        )

            except asyncio.CancelledError:
                raise

            except KeyboardInterrupt:
                raise


            except Exception as exc:

                print()

                print("EventSub connection error:")

                print(exc)

                # If the requested reconnect failed before the session

                # was established, fall back to a fresh EventSub session.

                if reuse_subscriptions:
                    print(

                        "[RECONNECT WARNING] The replacement session "

                        "was not established. Falling back to a new session."

                    )

                    reuse_subscriptions = False

                websocket_url = EVENTSUB_URL

                print("Retrying connection in 5 seconds...")

                await asyncio.sleep(5)

    finally:
        print()
        print("=" * 60)
        print("SHUTTING DOWN")
        print("=" * 60)

        if message_handler_tasks:
            print(
                "[SHUTDOWN] Waiting for "
                f"{len(message_handler_tasks)} "
                "message handler task(s)..."
            )

            await asyncio.gather(
                *message_handler_tasks,
                return_exceptions=True,
            )

        if worker_task is not None:
            print("[SHUTDOWN] Stopping redemption worker...")
            worker_task.cancel()

            try:
                await worker_task
            except asyncio.CancelledError:
                pass

        print("[SHUTDOWN] Closing browser...")
        await browser.close()

        print("[SHUTDOWN] Complete.")


if __name__ == "__main__":
    try:
        asyncio.run(run())

    except KeyboardInterrupt:
        print()
        print("EventSub monitor stopped.")

