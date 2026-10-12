import asyncio

import httpx

from app.auth import load_tokens, validate_access_token
from app.config import TWITCH_CLIENT_ID
from app.irc_chat import listen_to_channel
from app.message_handler import redemption_queue
from app.browser.manager import BrowserManager
from app.redemption.battlenet import BattleNetAdapter
from app.redemption.steam import SteamAdapter
from app.redemption.worker import RedemptionWorker

CHANNEL_LOGINS = [
"oilrats",
"timthetatman",
]

TWITCH_USERS_URL = "https://api.twitch.tv/helix/users"

def get_broadcaster_by_login(
    access_token: str,
    login: str,
    ) -> dict:
    """Retrieve a broadcaster's Twitch account details."""


    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {access_token}",
    }

    response = httpx.get(
        TWITCH_USERS_URL,
        headers=headers,
        params={"login": login},
        timeout=15.0,
    )

    response.raise_for_status()

    users = response.json().get("data", [])

    if not users:
        raise RuntimeError(
            f"Twitch user not found: {login}"
        )

    user = users[0]

    return {
        "id": user["id"],
        "login": user["login"],
        "display_name": user["display_name"],
    }


async def prepare_broadcasters(
    access_token: str,
    ) -> list[dict]:
    """Resolve configured channel logins to Twitch user records."""


    broadcasters = []

    for channel_login in CHANNEL_LOGINS:
        try:
            broadcaster = await asyncio.to_thread(
                get_broadcaster_by_login,
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

        except (httpx.HTTPError, RuntimeError, KeyError) as exc:
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

    return broadcasters


async def main() -> None:
    """Start IRC listeners and the existing dry-run redemption pipeline."""


    tokens = load_tokens()

    access_token = tokens.get("access_token")
    username = tokens.get("login")

    if not access_token or not username:
        raise RuntimeError(
            "The token file must contain access_token and login."
        )

    print("[IRC RUNNER] Validating saved Twitch credentials...")

    token_info = await asyncio.to_thread(
        validate_access_token,
        access_token,
    )

    if token_info.get("login", "").lower() != username.lower():
        raise RuntimeError(
            "The saved login does not match the validated token identity."
        )

    granted_scopes = set(token_info.get("scopes", []))

    if "chat:read" not in granted_scopes:
        raise RuntimeError(
            "The token lacks chat:read. Reauthorize the Twitch account."
        )

    print(
        f"[IRC RUNNER] Authenticated as "
        f"{token_info.get('login')}."
    )

    broadcasters = await prepare_broadcasters(access_token)

    browser = BrowserManager()
    worker_task = None
    listener_tasks = []

    try:
        # Start the existing browser manager.
        await browser.start()

        # IMPORTANT: Keep both adapters in dry-run mode.
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

        # Reuse the application's existing queue.
        worker = RedemptionWorker(
            queue=redemption_queue,
            adapters={
                "steam": steam_adapter,
                "battle.net": battlenet_adapter,
            },
        )

        worker_task = asyncio.create_task(
            worker.run(),
            name="redemption-worker",
        )

        print()
        print("=" * 60)
        print("COD LIVE CODE MONITOR - IRC LISTENER")
        print("=" * 60)
        print(f"Authenticated account: {username}")
        print(f"Configured channels : {len(broadcasters)}")
        print("Redemption mode      : DRY RUN")
        print("Press Ctrl+C to stop.")
        print("=" * 60)

        for broadcaster in broadcasters:
            listener_task = asyncio.create_task(
                listen_to_channel(
                    access_token=access_token,
                    channel_login=broadcaster["login"],
                    broadcaster=broadcaster,
                    username=username,
                ),
                name=f"irc-{broadcaster['login']}",
            )

            listener_tasks.append(listener_task)

        # Keep the runner alive while listeners are running.
        results = await asyncio.gather(
            *listener_tasks,
            return_exceptions=True,
        )

        for broadcaster, result in zip(broadcasters, results):
            if isinstance(result, Exception):
                print(
                    f"[IRC RUNNER] Listener for "
                    f"#{broadcaster['login']} stopped: {result}"
                )

        if all(task.done() for task in listener_tasks):
            print(
                "[IRC RUNNER] All IRC listeners have stopped."
            )

    finally:
        print()
        print("=" * 60)
        print("SHUTTING DOWN IRC RUNNER")
        print("=" * 60)

        # Cancel and await IRC listeners first.
        for task in listener_tasks:
            if not task.done():
                task.cancel()

        if listener_tasks:
            await asyncio.gather(
                *listener_tasks,
                return_exceptions=True,
            )

        # Stop the redemption worker.
        if worker_task is not None:
            print("[SHUTDOWN] Stopping redemption worker...")
            worker_task.cancel()

            try:
                await worker_task
            except asyncio.CancelledError:
                pass

        # Close the browser even if listener startup or shutdown fails.
        print("[SHUTDOWN] Closing browser...")
        await browser.close()

        print("[SHUTDOWN] Complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[IRC RUNNER] Stopped by user.")
