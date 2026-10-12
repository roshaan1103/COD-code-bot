import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DetectedCode:
    """
    Represents a detected giveaway code.
    """

    platform: str
    code: str


# Platform aliases are matched case-insensitively.
#
# Short aliases such as BN require a colon.
# Longer aliases may use a colon or whitespace as a separator.
PLATFORM_ALIASES = {
    "steam": "steam",
    "battle.net": "battle.net",
    "battle net": "battle.net",
    "battlenet": "battle.net",
    "bnet": "battle.net",
    "bn": "battle.net",
}

# Longer aliases are checked first to prevent a shorter alias
# from taking precedence over a more specific one.
_ALIAS_PATTERN = "|".join(
    re.escape(alias)
    for alias in sorted(PLATFORM_ALIASES, key=len, reverse=True)
)

PLATFORM_PATTERN = re.compile(
    rf"(?<!\w)(?P<alias>{_ALIAS_PATTERN})(?!\w)"
    rf"\s*(?P<separator>:)",
    re.IGNORECASE,
)

# Explicit punctuation that can end a code candidate.
# A hyphen is deliberately excluded because it may be part of a code.
CODE_DELIMITERS = ",;|"


def _normalize_platform(alias: str) -> str:
    """
    Convert a recognized platform alias to its canonical name.
    """

    normalized_alias = re.sub(r"\s+", " ", alias.strip().lower())
    return PLATFORM_ALIASES[normalized_alias]


def _extract_candidate(segment: str) -> Optional[str]:
    """
    Extract a candidate from the text following a platform label.

    The candidate ends at:
    - whitespace,
    - a configured delimiter,
    - or the end of the segment.

    No fixed length or grouping format is required.
    """

    segment = segment.strip()

    if not segment:
        return None

    # A code candidate ends at the first whitespace or explicit
    # delimiter. This intentionally does not validate the code's
    # length or character grouping.
    candidate_match = re.match(
        r"[^ \t\r\n,;|]+",
        segment,
    )

    if not candidate_match:
        return None

    candidate = candidate_match.group(0).strip()

    # Reject punctuation-only candidates.
    if not candidate or not any(character.isalnum() for character in candidate):
        return None

    return candidate.upper()


def detect_codes(text: str) -> list[DetectedCode]:
    """
    Detect one or more platform/code pairs in a chat message.

    Examples:
        Steam: ABCDE-BBBBB-CCCCC
        Battle.net: example-code
        BNet: example-code
        BN: example-code

    The sender's authorization must be checked separately by the
    message handler before detected codes are queued.
    """

    if not text:
        return []

    platform_matches = list(PLATFORM_PATTERN.finditer(text))

    if not platform_matches:
        return []

    detected_codes: list[DetectedCode] = []

    for index, platform_match in enumerate(platform_matches):
        # Only inspect the text between this label and the next
        # recognized platform label.
        segment_start = platform_match.end()

        if index + 1 < len(platform_matches):
            segment_end = platform_matches[index + 1].start()
        else:
            segment_end = len(text)

        segment = text[segment_start:segment_end]

        # Remove leading whitespace and optional common separators.
        segment = segment.lstrip(" \t\r\n:=")

        candidate = _extract_candidate(segment)

        if candidate is None:
            continue

        detected_codes.append(
            DetectedCode(
                platform=_normalize_platform(
                    platform_match.group("alias")
                ),
                code=candidate,
            )
        )

    return detected_codes


def detect_code(text: str) -> Optional[DetectedCode]:
    """
    Backward-compatible helper returning the first detected code.

    Existing code that expects a single DetectedCode can continue
    using this function.
    """

    codes = detect_codes(text)

    return codes[0] if codes else None