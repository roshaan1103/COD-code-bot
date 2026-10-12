def is_authorized_sender(tags: dict, broadcaster_id: str) -> bool:
    """
    Allow messages from the broadcaster or moderators.

    Prefer the broadcaster's stable Twitch user ID.
    Moderator status is read from the current message's metadata.
    """
    sender_id = tags.get("user-id", "")

    badges = {
        badge
        for badge in tags.get("badges", "").split(",")
        if badge
    }

    is_broadcaster = (
        sender_id == broadcaster_id
        or "broadcaster/1" in badges
    )

    is_moderator = (
        tags.get("mod", "0") == "1"
        or "moderator/1" in badges
    )

    return is_broadcaster or is_moderator


def run_tests():
    broadcaster_id = "1547458395"

    test_cases = [
        (
            "Broadcaster",
            {
                "user-id": "1547458395",
                "badges": "broadcaster/1",
                "mod": "0",
            },
            True,
        ),
        (
            "Moderator flag",
            {
                "user-id": "815998094",
                "badges": "",
                "mod": "1",
            },
            True,
        ),
        (
            "Moderator badge",
            {
                "user-id": "815998094",
                "badges": "moderator/1",
                "mod": "0",
            },
            True,
        ),
        (
            "Ordinary viewer",
            {
                "user-id": "815998094",
                "badges": "",
                "mod": "0",
            },
            False,
        ),
        (
            "Unknown sender",
            {
                "user-id": "",
                "badges": "",
                "mod": "0",
            },
            False,
        ),
    ]

    failures = 0

    for name, tags, expected in test_cases:
        actual = is_authorized_sender(tags, broadcaster_id)
        passed = actual == expected

        print(
            f"[{'PASS' if passed else 'FAIL'}] "
            f"{name}: expected={expected}, actual={actual}"
        )

        if not passed:
            failures += 1

    print()
    print(f"Results: {len(test_cases) - failures}/{len(test_cases)} passed")

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    run_tests()