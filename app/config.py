import os

from dotenv import load_dotenv


load_dotenv()


TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
TWITCH_REDIRECT_URI = os.getenv(
    "TWITCH_REDIRECT_URI",
    "http://localhost:3000",
)


if not TWITCH_CLIENT_ID:
    raise RuntimeError("TWITCH_CLIENT_ID is missing from .env")

if not TWITCH_CLIENT_SECRET:
    raise RuntimeError("TWITCH_CLIENT_SECRET is missing from .env")