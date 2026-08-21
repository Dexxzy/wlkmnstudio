from ..module import Mod, register
from .. import device


@register
class RebootUtil(Mod):
    id = "reboot"
    name = "Reboot / Restart UI"
    category = "System"
    status = "built"
    risk = "low"
    description = ("Reboot the device (needed to apply most mods), or just restart the player UI — "
                   "faster, reloads fonts/assets/config without a full boot. The UI respawns on its "
                   "own. No revert.")

    def inputs(self):
        return [{"name": "action", "type": "choice", "label": "Action", "default": "reboot",
                 "options": [("reboot", "Reboot device"), ("restart_ui", "Restart player UI only")]}]

    def apply(self, config, ctx):
        if config.get("action") == "restart_ui":
            device.shell("busybox pkill HgrmMediaPlayerApp 2>/dev/null || pkill HgrmMediaPlayerApp; true")
            return "restarted the player UI (it respawns automatically — give it a few seconds)"
        device._run(["reboot"])
        return "rebooting the device…"

    def revert(self, ctx):
        return
