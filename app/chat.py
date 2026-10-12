from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ChatMessage:
    """
    Normalized Twitch chat message.

    Role metadata is used to determine whether a message
    is eligible for giveaway-code detection.
    """

    event_id: str
    broadcaster_id: str
    broadcaster_login: str
    broadcaster_name: str

    chatter_id: str
    chatter_login: str
    chatter_name: str

    text: str
    received_at: datetime

    # Whether Twitch identifies the sender as a moderator.
    # Defaults to False for compatibility with existing callers.
    is_moderator: bool = False

