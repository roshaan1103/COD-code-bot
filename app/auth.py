import json
from pathlib import Path

import httpx

from app.config import (
    TWITCH_CLIENT_ID,
    TWITCH_CLIENT_SECRET,
    TWITCH_REDIRECT_URI,
)


TOKEN_URL = "https://id.twitch.tv/oauth2/token"
VALIDATE_URL = "https://id.twitch.tv/oauth2/validate"

TOKEN_FILE = Path(__file__).resolve().parent.parent / "twitch_tokens.json"


def exchange_authorization_code(code: str) -> dict:
    """
    Exchange a Twitch authorization code for an access token
    and refresh token.
    """

    data = {
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": TWITCH_REDIRECT_URI,
    }

    response = httpx.post(
        TOKEN_URL,
        data=data,
        timeout=15.0,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Twitch token exchange failed: "
            f"{response.status_code} - {response.text}"
        )

    tokens = response.json()

    required_fields = [
        "access_token",
        "refresh_token",
        "expires_in",
        "scope",
        "token_type",
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in tokens
    ]

    if missing_fields:
        raise RuntimeError(
            f"Twitch token response is missing fields: {missing_fields}"
        )

    return tokens


def validate_access_token(access_token: str) -> dict:
    """
    Validate a Twitch access token and return information
    about the authenticated Twitch user.
    """

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = httpx.get(
        VALIDATE_URL,
        headers=headers,
        timeout=15.0,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Twitch token validation failed: "
            f"{response.status_code} - {response.text}"
        )

    return response.json()


def save_tokens(tokens: dict) -> None:
    """
    Save Twitch tokens to a local file.
    """

    with TOKEN_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            tokens,
            file,
            indent=2,
        )

    print(f"Tokens saved to: {TOKEN_FILE}")


def load_tokens() -> dict:
    """
    Load previously saved Twitch tokens.
    """

    if not TOKEN_FILE.exists():
        raise FileNotFoundError(
            f"Token file not found: {TOKEN_FILE}"
        )

    with TOKEN_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)