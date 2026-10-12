import os

from dotenv import load_dotenv


load_dotenv()


TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")

TWITCH_REDIRECT_URI = os.getenv(
    "TWITCH_REDIRECT_URI",
    "http://localhost:3000",
)

# Comma-separated Twitch channel logins.
# Preserve the existing channel as the default.
_raw_twitch_channels = os.getenv(
    "TWITCH_CHANNELS",
    "dominent_orion",
)

TWITCH_CHANNELS = list(
    dict.fromkeys(
        channel.strip().lstrip("@").lower()
        for channel in _raw_twitch_channels.split(",")
        if channel.strip().lstrip("@")
    )
)


if not TWITCH_CLIENT_ID:
    raise RuntimeError(
        "TWITCH_CLIENT_ID is missing from .env"
    )

if not TWITCH_CLIENT_SECRET:
    raise RuntimeError(
        "TWITCH_CLIENT_SECRET is missing from .env"
    )

if not TWITCH_CHANNELS:
    raise RuntimeError(
        "TWITCH_CHANNELS must contain at least one channel login"
    )

