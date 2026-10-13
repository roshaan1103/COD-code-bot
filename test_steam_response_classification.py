import asyncio
from contextlib import asynccontextmanager

from app.redemption.base import RedemptionJob
from app.redemption.steam import SteamAdapter


STEAM_ACCOUNT_URL = "https://store.steampowered.com/account"


class FakeLocator:
    def __init__(
        self,
        text="",
        visible=True,
        count=1,
        href=None,
        page=None,
    ):
        self.text = text
        self.visible = visible
        self.element_count = count
        self.href = href
        self.page = page

        self.filled_value = None
        self.clicked = False

    async def fill(self, value):
        self.filled_value = value

    async def click(self):
        self.clicked = True

        # Only the simulated Finish link triggers navigation.
        if self.href == STEAM_ACCOUNT_URL and self.page is not None:
            self.page.finish_clicked = True

            if self.page.navigation_should_fail:
                raise RuntimeError(
                    "Simulated Finish navigation failure"
                )

            self.page.url = STEAM_ACCOUNT_URL

    async def inner_text(self):
        return self.text

    async def count(self):
        return self.element_count

    async def is_visible(self):
        return self.visible and self.element_count > 0

    async def get_attribute(self, name):
        if name == "href":
            return self.href

        return None

    def locator(self, selector):
        if (
            selector
            == "a[href='https://store.steampowered.com/account']"
        ):
            return self.page.finish_button

        raise AssertionError(
            f"Unexpected nested locator: {selector}"
        )

    async def wait_for(self, state="visible", timeout=None):
        if state == "visible":
            if not self.visible or self.element_count == 0:
                raise TimeoutError(
                    "Element did not become visible"
                )

        elif state == "hidden":
            if self.visible and self.element_count > 0:
                raise TimeoutError(
                    "Element did not become hidden"
                )


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status
        self.url = (
            "https://store.steampowered.com/account/ajaxregisterkey/"
        )
        self.request = FakeRequest()
        self.ok = 200 <= status < 400

    async def json(self):
        return self.payload


class FakeRequest:
    def __init__(self):
        self.method = "POST"


class FakeResponseInfo:
    def __init__(self, response):
        self.response = response
        self.value = self._get_response()

    async def _get_response(self):
        return self.response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False


class FakeNavigation:
    def __init__(self, page, timeout=None):
        self.page = page
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            return False

        if self.page.navigation_should_fail:
            raise TimeoutError(
                "Simulated navigation timeout"
            )

        if not self.page.finish_clicked:
            raise AssertionError(
                "Expected Finish to be clicked before navigation"
            )

        return False


class FakePage:
    def __init__(
        self,
        response,
        receipt_visible=False,
        product_text="",
        receipt_count=1,
        product_count=None,
        finish_count=1,
        navigation_should_fail=False,
    ):
        self.response = response
        self.url = (
            "https://store.steampowered.com/account/registerkey"
        )

        self.navigation_should_fail = navigation_should_fail
        self.finish_clicked = False

        if product_count is None:
            product_count = 1 if product_text else 0

        self.receipt_form = FakeLocator(
            text="Steam receipt",
            visible=receipt_visible and receipt_count > 0,
            count=receipt_count,
            page=self,
        )

        self.product_list = FakeLocator(
            text=product_text,
            visible=receipt_visible and product_count > 0,
            count=product_count,
            page=self,
        )

        self.finish_button = FakeLocator(
            text="Finish",
            visible=receipt_visible and finish_count > 0,
            count=finish_count,
            href=STEAM_ACCOUNT_URL,
            page=self,
        )

        self.response_info = FakeResponseInfo(response)

    def expect_response(self, predicate, timeout=None):
        # Ensure the adapter's response filter matches our fake response.
        if not predicate(self.response):
            raise AssertionError(
                "Fake response did not match the expected response filter"
            )

        return self.response_info

    def expect_navigation(self, wait_until=None, timeout=None):
        return FakeNavigation(
            page=self,
            timeout=timeout,
        )

    async def wait_for_url(
        self,
        expected_url,
        wait_until=None,
        timeout=None,
    ):
        if self.navigation_should_fail:
            raise TimeoutError(
                "Simulated wait_for_url timeout"
            )

        if self.url != expected_url:
            raise AssertionError(
                f"Expected URL {expected_url}, got {self.url}"
            )

    def locator(self, selector):
        if selector == "#receipt_form":
            return self.receipt_form

        if selector == "#registerkey_productlist":
            return self.product_list

        raise AssertionError(
            f"Unexpected selector requested by SteamAdapter: {selector}"
        )


class FakeBrowser:
    def __init__(self, page):
        self.steam_page = page


