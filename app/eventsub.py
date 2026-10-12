import asyncio
import json
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

# CHANGE THIS
CHANNEL_LOGIN = "dominent_orion"


async def create_chat_subscription(
    access_token: str,
    session_id: str,
    broadcaster_user_id: str,
    user_id: str,
) -> dict:
    """
    Create a channel.chat.message EventSub subscription.
    """

    url = (
        "https://api.twitch.tv/helix/eventsub/subscriptions"
    )

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
    """
    Convert Twitch's raw chat event into our internal
    ChatMessage representation.
    """

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
    user_id: str,
) -> None:
    """
    Create the EventSub chat subscription.
    """

    print()
    print("Creating channel.chat.message subscription...")

    result = await create_chat_subscription(
        access_token=access_token,
        session_id=session_id,
        broadcaster_user_id=broadcaster_user_id,
        user_id=user_id,
    )

    subscription = result["data"][0]

    print()
    print("Subscription created successfully.")
    print(f"Subscription ID: {subscription['id']}")
    print(f"Status        : {subscription['status']}")
    print(f"Type          : {subscription['type']}")


def schedule_message_handler(
    chat_message: ChatMessage,
    tasks: set[asyncio.Task],
) -> None:
    """
    Schedule a chat handler without blocking the
    EventSub WebSocket listener.
    """

    task = asyncio.create_task(
        handle_chat_message(chat_message)
    )

    tasks.add(task)

    def on_task_done(
        completed_task: asyncio.Task,
    ) -> None:
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

        worker_task = asyncio.create_task(
            worker.run()
        )

        access_token = tokens["access_token"]
        user_id = tokens["user_id"]

        print()
        print("=" * 60)
        print("COD LIVE CODE MONITOR - EVENTSUB LISTENER")
        print("=" * 60)
        print()

        print(f"Target channel: {CHANNEL_LOGIN}")

        print()
        print("Looking up Twitch channel...")

        broadcaster = get_user_by_login(
            access_token,
            CHANNEL_LOGIN,
        )

        broadcaster_user_id = broadcaster["id"]
        broadcaster_login = broadcaster["login"]
        broadcaster_name = broadcaster["display_name"]

        print(f"Channel name : {broadcaster_name}")
        print(f"Channel login: {broadcaster_login}")
        print(f"Channel ID   : {broadcaster_user_id}")

        print()
        print(f"Chat user ID : {user_id}")

        processed_message_ids = set()

        websocket_url = EVENTSUB_URL

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

                    message_type = (
                        message["metadata"]["message_type"]
                    )

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

                    await subscribe(
                        access_token=access_token,
                        session_id=session_id,
                        broadcaster_user_id=broadcaster_user_id,
                        user_id=user_id,
                    )

                    print()
                    print("=" * 60)
                    print(
                        f"LISTENING TO #{broadcaster_login}"
                    )
                    print(
                        "Waiting for chat messages..."
                    )
                    print("Press Ctrl+C to stop.")
                    print("=" * 60)
                    print()

                    while True:

                        raw_message = await websocket.recv()

                        message = json.loads(raw_message)

                        metadata = message["metadata"]

                        message_type = metadata[
                            "message_type"
                        ]

                        message_id = metadata[
                            "message_id"
                        ]

                        if message_id in processed_message_ids:
                            print(
                                "[DUPLICATE] "
                                f"Ignoring message {message_id}"
                            )
                            continue

                        processed_message_ids.add(message_id)

                        if message_type == "notification":

                            subscription_type = (
                                message["payload"]
                                ["subscription"]
                                ["type"]
                            )

                            if (
                                subscription_type
                                == "channel.chat.message"
                            ):
                                event = (
                                    message["payload"]
                                    ["event"]
                                )

                                chat_message = (
                                    build_chat_message(
                                        event
                                    )
                                )

                                schedule_message_handler(
                                    chat_message,
                                    message_handler_tasks,
                                )

                                continue

                        if (
                            message_type
                            == "session_keepalive"
                        ):
                            print(
                                "[KEEPALIVE] "
                                "EventSub connection healthy."
                            )
                            continue

                        if (
                            message_type
                            == "session_reconnect"
                        ):
                            reconnect_url = (
                                message["payload"]
                                ["session"]
                                ["reconnect_url"]
                            )

                            print()
                            print(
                                "Twitch requested a reconnect."
                            )

                            print(
                                "Switching to Twitch "
                                "reconnect URL..."
                            )

                            websocket_url = (
                                reconnect_url
                            )

                            break

                        if message_type == "revocation":

                            subscription = (
                                message["payload"]
                                ["subscription"]
                            )

                            print()
                            print(
                                "WARNING: Twitch revoked "
                                "an EventSub subscription."
                            )

                            print(
                                f"Type: "
                                f"{subscription['type']}"
                            )

                            print(
                                f"Reason: "
                                f"{subscription['status']}"
                            )

                            raise RuntimeError(
                                "EventSub subscription "
                                "was revoked."
                            )

                        print(
                            "[EVENTSUB] "
                            f"Unhandled message type: "
                            f"{message_type}"
                        )

            except asyncio.CancelledError:
                raise

            except KeyboardInterrupt:
                raise

            except Exception as exc:
                print()
                print(
                    "EventSub connection error:"
                )
                print(exc)

                print()
                print(
                    "Retrying connection in 5 seconds..."
                )

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