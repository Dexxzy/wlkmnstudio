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
        ("separator",     viewstyle.HARDCODED["separator"],     "Separator / divider lines"),
    ]

    T = viewstyle.TOKENS
    # curated one-click palettes: (colormap {qml token: hex}, hexmap {stock hex: hex}). Cohesive,
    # legibility-checked schemes so users get a good look without picking colors.
    PRESETS = {
        "crimson": ({T["primary_text"]: "#CC516C", T["secondary_text"]: "#B07782",
                     T["disabled_text"]: "#6E4149", T["vivid_text"]: "#D96A83",
                     T["extra_text"]: "#B07782", T["background"]: "#22242A", T["vivid_bg"]: "#2A2D35"},
                    {"#143a8b": "#6E2637", "#21d6cd": "#CC516C", "#222222": "#33262A"}),
        "mono":    ({T["primary_text"]: "#E6E6E6", T["secondary_text"]: "#A8A8A8",
                     T["disabled_text"]: "#6A6A6A", T["vivid_text"]: "#F0F0F0",
                     T["extra_text"]: "#C8C8C8", T["background"]: "#1A1A1A", T["vivid_bg"]: "#252525"},
                    {"#143a8b": "#3A3A3A", "#21d6cd": "#D8D8D8", "#222222": "#2A2A2A"}),
        "ocean":   ({T["primary_text"]: "#7FD4E0", T["secondary_text"]: "#5A9AA8",
                     T["disabled_text"]: "#3C5A64", T["vivid_text"]: "#9EE6F0",
                     T["extra_text"]: "#6FB8C4", T["background"]: "#0E1E26", T["vivid_bg"]: "#16303A"},
                    {"#222222": "#16262C"}),   # ocean keeps the stock blue/teal spectrum
        "amber":   ({T["primary_text"]: "#E6B45C", T["secondary_text"]: "#B08A44",
                     T["disabled_text"]: "#6E5525", T["vivid_text"]: "#F2C878",
                     T["extra_text"]: "#C89A50", T["background"]: "#201C12", T["vivid_bg"]: "#2A2418"},
                    {"#143a8b": "#5A3A10", "#21d6cd": "#E6B45C", "#222222": "#2A2418"}),
    }

    def inputs(self):
        fields = [{"name": "preset", "type": "choice", "label": "Theme preset", "default": "custom",
                   "options": [("custom", "Custom (use the colors below)"), ("crimson", "Crimson"),
                               ("mono", "Mono"), ("ocean", "Ocean"), ("amber", "Amber")]}]
        for name, _tok, label in self.SLOTS:
            fields.append({"name": name, "type": "color", "label": label + "  (blank = keep)",
                           "default": "#cc516c" if name == "primary_text" else ""})
        for name, _hex, label in self.HEX_SLOTS:
            fields.append({"name": name, "type": "color", "label": label + "  (blank = keep)",
                           "default": ""})
        return fields

    def _maps(self, config):
        """Build the viewstyle-token colormap + hardcoded-hex hexmap. A chosen preset wins over the
        individual slots; 'custom' uses the slots. Invalid hex is passed through so viewstyle.patch()
        raises a clear error (catches typos)."""
        preset = (config.get("preset") or "custom").strip().lower()
        if preset in self.PRESETS:
            cmap, hmap = self.PRESETS[preset]
            return dict(cmap), dict(hmap)
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
