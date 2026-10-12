import asyncio

from app.redemption.base import RedemptionJob
from app.redemption.steam import SteamAdapter


class FakeLocator:
    """Simulate a Playwright locator without a real browser."""

    def __init__(self, text=""):
        self.text = text
        self.filled_value = None
        self.click_count = 0

    async def fill(self, value):
        self.filled_value = value

    async def click(self):
        self.click_count += 1

    async def inner_text(self):
        return self.text


class FakeResponse:
    """Simulate a response from Steam's redemption endpoint."""

    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

        # Represents the POST request expected by the adapter.
        self.url = (
            "https://store.steampowered.com/"
            "account/ajaxregisterkey/"
        )

        self.request = type(
            "FakeRequest",
            (),
            {"method": "POST"},
        )()
        self.ok = 200 <= status < 400
        self.status = status

    async def json(self):
        return self.payload


class FakeResponseInfo:
    """Simulate Playwright's expect_response context manager."""

    def __init__(self, response):
        self.value = self._get_response(response)

    async def _get_response(self, response):
        return response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False


class FakePage:
    """Provide the response expected by the adapter."""

    def __init__(self, response):
        self.response = response

    def expect_response(self, predicate, timeout=15000):
        # No network request occurs. Return the prepared fake response.
        return FakeResponseInfo(self.response)


class FakeBrowser:
    """Provide the page interface required by SteamAdapter."""

    def __init__(self, response):
        self.steam_page = FakePage(response)


async def run_test(
    name,
    payload,
    expected_status,
    error_text="",
    http_status=200,
):
    """Run one response-classification test."""

    response = FakeResponse(
        payload,
        status=http_status,
    )
    browser = FakeBrowser(response)

    adapter = SteamAdapter(
        browser=browser,
        dry_run=False,
    )

    # Inject fake locators instead of running prepare() against Steam.
    adapter.product_key = FakeLocator()
    adapter.register_button = FakeLocator()
    adapter.error_display = FakeLocator(error_text)

    job = RedemptionJob(
        platform="steam",
        code="AAAA-BBBB-CCCC-DDDD",
        streamer="test-streamer",
    )

    result = await adapter.redeem(job)

    assert result.status == expected_status, (
        f"{name}: expected {expected_status}, "
        f"received {result.status}"
    )

    # Verify that the simulated submission click occurred.
    # This is only a fake locator, not a real Steam button.
    assert adapter.register_button.click_count == 1, (
        f"{name}: expected one simulated click"
    )

    print(f"PASS: {name} -> {result.status}")


async def main():
    print("=" * 60)
    print("STEAM RESPONSE-CLASSIFICATION TESTS")
    print("All browser components and responses are simulated.")
    print("No network requests or real redemptions will occur.")
    print("=" * 60)

    tests = [
        (
            "Successful redemption",
            {"success": 1},
            "SUCCESS",
            "",
        ),
        (
            "Invalid product code",
            {
                "success": 0,
                "purchase_result_details": 14,
            },
            "INVALID_CODE",
            "Simulated invalid code message",
        ),
        (
            "Already activated code",
            {
                "success": 0,
                "purchase_result_details": 15,
            },
            "ALREADY_REDEEMED",
            "",
        ),
        (
            "Rate limited",
            {
                "success": 0,
                "purchase_result_details": 53,
            },
            "RATE_LIMITED",
            "",
        ),
        (
            "Unrecognized failure",
            {
                "success": 0,
                "purchase_result_details": 999,
            },
            "UNKNOWN",
            "",
        ),
    ]

    # Run the five standard response-classification tests.
    for name, payload, expected_status, error_text in tests:
        await run_test(
            name=name,
            payload=payload,
            expected_status=expected_status,
            error_text=error_text,
        )

    # Run the HTTP failure test exactly once, after the loop.
    await run_test(
        name="HTTP 500 despite success JSON",
        payload={"success": 1},
        expected_status="UNKNOWN",
        http_status=500,
    )

    print()
    print("=" * 60)
    print("ALL SIX TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())