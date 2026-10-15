import winsound

def play_code_detected_alert() -> None:
    """Play a short alert when a new giveaway code is queued."""


    try:
        winsound.Beep(1200, 1500)
        winsound.Beep(1400, 1500)

    except RuntimeError as exc:
        # A sound-device problem should not interrupt redemption.
        print(
            "[SOUND ALERT] Could not play the alert: "
            f"{exc}"
        )

