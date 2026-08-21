from ..module import Mod, register
from .. import device
from ..formats import viewstyle

APP = "/system/vendor/sony/bin/HgrmMediaPlayerApp"

DISCLAIMER = (
    "⚠️  WARNING — READ BEFORE APPLYING\n"
    "This rewrites the system UI application (HgrmMediaPlayerApp). A bad build can bootloop or "
    "otherwise DAMAGE your Walkman's OS. It requires Walkman One firmware and root. A backup is "
    "made and Revert restores it, but flashing system files is inherently risky and recovery may "
    "require reinstalling the firmware. USE AT YOUR OWN RISK — the author accepts NO liability for "
    "any damage, data loss, or bricking. By applying you accept full responsibility."
)


@register
class UIThemer(Mod):
    id = "ui_themer"
    name = "UI Text Themer"
    category = "Theme"
    risk = "high"
    status = "built"
    description = (
        "Recolor the player's MAIN UI text and background to ANY colors you choose — each element "
        "individually (primary/secondary/disabled text, the hi-res highlight, and the background). "
        "Leave a color blank to keep it as-is. Works by redirecting the QML palette bindings "
        "(viewstyle.textcolor.*/bgcolor.D1) that every screen reads, so it reaches the text the icon "
        "recolor can't. Backed up + md5-verified; reboot to see it; Revert restores the previous app.\n\n"
        + DISCLAIMER
    )

    # token slots (redirect a viewstyle.* binding).  (field name, qml token, label)
    SLOTS = [
        ("primary_text",   viewstyle.TOKENS["primary_text"],   "Primary text"),
        ("secondary_text", viewstyle.TOKENS["secondary_text"], "Secondary text"),
        ("disabled_text",  viewstyle.TOKENS["disabled_text"],  "Disabled text"),
        ("highlight_text", viewstyle.TOKENS["highlight_text"], "Hi-res highlight"),
        ("vivid_text",     viewstyle.TOKENS["vivid_text"],     "Vivid text"),
        ("extra_text",     viewstyle.TOKENS["extra_text"],     "Emphasis text"),
        ("background",     viewstyle.TOKENS["background"],      "Background"),
        ("vivid_bg",       viewstyle.TOKENS["vivid_bg"],        "Vivid background"),
    ]
    # hardcoded-hex slots (swap a literal value).  (field name, stock hex, label)
    HEX_SLOTS = [
        ("spectrum_low",  viewstyle.HARDCODED["spectrum_low"],  "Spectrum gradient (low)"),
        ("spectrum_high", viewstyle.HARDCODED["spectrum_high"], "Spectrum gradient (high)"),
    ]

    def inputs(self):
        fields = []
        for name, _tok, label in self.SLOTS:
            fields.append({"name": name, "type": "color", "label": label + "  (blank = keep)",
                           "default": "#cc516c" if name == "primary_text" else ""})
        for name, _hex, label in self.HEX_SLOTS:
            fields.append({"name": name, "type": "color", "label": label + "  (blank = keep)",
                           "default": ""})
        return fields

    def _maps(self, config):
        """Split the non-blank slots into a viewstyle-token colormap and a hardcoded-hex hexmap.
        Invalid hex is passed through so viewstyle.patch() raises a clear error (catches typos)."""
        cmap, hmap = {}, {}
        for name, tok, _label in self.SLOTS:
            v = (config.get(name) or "").strip()
            if v and v.lower() != "keep":
                cmap[tok] = v
        for name, stock_hex, _label in self.HEX_SLOTS:
            v = (config.get(name) or "").strip()
            if v and v.lower() != "keep":
                hmap[stock_hex] = v
        if not cmap and not hmap:
            raise ValueError("pick at least one color (all slots are blank)")
        return cmap, hmap

    def _build(self, config, ctx):
        data = device.pull_file(APP)
        cmap, hmap = self._maps(config)
        available = viewstyle.scan(data)
        for tok in cmap:
            if available.get(tok, 0) == 0:
                raise RuntimeError("token %s not found in this app build — cannot theme" % tok)
        new, stats = viewstyle.patch(data, cmap, hmap)
        return new, stats, cmap, hmap

    def preview(self, config, ctx):
        _new, stats, cmap, hmap = self._build(config, ctx)
        lines = ["%s → %s  (%d)" % (t, c, stats["tokens"].get(t, 0)) for t, c in cmap.items()]
        lines += ["%s → %s  (%d)" % (o, n, stats["tokens"].get(o, 0)) for o, n in hmap.items()]
        lines.append("blobs rewritten: %d   size: %d (unchanged)" % (stats["blobs"], stats["size"]))
        return {"kind": "text", "data": "\n".join(lines) + "\n\n" + DISCLAIMER}

    def apply(self, config, ctx):
        new, stats, cmap, hmap = self._build(config, ctx)
        ctx.ledger.backup_file(self.id, APP)
        device.install_file(new, APP, mode="755")
        total = sum(stats["tokens"].values())
        return ("UI themed: %d colors across %d blobs recolored. Reboot (or kill the player) to "
                "see it. Revert restores the previous app." % (total, stats["blobs"]))

    def revert(self, ctx):
        ctx.ledger.restore(self.id)
