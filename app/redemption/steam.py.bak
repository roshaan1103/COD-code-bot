import time

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.browser.manager import BrowserManager
from app.redemption.base import (
    RedemptionJob,
    RedemptionResult,
)


class SteamAdapter:
    platform = "steam"

    def __init__(
        self,
        browser: BrowserManager,
        dry_run: bool = True,
    ):
        self.browser = browser
        self.dry_run = dry_run

        # These locators are initialized during prepare().
        self.product_key = None
        self.register_button = None
        self.error_display = None

    async def prepare(self) -> None:
        """
        Prepare the Steam redemption page once during browser startup.

        This method verifies the required controls and checks the
        agreement checkbox so that the per-code redemption path
        does not need to perform that work.
        """

        page = self.browser.steam_page

        if page is None:
            raise RuntimeError(
                "Steam page is not available."
            )

        print()
        print("=" * 60)
        print("PREPARING STEAM REDEMPTION PAGE")
        print("=" * 60)

        self.product_key = page.locator("#product_key")
        checkbox = page.locator("#accept_ssa")
        self.register_button = page.locator("#register_btn")
        self.error_display = page.locator("#error_display")

        if await self.product_key.count() != 1:
            raise RuntimeError(
                "Steam product key input #product_key "
                "was not found."
            )

        if await checkbox.count() != 1:
            raise RuntimeError(
                "Steam agreement checkbox #accept_ssa "
                "was not found."
            )

        if await self.register_button.count() != 1:
            raise RuntimeError(
                "Steam Continue control #register_btn "
                "was not found."
            )

        if await self.error_display.count() != 1:
            raise RuntimeError(
                "Steam error container #error_display "
                "was not found."
            )

        if not await checkbox.is_checked():
            await checkbox.check()

        if not await checkbox.is_checked():
            raise RuntimeError(
                "Steam agreement checkbox could not be checked."
            )

        print("[STEAM] Product key input ready.")
        print("[STEAM] Agreement checkbox ready.")
        print("[STEAM] Continue control ready.")
        print("[STEAM] Error container ready.")
        print("[STEAM] Agreement checkbox is checked.")

        print()
        print("[STEAM] Redemption page READY.")
        print("=" * 60)

    async def redeem(
        self,
        job: RedemptionJob,
    ) -> RedemptionResult:
        """
        Redeem one Steam code using the already-prepared page.

        Dry-run mode fills the input but never submits the code.

        Real mode:
        1. Submits the code once.
        2. Interprets Steam's response.
        3. Verifies the success receipt and product details.
        4. Attempts to click Finish and return to the account page.

        If activation is confirmed but the final navigation fails,
        the redemption remains SUCCESS.
        """

        if (
            self.product_key is None
            or self.register_button is None
            or self.error_display is None
        ):
            raise RuntimeError(
                "Steam adapter has not been prepared."
            )

        started_at = time.perf_counter()

        product_key = self.product_key
        register_button = self.register_button
        error_display = self.error_display
        page = self.browser.steam_page

        controls_ready_at = time.perf_counter()

        # ---------------------------------------------------------
        # FILL CODE
        # ---------------------------------------------------------

        await product_key.fill(job.code)

        code_filled_at = time.perf_counter()

        print()
        print("=" * 60)
        print("STEAM REDEMPTION")
        print("=" * 60)

        # Avoid printing the actual key in application logs.
        print("[STEAM] Code loaded.")
        print(f"Streamer       : {job.streamer}")
        print(f"Dry run        : {self.dry_run}")

        print()
        print(
            f"Controls ready : "
            f"{(controls_ready_at - started_at) * 1000:.3f} ms"
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
            print("[STEAM] Dry run enabled.")
            print("[STEAM] Submission skipped.")
            print("[STEAM] Finish navigation skipped.")
            print("=" * 60)

            return RedemptionResult(
                status="DRY_RUN",
                platform=job.platform,
                code=job.code,
                message="Steam submission was skipped.",
            )

        # ---------------------------------------------------------
        # REAL SUBMISSION
        # ---------------------------------------------------------

        print()
        print("[STEAM] Submitting code...")

        submit_started_at = time.perf_counter()

        try:
            # Listen before clicking so a fast response is not missed.
            async with page.expect_response(
                lambda response: (
                    "/account/ajaxregisterkey/" in response.url
                    and response.request.method == "POST"
                ),
                timeout=15000,
            ) as response_info:
                await register_button.click()

            response = await response_info.value

            click_finished_at = time.perf_counter()

            print(
                f"[STEAM] Click completed in "
                f"{(click_finished_at - submit_started_at) * 1000:.3f} ms"
            )
            print(
                f"[STEAM] Response HTTP status: {response.status}"
            )

        except PlaywrightTimeoutError:
            print()
            print(
                "[STEAM] Timed out waiting for the redemption response."
            )
            print(
                "[STEAM] The outcome is unknown; do not automatically retry."
            )
            print("=" * 60)

            return RedemptionResult(
                status="UNKNOWN",
                platform=job.platform,
                code=job.code,
                message=(
                    "Timed out waiting for Steam's redemption response. "
                    "The code may or may not have been processed."
                ),
            )


        except Exception:

            print()

            print("[STEAM] Submission/result error.")

            print(

                "[STEAM] The outcome is unknown; do not automatically retry."

            )
            print("=" * 60)

            return RedemptionResult(
                status="UNKNOWN",
                platform=job.platform,
                code=job.code,
                message=(
                    "An error occurred while submitting or observing "
                    "the Steam response. The outcome is unknown."
                ),
            )

        # ---------------------------------------------------------
        # VALIDATE HTTP RESPONSE
        # ---------------------------------------------------------

        if not response.ok:
            print()
            print(
                f"[STEAM] HTTP request failed: {response.status}"
            )
            print("[STEAM] Redemption cannot be confirmed.")
            print("=" * 60)

            return RedemptionResult(
                status="UNKNOWN",
                platform=job.platform,
                code=job.code,
                message=(
                    f"Steam returned HTTP {response.status}. "
                    "Redemption could not be confirmed."
                ),
            )

        # ---------------------------------------------------------
        # PARSE STEAM RESPONSE
        # ---------------------------------------------------------

        try:
            result_data = await response.json()
        except Exception:
            print()
            print("[STEAM] Response was not valid JSON.")
            print("[STEAM] Result cannot be confirmed.")
            print("=" * 60)

            return RedemptionResult(
                status="UNKNOWN",
                platform=job.platform,
                code=job.code,
                message=(
                    "Steam returned a response that could not be "
                    "parsed as JSON."
                ),
            )

        if not isinstance(result_data, dict):
            return RedemptionResult(
                status="UNKNOWN",
                platform=job.platform,
                code=job.code,
                message="Steam returned an unexpected JSON structure.",
            )

        # ---------------------------------------------------------
        # SUCCESS: VERIFY RECEIPT, CAPTURE PRODUCT, CLICK FINISH
        # ---------------------------------------------------------

        if result_data.get("success") == 1:
            print()
            print(
                "[STEAM] Response indicates successful redemption."
            )
            print("[STEAM] Verifying the receipt page...")

            receipt_form = page.locator("#receipt_form")
            product_list = page.locator(
                "#registerkey_productlist"
            )

            try:
                await receipt_form.wait_for(
                    state="visible",
                    timeout=5000,
                )

                await product_list.wait_for(
                    state="visible",
                    timeout=3000,
                )

                # Capture the product name BEFORE leaving the receipt.
                product_text = (
                    await product_list.inner_text()
                ).strip()

                if not product_text:
                    raise RuntimeError(
                        "The Steam receipt contains no product details."
                    )


            except Exception:

                print("[STEAM] Receipt verification failed.")
                print(
                    "[STEAM] Returning UNKNOWN; success "
                    "cannot be confirmed."
                )
                print("=" * 60)

                return RedemptionResult(
                    status="UNKNOWN",
                    platform=job.platform,
                    code=job.code,
                    message=(
                        "Steam returned a successful response, "
                        "but a receipt containing product details "
                        "could not be verified."
                    ),
                )

            # At this point, activation has been confirmed by the
            # successful response and populated receipt.
            print()
            print("[STEAM] SUCCESS: Redemption receipt verified.")
            print(f"[STEAM] Receipt product: {product_text}")

            # -----------------------------------------------------
            # CLICK FINISH
            # -----------------------------------------------------

            finish_succeeded = False
            finish_message = ""

            try:
                # The inspected Steam DOM showed that Finish is the
                # receipt link pointing to the Steam account page.
                finish_button = receipt_form.locator(
                    "a[href='https://store.steampowered.com/account']"
                )

                if await finish_button.count() != 1:
                    raise RuntimeError(
                        "Could not uniquely identify the Steam Finish link."
                    )

                # Verify the expected destination before clicking.
                finish_href = await finish_button.get_attribute("href")

                if finish_href != "https://store.steampowered.com/account":
                    raise RuntimeError(
                        "The Steam Finish link destination was unexpected."
                    )

                print("[STEAM] Clicking Finish...")

                # Register the navigation wait before clicking.
                async with page.expect_navigation(
                    wait_until="domcontentloaded",
                    timeout=10000,
                ):
                    await finish_button.click()

                # Confirm the resulting page is the expected account URL.
                await page.wait_for_url(
                    "https://store.steampowered.com/account",
                    wait_until="domcontentloaded",
                    timeout=5000,
                )

                finish_succeeded = True

                print(
                    "[STEAM] Finish clicked; account page navigation confirmed."
                )

            except Exception as exc:
                # Do not downgrade a confirmed redemption because
                # post-redemption navigation failed.
                finish_message = (
                    " Activation was confirmed, but automatic Finish "
                    "navigation could not be confirmed. "
                    "Check the Steam browser tab."
                )

                print("[STEAM] Finish/navigation warning.")
                print(
                    "[STEAM] The redemption remains SUCCESS."
                )

            print("=" * 60)

            if finish_succeeded:
                message = (
                    f"Steam activation confirmed. Product: {product_text}. "
                    "The Finish link was clicked and the account page "
                    "navigation was confirmed."
                )
            else:
                message = (
                    f"Steam activation confirmed. Product: {product_text}."
                    f"{finish_message}"
                )

            return RedemptionResult(
                status="SUCCESS",
                platform=job.platform,
                code=job.code,
                message=message,
            )

        # ---------------------------------------------------------
        # FAILURE DETAILS
        # ---------------------------------------------------------

        purchase_result = result_data.get(
            "purchase_result_details"
        )

        # Only match actual integer result codes, not strings or booleans.
        if type(purchase_result) is int and purchase_result == 14:
            error_text = (
                await error_display.inner_text()
            ).strip()

            message = (
                    error_text
                    or "Steam reported an invalid product code."
            )

            print()
            print("[STEAM] INVALID_CODE")
            print("[STEAM] Steam reported an invalid product code.")
            print("=" * 60)

            return RedemptionResult(
                status="INVALID_CODE",
                platform=job.platform,
                code=job.code,
                message=message,
            )

        if type(purchase_result) is int and purchase_result == 15:
            message = (
                "Steam reports that this code was already activated "
                "on another Steam account."
            )

            print()
            print("[STEAM] ALREADY_REDEEMED")
            print("=" * 60)

            return RedemptionResult(
                status="ALREADY_REDEEMED",
                platform=job.platform,
                code=job.code,
                message=message,
            )

        if type(purchase_result) is int and purchase_result == 53:
            message = (
                "Steam reports too many recent activation attempts. "
                "Stop further redemption attempts and investigate "
                "before continuing."
            )

            print()
            print("[STEAM] RATE_LIMITED")
            print(f"[STEAM] {message}")
            print("=" * 60)

            return RedemptionResult(
                status="RATE_LIMITED",
                platform=job.platform,
                code=job.code,
                message=message,
            )

        # Do not guess what other Steam result codes mean.
        error_text = (
            await error_display.inner_text()
        ).strip()

        print()
        print("[STEAM] Steam returned an unrecognized failure.")
        print("[STEAM] Steam returned unrecognized response details.")

        if error_text:
            print("[STEAM] Additional error details were returned.")

        print("[STEAM] Returning UNKNOWN rather than guessing.")
        print("=" * 60)

        return RedemptionResult(
            status="UNKNOWN",
            platform=job.platform,
            code=job.code,
            message=(
                "Steam did not confirm success, and the returned "
                "failure could not be classified safely."
            ),
        )