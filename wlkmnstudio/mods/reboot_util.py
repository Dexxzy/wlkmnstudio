from ..module import Mod, register
from .. import device


@register
class RebootUtil(Mod):
    id = "reboot"
    name = "Reboot / Restart UI"
    category = "System"
    status = "built"
    risk = "low"
    description = ("Reboot the device (needed to apply most mods), or ask the system to relaunch just "
                   "the player UI to reload fonts/assets/config. The UI restart goes through the "
                   "system's own service manager (init) rather than force-killing the app. On most "
                   "firmware it's quicker than a full reboot; note the player is watchdog-protected, so "
                   "some builds do a quick full restart to bring it back. Either way the screen blanks "
                   "for a moment and the USB link briefly drops. No revert.")

    def inputs(self):
        return [{"name": "action", "type": "choice", "label": "Action", "default": "reboot",
                 "options": [("reboot", "Reboot device"), ("restart_ui", "Restart player UI only")]}]

    def apply(self, config, ctx):
        if config.get("action") == "restart_ui":
            # The player app (HgrmMediaPlayerApp) is hosted by the "appmgrservice" hagodaemon, which
            # init runs as one of the hagoromoN services. Ask init to restart THAT service, so init
            # cleanly tears down and respawns the whole app process group — far more reliable than
            # SIGKILL'ing the app and hoping its parent brings it back. The service's init name isn't
            # fixed across firmware builds, so discover it from init.hagoromo.rc at runtime.
            svc = device.shell(
                "busybox awk '/^service/ && /appmgrservice/{print $2; exit}' /init.hagoromo.rc"
            ).strip()
            if svc:
                device.shell("setprop ctl.restart %s" % svc)
                return "restarting the player UI (via %s) — back in a few seconds" % svc
            # Unrecognized init layout: fall back to the (proven-working) app kill; its host respawns it.
            device.shell("busybox pkill HgrmMediaPlayerApp 2>/dev/null || pkill HgrmMediaPlayerApp; true")
            return "restarted the player UI (it respawns automatically — give it a few seconds)"
        device._run(["reboot"])
        return "rebooting the device…"

    def revert(self, ctx):
        return
