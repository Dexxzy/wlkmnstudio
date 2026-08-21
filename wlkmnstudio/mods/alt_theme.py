from ..module import Mod, register
from .. import device
from ..formats import viewstyle

APP = "/system/vendor/sony/bin/HgrmMediaPlayerApp"

# The player has two palettes: styleProperties["normal"] and ["reverse"] (the reverse scheme the
# language-study screens use). viewstyle reads styleProperties[mode], and QML sets mode to "normal"
# in 8 places + the default declaration. Flip them all to "reverse" -> the whole UI uses palette #2.
SWAP = {
    'viewstyle.mode = "normal"':      'viewstyle.mode = "reverse"',
    'property string mode: "normal"': 'property string mode: "reverse"',
}


@register
class AltTheme(Mod):
    id = "alt_theme"
    name = "Alternate Theme"
    category = "Theme"
    risk = "med"
    status = "prototype"
    description = ("Switch the ENTIRE UI to the firmware's second palette — the 'reverse' color scheme "
                   "the language-study screens use — in one toggle. EXPERIMENTAL: the exact look is "
                   "whatever that palette defines (it's a valid, complete scheme, so nothing breaks), and "
                   "it's fully reversible — Revert restores the normal theme. Pair with the UI Text "
                   "Themer if you want to hand-pick colors instead.")

    def _count(self, data):
        return sum(sum(o.count(k.encode()) for k in SWAP)
                   for _, _, o in viewstyle.iter_blobs(data))

    def preview(self, config, ctx):
        n = self._count(device.pull_file(APP))
        if n == 0:
            return {"kind": "text", "data": "Already on the alternate theme (or the app was modified). "
                    "Use Revert to return to the normal theme."}
        return {"kind": "text", "data": "Will switch the UI to the alternate 'reverse' palette "
                "(%d mode sites). Reboot / restart the player to see it; Revert restores normal." % n}

    def apply(self, config, ctx):
        data = device.pull_file(APP)
        if self._count(data) == 0:
            return "Already on the alternate theme — nothing to do."
        new, stats = viewstyle.patch(data, strmap=SWAP)
        ctx.ledger.backup_file(self.id, APP)
        device.install_file(new, APP, mode="755")
        return ("Alternate theme applied across %d blob(s). Reboot / restart the player. "
                "Revert restores the normal theme." % stats["blobs"])

    def revert(self, ctx):
        ctx.ledger.restore(self.id)
