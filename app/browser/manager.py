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
                user_data_dir=str(
                    BROWSER_PROFILE_DIR
                ),
                headless=False,
            )
        )

        print()
        print(
            "Persistent browser profile:"
        )
        print(BROWSER_PROFILE_DIR)

        # -----------------------------------------------------
        # Steam
        # -----------------------------------------------------

        self.steam_page = await self.context.new_page()

        print()
        print("Opening Steam redemption page...")

        await self.steam_page.goto(
            STEAM_REDEEM_URL,
            wait_until="domcontentloaded",
        )

        print(
            "Steam page loaded:"
            f" {self.steam_page.url}"
        )

        # -----------------------------------------------------
        # Battle.net
        # -----------------------------------------------------

        self.battlenet_page = (
            await self.context.new_page()
        )

        print()
        print(
            "Opening Battle.net redemption page..."
        )

        await self.battlenet_page.goto(
            BATTLENET_REDEEM_URL,
            wait_until="domcontentloaded",
        )

        print(
            "Battle.net page loaded:"
            f" {self.battlenet_page.url}"
        )

        print()
        print("=" * 60)
        print("BROWSER READY")
        print("=" * 60)
        print()
        print(
            "Check that both accounts are logged in."
        )
        print()
        print(
            "Press Ctrl+C to close the browser."
        )

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