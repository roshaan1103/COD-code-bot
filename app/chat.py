from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ChatMessage:
    """
    Normalized Twitch chat message.
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