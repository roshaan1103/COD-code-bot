import os

from dotenv import load_dotenv


load_dotenv()


# Twitch API credentials
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")

TWITCH_REDIRECT_URI = os.getenv(
    "TWITCH_REDIRECT_URI",
    "http://localhost:3000",
)


# Twitch channel configuration.
# An empty TWITCH_CHANNELS value disables Twitch monitoring.
# Multiple channels can be separated by commas.
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


# YouTube configuration.
# An empty YOUTUBE_VIDEO_ID disables YouTube monitoring.
YOUTUBE_VIDEO_ID = os.getenv(
    "YOUTUBE_VIDEO_ID",
    "SU0MbaPdsBk",
).strip()


# Twitch credentials are required only when Twitch is enabled.
if TWITCH_CHANNELS:
    if not TWITCH_CLIENT_ID:
        raise RuntimeError(
            "TWITCH_CLIENT_ID is missing from .env "
            "while Twitch monitoring is enabled."
        )

    if not TWITCH_CLIENT_SECRET:
        raise RuntimeError(
            "TWITCH_CLIENT_SECRET is missing from .env "
            "while Twitch monitoring is enabled."
        )


# At least one platform must be enabled.
if not TWITCH_CHANNELS and not YOUTUBE_VIDEO_ID:
    raise RuntimeError(
        "Both Twitch and YouTube are disabled. "
        "Configure TWITCH_CHANNELS, YOUTUBE_VIDEO_ID, or both."
    )