from ..module import Mod, register
from .. import device

APP = "/system/vendor/sony/bin/HgrmMediaPlayerApp"


@register
class UIRecolor(Mod):
    id = "ui_recolor"
    name = "UI Accent + Icons"
    category = "Theme"
    description = ("Recolor the home-screen ICONS + the EQ-meter/streaming accent to your color. "
                   "PROVEN-SAFE recipe (verified booting on-device): swaps the DEFAULT icon preset "
                   "(#DDDDDD, COL=0) and the Sony gold accent (#c0a565) — leaving the other 4 icon "
                   "presets DISTINCT (collapsing all 5 to one value bootloops the app). "
                   "Menu/track TEXT is handled separately by the 'UI Text Themer' mod (any color, "
                   "per element) — use both together for a full theme. "
                   "Backed up + md5-verified; reboot to see it; Revert restores stock.")
    risk = "high"          # it's the main UI app — but this exact recipe is verified to boot
    status = "built"
    # (from, keep-distinct): recolor these to the accent; NEVER collapse all 5 icon presets
    ACCENT_SRC = "#c0a565"     # EQ meter peak + streaming text (2×)
    ICON_SRC = "#DDDDDD"       # DEFAULT home-icon preset (COL=0). Others left distinct on purpose.

    def inputs(self):
        return [{"name": "accent", "type": "color", "label": "Accent", "default": "#cc516c"}]

    def _build(self, config, ctx):
        acc = config.get("accent", "#cc516c")
        if len(acc) != 7:
            raise ValueError("accent must be a 7-char #rrggbb hex color")
        data = device.pull_file(APP)
        applied = {}
        for src in (self.ACCENT_SRC, self.ICON_SRC):
            n = data.count(src.encode())
            if n:
                data = data.replace(src.encode(), acc.encode())
                applied[src] = (acc, n)
        if not applied:
            raise RuntimeError("no editable UI colors found — app build differs")
        return data, applied

    def preview(self, config, ctx):
        try:
            _, applied = self._build(config, ctx)
        except RuntimeError as e:
            return {"kind": "text", "data": "%s\n(already recolored on this device, or the app has "
                    "been modified — start from a stock HgrmMediaPlayerApp to recolor)" % e}
        return {"kind": "text", "data": "will recolor " +
                ", ".join(f"{f}→{t} ({n}×)" for f, (t, n) in applied.items()) +
                "\n(icons + accent; use the UI Text Themer for menu/track text)"}

    def apply(self, config, ctx):
        data, applied = self._build(config, ctx)
        ctx.ledger.backup_file(self.id, APP)
        device.install_file(data, APP, mode="755")
        n = sum(v[1] for v in applied.values())
        return f"UI icons + accent recolored ({n} swaps) — reboot to see it (Revert restores stock)"

    def revert(self, ctx):
        ctx.ledger.restore(self.id)
