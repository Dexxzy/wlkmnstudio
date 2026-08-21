import re
from ..module import Mod, register
from .. import device

SETTINGS = "/contents/CFW/settings.txt"

# key, label, [(value, human_label)]
OPTIONS = [
    ("SIG", "Sound signature", [("0", "Neutral"), ("1", "Warm (Midnight)"),
                                ("2", "Bright (Dawn)"), ("3", "WM1Z")]),
    ("COL", "Home icon color", [("0", "Default (gray)"), ("1", "Peach"), ("2", "Red"),
                                ("3", "Blue"), ("4", "Green")]),
    ("GMD", "Gain mode", [("0", "Normal"), ("1", "Lower gain")]),
    ("DIM", "DAC init mode", [("0", "Normal"), ("1", "Alternate")]),
    ("PMV", "Plus-mode version", [("2", "v2"), ("1", "v1")]),
    ("PMD", "Plus mode by default", [("0", "Off"), ("1", "On")]),
    ("REM", "Show BT remote option", [("0", "Off"), ("1", "On")]),
    ("REG", "Region", [(r, r) for r in ("J", "U", "U2", "U3", "CA", "CEV", "CE7", "CEW",
                                        "CEW2", "CN", "KR", "E", "MX", "E2", "MX3", "TW")]),
]


@register
class WM1Settings(Mod):
    id = "wm1_settings"
    name = "Walkman One Settings"
    category = "System"
    description = ("GUI for Walkman One's config file (/contents/CFW/settings.txt): sound signature, "
                   "region, gain, DAC init, home-icon color, Plus mode, BT remote. Safe text config — "
                   "a bad value just falls back to the firmware default. Reboot to apply. NOTE: changing "
                   "the sound SIGNATURE also needs the matching external tuning applied from a PC.")
    status = "built"
    risk = "low"

    def inputs(self):
        return [{"name": k, "type": "choice", "label": lbl, "default": opts[0][0], "options": opts}
                for k, lbl, opts in OPTIONS]

    def _current(self):
        try:
            return device.pull_file(SETTINGS).decode("utf-8", "replace")
        except Exception:
            return ""

    def preview(self, config, ctx):
        txt = self._current()
        if not txt.strip():
            return {"kind": "text", "data": "settings.txt not readable (is /contents mounted? Mass Storage off?)"}
        rows = []
        for k, lbl, _ in OPTIONS:
            m = re.search(rf"(?m)^{k}=(\S*)", txt)
            rows.append(f"  {k:4} {lbl:22} = {m.group(1) if m else '(default)'}")
        return {"kind": "text", "data": "current Walkman One settings:\n" + "\n".join(rows)}

    def apply(self, config, ctx):
        txt = self._current()
        if not txt.strip():
            raise RuntimeError("settings.txt not found/empty — turn off Mass Storage and check /contents/CFW")
        ctx.ledger.backup_file(self.id, SETTINGS)
        changed = []
        for k, _, _ in OPTIONS:
            if k in config:
                txt, n = re.subn(rf"(?m)^{k}=\S*", f"{k}={config[k]}", txt)
                if n:
                    changed.append(f"{k}={config[k]}")
        device.install_file(txt.encode("utf-8"), SETTINGS, mode="644")
        return f"updated {', '.join(changed) if changed else '(nothing)'} — reboot to apply"

    def revert(self, ctx):
        ctx.ledger.restore(self.id)
