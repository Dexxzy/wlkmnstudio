import datetime
from ..module import Mod, register
from .. import device


@register
class ClockFix(Mod):
    id = "clock_fix"
    name = "Clock Fix (DB-rebuild)"
    category = "QOL"
    status = "built"
    risk = "low"
    description = ("KILLS the #1 gripe — the boot-time database rebuild. The A50 clock sits at the 2018 "
                   "firmware date, so the genesys-db scanner sees your SD tracks (2024-2026 dates) as "
                   "'from the future' and re-imports the whole library on every boot. This sets the "
                   "clock + RTC to your computer's time; the RTC holds it across reboots → the scan goes "
                   "incremental and boot is dramatically faster. Verified: clock persisted a reboot, boot "
                   "went 'leagues faster'. (If a unit's RTC cell is dead and it reverts, a boot-script "
                   "persist via prepare_contentroot.sh is the fallback.)")

    def _now(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def preview(self, config, ctx):
        dev = device.shell("date").strip()
        return {"kind": "text", "data": f"device clock : {dev}\ncomputer now : {self._now()}\n"
                                        f"(if the device is years behind, that's the DB-rebuild cause)"}

    def apply(self, config, ctx):
        now = self._now()
        device.shell(f'busybox date -s "{now}" 2>/dev/null; busybox hwclock -w 2>/dev/null; true')
        got = device.shell("date").strip()
        return (f"clock set to {got} (+ written to RTC). Reboot and check: if the boot is faster and the "
                f"clock stays current, the DB-rebuild is fixed. If it reverts to 2018, the RTC cell is "
                f"weak — a boot-script persist is the next step.")

    def revert(self, ctx):
        return  # a clock has no meaningful 'previous value' to restore
