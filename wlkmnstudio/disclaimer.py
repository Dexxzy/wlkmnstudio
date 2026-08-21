"""Shared risk disclaimer + first-run acceptance, used by both the GUI and the CLI so the
two front-ends stay consistent (accepting in either one counts)."""
import os

ACCEPT_FLAG = os.path.expanduser("~/.wlkmnstudio/accepted")

RISK_TEXT = (
    "WLKMN Studio modifies system files and partitions on your rooted Sony Walkman. "
    "Flashing can bootloop or otherwise damage your device.\n\n"
    "Every change is backed up and md5-verified and can be reverted — but recovery may still "
    "require reinstalling Walkman One, and some actions carry inherent risk.\n\n"
    "This software is provided AS IS, with NO WARRANTY. You use it entirely AT YOUR OWN RISK. "
    "The authors accept NO liability for any damage, data loss, or bricking.\n\n"
    "It requires Walkman One firmware on a rooted device and is not affiliated with or endorsed by Sony.\n\n"
    "By continuing you confirm that you understand these risks and accept full responsibility."
)

# One-line reminder shown before each flashing action.
SHORT = ("Flashing system files is inherently risky — a bad write can bootloop your device. "
         "The original is backed up and Revert restores it.")


def accepted():
    return os.path.exists(ACCEPT_FLAG)


def mark_accepted():
    try:
        os.makedirs(os.path.dirname(ACCEPT_FLAG), exist_ok=True)
        with open(ACCEPT_FLAG, "w") as f:
            f.write("accepted\n")
    except OSError:
        pass