async def run_test(
    payload,
    expected_status,
    *,
    http_status=200,
    receipt_visible=False,
    product_text="",
    receipt_count=1,
    product_count=None,
    finish_count=1,
    navigation_should_fail=False,
):
    response = FakeResponse(
        payload=payload,
        status=http_status,
    )

    page = FakePage(
        response=response,
        receipt_visible=receipt_visible,
        product_text=product_text,
        receipt_count=receipt_count,
        product_count=product_count,
        finish_count=finish_count,
        navigation_should_fail=navigation_should_fail,
    )

    browser = FakeBrowser(page)

    adapter = SteamAdapter(
        browser=browser,
        dry_run=False,
    )

    # Supply the controls that prepare() normally caches.
    adapter.product_key = FakeLocator()
    adapter.register_button = FakeLocator()
    adapter.error_display = FakeLocator(
        text="Simulated Steam error",
        visible=False,
    )

    job = RedemptionJob(
        platform="steam",
        code="AAAA-BBBB-CCCC-DDDD",
        streamer="test-streamer",
    )

    result = await adapter.redeem(job)

    assert result.status == expected_status, (
        f"Expected {expected_status}, got {result.status}. "
        f"Message: {result.message}"
    )

    assert adapter.register_button.clicked, (
        "Expected the simulated registration button to be clicked"
    )

    return result, page


async def main():
    tests = [
        (
            "Successful response with receipt and product",
            {
                "success": 1,
                "purchase_result_details": 0,
            },
            "SUCCESS",
            {
                "receipt_visible": True,
                "product_text": "Example Game",
            },
            "success",
        ),
        (
            "Successful response without visible receipt",
            {
                "success": 1,
                "purchase_result_details": 0,
            },
            "UNKNOWN",
            {
                "receipt_visible": False,
                "product_text": "",
            },
            "normal",
        ),
        (
            "Visible receipt with empty product list",
            {
                "success": 1,
                "purchase_result_details": 0,
            },
            "UNKNOWN",
            {
                "receipt_visible": True,
                "product_text": "",
                "product_count": 1,
            },
            "normal",
        ),
        (
            "Receipt product text contains only whitespace",
            {
                "success": 1,
                "purchase_result_details": 0,
            },
            "UNKNOWN",
            {
                "receipt_visible": True,
                "product_text": "   \n\t   ",
                "product_count": 1,
            },
            "normal",
        ),
        (
            "Missing product-list element",
            {
                "success": 1,
                "purchase_result_details": 0,
            },
            "UNKNOWN",
            {
                "receipt_visible": True,
                "product_text": "",
                "product_count": 0,
            },
            "normal",
        ),
        (
            "Missing receipt container",
            {
                "success": 1,
                "purchase_result_details": 0,
            },
            "UNKNOWN",
            {
                "receipt_visible": True,
                "product_text": "Example Game",
                "receipt_count": 0,
            },
            "normal",
        ),
        (
            "Invalid key result code 14",
            {
                "success": 0,
                "purchase_result_details": 14,
            },
            "INVALID_CODE",
            {},
            "normal",
        ),
        (
            "Already redeemed result code 15",
            {
                "success": 0,
                "purchase_result_details": 15,
            },
            "ALREADY_REDEEMED",
            {},
            "normal",
        ),
        (
            "Rate-limited result code 53",
            {
                "success": 0,
                "purchase_result_details": 53,
            },
            "RATE_LIMITED",
            {},
            "normal",
        ),
        (
            "Unexpected Steam result code",
            {
                "success": 0,
                "purchase_result_details": 999,
            },
            "UNKNOWN",
            {},
            "normal",
        ),
        (
            "HTTP 500 despite success-like JSON",
            {
                "success": 1,
                "purchase_result_details": 0,
            },
            "UNKNOWN",
            {
                "http_status": 500,
                "receipt_visible": True,
                "product_text": "Example Game",
            },
            "normal",
        ),
        (
            "Finish clicked and account navigation confirmed",
            {
                "success": 1,
                "purchase_result_details": 0,
            },
            "SUCCESS",
            {
                "receipt_visible": True,
                "product_text": "Example Game",
            },
            "finish_success",
        ),
        (
            "Finish navigation failure preserves SUCCESS",
            {
                "success": 1,
                "purchase_result_details": 0,
            },
            "SUCCESS",
            {
                "receipt_visible": True,
                "product_text": "Example Game",
                "navigation_should_fail": True,
            },
            "finish_failure",
        ),
        (
            "Missing Finish link preserves SUCCESS with warning",
            {
                "success": 1,
                "purchase_result_details": 0,
            },
            "SUCCESS",
            {
                "receipt_visible": True,
                "product_text": "Example Game",
                "finish_count": 0,
            },
            "finish_failure",
        ),
    ]

    passed = 0

    for name, payload, expected_status, options, mode in tests:
        try:
            result, page = await run_test(
                payload=payload,
                expected_status=expected_status,
                **options,
            )

            if mode == "success":
                # A valid receipt should trigger a Finish attempt.
                assert page.finish_clicked, (
                    "Expected Finish to be clicked after receipt verification"
                )

            elif mode == "finish_success":
                assert page.finish_clicked, (
                    "Expected the Finish link to be clicked"
                )
                assert page.url == STEAM_ACCOUNT_URL, (
                    f"Expected account URL, got {page.url}"
                )
                assert "Example Game" in result.message, (
                    "Expected the product name in the result message"
                )

            elif mode == "finish_failure":
                assert result.status == "SUCCESS", (
                    "A verified activation must remain SUCCESS"
                )
                assert "could not be confirmed" in result.message.lower(), (
                    "Expected a warning about unconfirmed navigation"
                )

            print(f"PASS: {name}")
            passed += 1

        except Exception as exc:
            print(f"FAIL: {name}")
            print(f"      {type(exc).__name__}: {exc}")

    print()
    print(f"Results: {passed}/{len(tests)} tests passed")

    if passed != len(tests):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())