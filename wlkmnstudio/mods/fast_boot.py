from ..module import Mod, register
from .. import device
from ..formats import mediastore

SERVICE = "/system/vendor/sony/lib/libMediaStoreService.so"

DISCLAIMER = (
    "⚠️  WARNING — READ BEFORE APPLYING\n"
    "This patches the system media service (libMediaStoreService.so) and adds a boot script. "
    "A bad flash can hang on 'Creating Database' or fail to boot. It requires Walkman One firmware "
    "and root. Everything is backed up and md5-verified and Revert restores stock, but recovery may "
    "require reflashing the firmware. USE AT YOUR OWN RISK — the author accepts NO liability."
)


@register
class FastBoot(Mod):
    id = "fast_boot"
    name = "Fast Boot (skip DB scan)"
    category = "QOL"
    risk = "high"
    status = "built"
    description = (
        "Kill the 'Creating Database' scan that blocks EVERY boot — the #1 A50/A55 complaint — "
        "WITHOUT losing USB library scanning. Marker-gates the scan worker so a normal boot skips "
        "the /contents crawl (instant, no popup), while a tiny watcher re-enables it automatically "
        "after a USB transfer (it sees /contents unmount, drops a marker, the next scan crawls and "
        "indexes your new music). Installs a patched libMediaStoreService.so + a boot watcher + a "
        "hook in buildinfo.sh; all backed up, Revert restores stock.\n\n" + DISCLAIMER
    )

    def _build(self, ctx):
        """Pull the device's service and produce the marker-gated build. Raises ValueError on an
        unrecognized firmware so apply() aborts before writing anything."""
        stock = device.pull_file(SERVICE)
        if mediastore.is_gated(stock):
            return None                          # already patched on-device
        return mediastore.build_gated_service(stock)

    def preview(self, config, ctx):
        try:
            gated = self._build(ctx)
        except ValueError as e:
            return {"kind": "text", "data": "Cannot apply on this device:\n  %s" % e}
        if gated is None:
            return {"kind": "text", "data": "Already installed on this device (service is marker-gated)."}
        return {"kind": "text", "data":
                "Ready. Will install:\n"
                "  • marker-gated libMediaStoreService.so (%d bytes, md5 %s…)\n"
                "  • boot watcher  %s\n"
                "  • hook in       %s\n\n"
                "Reboot after applying: boot is instant (no 'Creating Database'); a USB transfer "
                "still triggers a real scan.\n\n%s"
                % (len(gated), device.md5_bytes(gated)[:8], mediastore.WATCHER_PATH,
                   mediastore.HOOK_TARGET, DISCLAIMER)}

    def apply(self, config, ctx):
        gated = self._build(ctx)                  # may raise -> nothing written
        if gated is None:
            return "Fast Boot already installed (service already marker-gated). Nothing to do."
        # 1) patched media service
        ctx.ledger.backup_file(self.id + "_service", SERVICE)
        device.install_file(gated, SERVICE, mode="755")
        # 2) the /contents watcher (new file — revert removes it)
        device.install_file(mediastore.WATCHER_SCRIPT.encode("utf-8"), mediastore.WATCHER_PATH, mode="755")
        # 3) boot hook that launches the watcher
        ctx.ledger.backup_file(self.id + "_hook", mediastore.HOOK_TARGET)
        cur = device.pull_file(mediastore.HOOK_TARGET)
        device.install_file(mediastore.hook_buildinfo(cur), mediastore.HOOK_TARGET, mode="755")
        return ("Fast Boot installed (service + watcher + boot hook). REBOOT to activate: the "
                "'Creating Database' screen is skipped on boot; adding music over USB still scans "
                "automatically. Revert restores stock.")

    def revert(self, ctx):
        ctx.ledger.restore(self.id + "_service")     # stock libMediaStoreService.so (remounts rw)
        ctx.ledger.restore(self.id + "_hook")        # stock buildinfo.sh
        # Delete the watcher script + marker in a command with NO pkill — `pkill -f wlkmn_scanwatch`
        # matches its OWN shell (this string is in its cmdline) and would kill it before the rm runs.
        device.shell("mount -o rw,remount /system 2>/dev/null; "
                     "busybox rm -f %s /data/wlkmn_rescan 2>/dev/null; sync; true"
                     % mediastore.WATCHER_PATH)
        # Then stop the still-running watcher (separate call; the rm has already completed).
        device.shell("busybox pkill -f wlkmn_scanwatch 2>/dev/null; true")
