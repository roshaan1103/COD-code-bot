import re
from dataclasses import dataclass
from typing import Optional


# Initial giveaway code format:
#
# XXXX-XXXX-XXXX-XXXX
#
# Each X can be an uppercase/lowercase letter or number.
CODE_PATTERN = re.compile(
    r"\b([A-Z0-9]{4}(?:-[A-Z0-9]{4}){3})\b",
    re.IGNORECASE,
)


PLATFORM_PATTERN = re.compile(
    r"\b(steam|battlenet|xbox|playstation)\s*:",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DetectedCode:
    """
    Represents a detected giveaway code.
    """

    platform: str
    code: str


def detect_code(text: str) -> Optional[DetectedCode]:
    """
    Detect a platform and giveaway code from a chat message.

    Expected format:

        Steam:XXXX-XXXX-XXXX-XXXX
        Battlenet:XXXX-XXXX-XXXX-XXXX
        Xbox:XXXX-XXXX-XXXX-XXXX
        PlayStation:XXXX-XXXX-XXXX-XXXX

    Returns:
        DetectedCode if a valid-looking code is found.
        None otherwise.
    """

    if not text:
        return None

    platform_match = PLATFORM_PATTERN.search(text)

    if not platform_match:
        return None

    platform = platform_match.group(1).lower()

    code_match = CODE_PATTERN.search(
        text,
        platform_match.end(),
    )

    if not code_match:
        return None

    code = code_match.group(1).upper()

    return DetectedCode(
        platform=platform,
        code=code,
    )