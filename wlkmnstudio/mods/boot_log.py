from ..module import Mod, register
from .. import device

LOG = "/contents/CFW/boot_log.txt"


@register
class BootLog(Mod):
    id = "boot_log"
    name = "Boot Log"
    category = "QOL"
    status = "built"
    readonly = True
    description = ("Read Walkman One's boot log (/contents/CFW/boot_log.txt) — confirms which "
                   "settings.txt options were applied at the last boot (sound signature, region, "
                   "icon color, external tuning status, etc.). The place to check if a setting "
                   "didn't take.")

    def preview(self, config, ctx):
        try:
            txt = device.pull_file(LOG).decode("utf-8", "replace")
        except Exception as e:
            return {"kind": "text", "data": f"boot_log.txt not readable: {e}"}
        lines = [l for l in txt.splitlines() if l.strip()]
        tail = lines[-45:] if len(lines) > 45 else lines
        return {"kind": "text", "data": "\n".join(tail)}
