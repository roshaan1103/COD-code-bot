from pathlib import Path

from playwright.async_api import (
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)


STEAM_REDEEM_URL = (
    "https://store.steampowered.com/account/registerkey"
)

BATTLENET_REDEEM_URL = (
    "https://eu.checkout.battle.net/"
    "shop/en-us/checkout/key-claim?flowTrackingId"
)


BROWSER_PROFILE_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "browser_profile"
)


class BrowserManager:
    """
    Manages the persistent Playwright browser context
    used by the redemption adapters.
    """

    def __init__(self):
        self.playwright: Playwright | None = None
        self.context: BrowserContext | None = None

        self.steam_page: Page | None = None
        self.battlenet_page: Page | None = None

    async def start(self) -> None:
        """
        Start Playwright and open the redemption pages.

        A navigation timeout is reported without preventing
        the other redemption page from opening.
        """

        print()
        print("=" * 60)
        print("STARTING PLAYWRIGHT BROWSER")
        print("=" * 60)

        BROWSER_PROFILE_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.playwright = await async_playwright().start()

        self.context = (
            await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(BROWSER_PROFILE_DIR),
                headless=False,
            )
        )

        print()
        print("Persistent browser profile:")
        print(BROWSER_PROFILE_DIR)

        # -----------------------------------------------------
        # Steam
        # -----------------------------------------------------

        self.steam_page = await self.context.new_page()

        print()
        print("Opening Steam redemption page...")

        try:
            await self.steam_page.goto(
                STEAM_REDEEM_URL,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            print(
                "Steam page loaded:"
                f" {self.steam_page.url}"
            )

        except Exception as exc:
            print(
                "[BROWSER] Steam navigation did not complete:"
                f" {type(exc).__name__}: {exc}"
            )
            print(
                "[BROWSER] Inspect the Steam tab manually."
            )

        # -----------------------------------------------------
        # Battle.net
        # -----------------------------------------------------

        self.battlenet_page = await self.context.new_page()

        print()
        print("Opening Battle.net redemption page...")

        try:
            await self.battlenet_page.goto(
                BATTLENET_REDEEM_URL,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            print(
                "Battle.net page loaded:"
                f" {self.battlenet_page.url}"
            )

        except Exception as exc:
            print(
                "[BROWSER] Battle.net navigation did not complete:"
                f" {type(exc).__name__}: {exc}"
            )
            print(
                "[BROWSER] Inspect the Battle.net tab manually."
            )

        print()
        print("=" * 60)
        print("BROWSER READY FOR MANUAL INSPECTION")
        print("=" * 60)
        print()
        print(
            "Check both tabs and log in manually if necessary."
        )
        print(
            "Do not run redemption attempts until the pages "
            "are confirmed to be ready."
        )
        print()
        print("Press Ctrl+C to close the browser.")

    async def close(self) -> None:
        """
        Close the browser and Playwright.
        """

        print()
        print("Closing browser...")

        if self.context is not None:
            await self.context.close()

        if self.playwright is not None:
            await self.playwright.stop()

        print("Browser closed.")

