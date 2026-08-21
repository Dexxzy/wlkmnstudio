from ..module import Mod, register
from .. import device

# nvpflag zones on the NW-A50 (from `nvpflag` usage). Read-only here; writing NVP is dangerous
# (region/calibration/update/loader flags) and deliberately NOT exposed in the beta.
ZONES = [
    ("syi", "system information"),
    ("mid", "model id"),
    ("ctr", "country / region (rflcountry)"),
    ("sku", "SKU (rflsku)"),
    ("ins", "install flag (0x494E5354 = Installed)"),
    ("fup", "firmware update flag (0x70555766 = update mode)"),
    ("hld", "loader hold mode"),
    ("tst", "mp test boot flag"),
    ("gty", "getty (serial console) flag"),
    ("mso", "MSC-only mode flag"),
    ("dgs", "disable GVA boot sound"),
    ("bml", "bluetooth middleware log mode"),
    ("mac", "Ethernet MAC address"),
    ("nvr", "NVRAM initial flag"),
    ("prk", "printk flag"),
    ("fni", "function information"),
    ("sid", "service id"),
]


@register
class NvpFlags(Mod):
    id = "nvp_flags"
    name = "NVP Flags"
    category = "System"
    description = ("Inspect Sony's non-volatile flags (region/SKU, install state, boot sound, BT log "
                   "mode, loader flags…) via `nvpflag`. Read-only — writing NVP can brick region/"
                   "calibration/update state, so writes are intentionally left out of the beta.")
    status = "prototype"
    readonly = True

    def preview(self, config, ctx):
        rows = []
        for zone, desc in ZONES:
            try:
                out = device.shell(f"nvpflag {zone} 2>/dev/null").strip().splitlines()
                val = out[0].strip() if out else "?"
            except Exception:
                val = "err"
            rows.append(f"  {zone}  {val:<14} {desc}")
        return {"kind": "text", "data": "NVP zones (read-only):\n" + "\n".join(rows)}
