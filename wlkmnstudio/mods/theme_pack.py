from ..module import Mod, register
from .. import device
from ..formats import viewstyle
from .ui_themer import UIThemer, DISCLAIMER
from .ui_recolor import UIRecolor

APP = "/system/vendor/sony/bin/HgrmMediaPlayerApp"


@register
class ThemePack(Mod):
    id = "theme_pack"
    name = "Theme Packs (1-click look)"
    category = "Theme"
    risk = "high"
    status = "built"
    description = (
        "Recolor the WHOLE interface in one click — pick a look and it applies the matching text, "
        "background, home icons and accent together (what the UI Text Themer + UI Accent mods do, "
        "combined into a single coordinated theme). Great if you just want it to look good without "
        "picking colors. Start from a stock player app for best results (Revert first if you've already "
        "themed). Backed up + md5-verified; reboot to see it; Revert restores stock.\n\n" + DISCLAIMER
    )

    # look -> (UIThemer text-preset key, icon+accent color). The icon color is the look's primary text,
    # so the icons match the menu text.
    PACKS = {
        "crimson": ("crimson", "#CC516C"),
        "mono":    ("mono",    "#E6E6E6"),
        "ocean":   ("ocean",   "#7FD4E0"),
        "amber":   ("amber",   "#E6B45C"),
    }

    def inputs(self):
        return [{"name": "pack", "type": "choice", "label": "Look", "default": "crimson",
                 "options": [("crimson", "Crimson (red/pink)"), ("mono", "Mono (greyscale)"),
                             ("ocean", "Ocean (teal/blue)"), ("amber", "Amber (gold)")]}]

    def _build(self, config, ctx):
        pack = (config.get("pack") or "crimson").strip().lower()
        if pack not in self.PACKS:
            raise ValueError("unknown look '%s'" % pack)
        preset_key, icon_accent = self.PACKS[pack]
        cmap, hmap = UIThemer.PRESETS[preset_key]

        data = device.pull_file(APP)
        # 1) text + background palette (the viewstyle QML rewrite). Size-preserving.
        new, tstats = viewstyle.patch(data, dict(cmap), dict(hmap))
        # 2) home icons + EQ/streaming accent (byte-replace, same proven recipe as UI Accent). Also
        #    size-preserving, and touches different bytes than the palette blobs — safe to compose.
        icons = 0
        for src in (UIRecolor.ACCENT_SRC, UIRecolor.ICON_SRC):
            c = new.count(src.encode())
            if c:
                new = new.replace(src.encode(), icon_accent.encode())
                icons += c
        text_swaps = sum(tstats["tokens"].values())
        return new, text_swaps, icons

    def preview(self, config, ctx):
        try:
            new, text_swaps, icons = self._build(config, ctx)
        except Exception as e:
            return {"kind": "text", "data": "Cannot apply: %s\n(Revert any existing theme first, or "
                    "start from a stock player app.)" % e}
        note = "" if text_swaps else ("\n⚠ no text-palette tokens found — this app is already themed; "
                                      "Revert to stock first for the full look.")
        return {"kind": "text", "data":
                "This look will recolor %d text/background spots + %d icon/accent spots in one go. "
                "Reboot to see it.%s\n\n%s" % (text_swaps, icons, note, DISCLAIMER)}

    def apply(self, config, ctx):
        new, text_swaps, icons = self._build(config, ctx)
        ctx.ledger.backup_file(self.id, APP)
        device.install_file(new, APP, mode="755")
        return ("Theme applied: %d text + %d icon/accent recolors in one pack. Reboot (or restart the "
                "player) to see it. Revert restores the previous app." % (text_swaps, icons))

    def revert(self, ctx):
        ctx.ledger.restore(self.id)
