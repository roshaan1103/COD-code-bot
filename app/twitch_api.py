import httpx

from app.config import TWITCH_CLIENT_ID


TWITCH_API_BASE = "https://api.twitch.tv/helix"


def get_user_by_login(
    access_token: str,
    login: str,
) -> dict:
    """
    Get Twitch user information from a login name.
    """

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-Id": TWITCH_CLIENT_ID,
    }

    response = httpx.get(
        f"{TWITCH_API_BASE}/users",
        headers=headers,
        params={
            "login": login,
        },
        timeout=15.0,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Twitch user lookup failed: "
            f"{response.status_code} - {response.text}"
        )

    data = response.json().get("data", [])

    if not data:
        raise RuntimeError(
            f"Twitch channel not found: {login}"
        )

    return data[0]