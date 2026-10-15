import winsound

def play_test_alert() -> None:
    """Play a short, two-tone Windows sound alert."""

    print("[SOUND TEST] Playing alert...")

    winsound.Beep(1200, 1500)
    winsound.Beep(1400, 1500)

    print("[SOUND TEST] Alert finished successfully.")


if __name__== "__main__":
    play_test_alert()
