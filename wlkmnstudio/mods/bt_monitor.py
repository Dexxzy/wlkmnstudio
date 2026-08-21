from ..module import Mod, register
from .. import monitor


@register
class BTMonitor(Mod):
    id = "bt_monitor"
    name = "BT Monitor"
    category = "Audio"
    description = ("Live read of mtkbt's RTP session (from /proc/mem) — shows whether BT audio is "
                   "streaming and whether the AirPods timestamp fix is active. Read-only diagnostic; "
                   "play audio to a Bluetooth sink first to get a live reading.")
    status = "prototype"
    readonly = True

    def preview(self, config, ctx):
        return {"kind": "text", "data": monitor.format_status(monitor.bt_status())}
