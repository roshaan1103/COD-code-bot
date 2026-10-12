import time

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.browser.manager import BrowserManager
from app.redemption.base import (
    RedemptionJob,
    RedemptionResult,
)

def classify_battlenet_error(
    error_text: str,
) -> tuple[str, str]:
    """
    Classify a Battle.net error only when its wording
    explicitly identifies an invalid code.

    Unrecognized messages remain UNKNOWN.
    """

    normalized = " ".join(
        error_text.casefold().split()
    )

    if not normalized:
        return (
            "UNKNOWN",
            "The error message was empty.",
        )

    invalid_code_phrases = (
        "invalid code",
        "code is invalid",
        "incorrect code",
        "code is incorrect",
        "not a valid code",
        "cannot be claimed",
        "can't be claimed",
    )

    if any(
        phrase in normalized
        for phrase in invalid_code_phrases
    ):
        return (
            "INVALID_CODE",
            error_text.strip(),
        )

    return (
        "UNKNOWN",
        error_text.strip(),
    )

class BattleNetAdapter:
    platform = "battle.net"

    def __init__(
        self,
        browser: BrowserManager,
        dry_run: bool = True,
    ):
        self.browser = browser
        self.dry_run = dry_run

        # Locators are initialized during prepare().
        self.code_input = None
        self.redeem_button = None
        self.error_alert = None

    async def prepare(self) -> None:
        """
        Prepare the Battle.net redemption page once at startup.
        """

        page = self.browser.battlenet_page

        if page is None:
            raise RuntimeError(
                "Battle.net page is not available."
            )

        print()
        print("=" * 60)
        print("PREPARING BATTLE.NET REDEMPTION PAGE")
        print("=" * 60)

        # ---------------------------------------------------------
        # CACHE LOCATORS
        # ---------------------------------------------------------

        self.code_input = page.locator(
            "#enter-code-input"
        )

        self.redeem_button = page.locator(
            "#enter-key-submit"
        )

        # This error alert only exists after an error occurs.
        #
        # Therefore we create the locator here but do NOT require
        # it to exist during startup.
        self.error_alert = page.locator(
            "blz-alert.alert-notification-banner.error-notification-banner"
        )

        # ---------------------------------------------------------
        # VERIFY INPUT
        # ---------------------------------------------------------

        if await self.code_input.count() != 1:
            raise RuntimeError(
                "Battle.net code input "
                "#enter-code-input was not found."
            )

        # ---------------------------------------------------------
        # VERIFY REDEEM BUTTON
        # ---------------------------------------------------------

        if await self.redeem_button.count() != 1:
            raise RuntimeError(
                "Battle.net Redeem Code button "
                "#enter-key-submit was not found."
            )

        # ---------------------------------------------------------
        # VERIFY VISIBILITY
        # ---------------------------------------------------------

        if not await self.code_input.is_visible():
            raise RuntimeError(
                "Battle.net code input is not visible."
            )

        if not await self.redeem_button.is_visible():
            raise RuntimeError(
                "Battle.net Redeem Code button "
                "is not visible."
            )

        # ---------------------------------------------------------
        # INITIAL STATE
        # ---------------------------------------------------------

        initial_disabled = (
            await self.redeem_button.is_disabled()
        )

        print(
            "[BATTLE.NET] Code input ready."
        )

        print(
            "[BATTLE.NET] Redeem Code button ready."
        )

        print(
            "[BATTLE.NET] Initial button state: "
            f"disabled={initial_disabled}"
        )

        print()
        print(
            "[BATTLE.NET] Redemption page READY."
        )
        print("=" * 60)

    async def redeem(
        self,
        job: RedemptionJob,
    ) -> RedemptionResult:
        """
        Fill and, unless dry-run is enabled, submit one code.
        """

        if (
            self.code_input is None
            or self.redeem_button is None
            or self.error_alert is None
        ):
            raise RuntimeError(
                "Battle.net adapter has not been prepared."
            )

        started_at = time.perf_counter()

        code_input = self.code_input
        redeem_button = self.redeem_button
        error_alert = self.error_alert

        # ---------------------------------------------------------
        # FILL CODE
        # ---------------------------------------------------------

        await code_input.fill(job.code)

        code_filled_at = time.perf_counter()

        print()
        print("=" * 60)
        print("BATTLE.NET REDEMPTION")
        print("=" * 60)

        print(
            f"Code           : {job.code}"
        )

        print(
            f"Streamer       : {job.streamer}"
        )

        print(
            f"Dry run        : {self.dry_run}"
        )

        print(
            f"Code filled    : "
            f"{(code_filled_at - started_at) * 1000:.3f} ms"
        )

        # ---------------------------------------------------------
        # DRY RUN
        # ---------------------------------------------------------

        if self.dry_run:
            print()
            print(
                "[BATTLE.NET] Dry run enabled."
            )

            print(
                "[BATTLE.NET] Submission skipped."
            )

            print("=" * 60)

            return RedemptionResult(
                status="DRY_RUN",
                platform=job.platform,
                code=job.code,
                message=(
                    "Battle.net submission was skipped."
                ),
            )

        # ---------------------------------------------------------
        # WAIT FOR BUTTON TO BECOME ENABLED
        # ---------------------------------------------------------

        try:
            await redeem_button.wait_for(
                state="visible",
                timeout=3000,
            )

        except PlaywrightTimeoutError:
            return RedemptionResult(
                status="UNKNOWN",
                platform=job.platform,
                code=job.code,
                message=(
                    "Battle.net Redeem Code button "
                    "was not available."
                ),
            )

        if await redeem_button.is_disabled():
            return RedemptionResult(
                status="UNKNOWN",
                platform=job.platform,
                code=job.code,
                message=(
                    "Battle.net Redeem Code button "
                    "remained disabled after filling."
                ),
            )

        # ---------------------------------------------------------
        # SUBMIT
        # ---------------------------------------------------------

        print()
        print(
            "[BATTLE.NET] Submitting code..."
        )

        submit_started_at = time.perf_counter()

        try:
            async with code_input.page.expect_navigation(
                    wait_until="domcontentloaded",
                    timeout=3000,
            ):
                await redeem_button.click()

        except PlaywrightTimeoutError:
            click_finished_at = time.perf_counter()

            print(
                "[BATTLE.NET] Navigation did not complete "
                "within the expected time."
            )

            print(
                "[BATTLE.NET] Result will be classified "
                "from the current page."
            )

        else:
            click_finished_at = time.perf_counter()

        print(
            "[BATTLE.NET] Submit/navigation time: "
            f"{(click_finished_at - submit_started_at) * 1000:.3f} ms"
        )

        # ---------------------------------------------------------
        # CLASSIFY VISIBLE ERROR
        # ---------------------------------------------------------

        try:
            await error_alert.wait_for(
                state="visible",
                timeout=1000,
            )

        except PlaywrightTimeoutError:
            pass

        if await error_alert.count() > 0:
            if await error_alert.is_visible():
                error_text = (
                    await error_alert.inner_text()
                ).strip()

                status, message = (
                    classify_battlenet_error(
                        error_text
                    )
                )

                print()
                print(
                    "[BATTLE.NET] Error response detected."
                )

                print(
                    f"[BATTLE.NET] Classification: "
                    f"{status}"
                )

                print(
                    f"[BATTLE.NET] Message: {message}"
                )

                print("=" * 60)

                return RedemptionResult(
                    status=status,
                    platform=job.platform,
                    code=job.code,
                    message=message,
                )

        # ---------------------------------------------------------
        # UNKNOWN RESULT
        # ---------------------------------------------------------

        print()
        print(
            "[BATTLE.NET] No recognized error "
            "was detected."
        )

        print(
            "[BATTLE.NET] Success detection "
            "is not implemented yet."
        )

        print("=" * 60)

        return RedemptionResult(
            status="UNKNOWN",
            platform=job.platform,
            code=job.code,
            message=(
                "Battle.net returned no recognized "
                "result state."
            ),
        )


class page_expect_navigation:
    """
    Small async context-manager wrapper around Playwright's
    expect_navigation().

    This keeps the redemption method readable while allowing
    navigation timeout handling around the actual click.
    """

    def __init__(self, page):
        self.page = page
        self._context_manager = None

    async def __aenter__(self):
        self._context_manager = self.page.expect_navigation(
            wait_until="domcontentloaded",
            timeout=3000,
        )
        return await self._context_manager.__aenter__()

    async def __aexit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        return await self._context_manager.__aexit__(
            exc_type,
            exc_value,
            traceback,
        )

