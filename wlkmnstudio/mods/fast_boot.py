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

    def _state(self):
        """Inspect the three components on-device. Returns (svc_bytes, gated, has_watcher, hooked).
        `gated` is True/False/None (None = unrecognized firmware)."""
        svc = device.pull_file(SERVICE)
        gated = mediastore.is_gated(svc)
        has_watcher = bool(device.shell("ls %s 2>/dev/null" % mediastore.WATCHER_PATH).strip())
        hooked = "wlkmn_scanwatch" in device.pull_file(mediastore.HOOK_TARGET).decode("utf-8", "replace")
        return svc, gated, has_watcher, hooked

    def preview(self, config, ctx):
        svc, gated, has_watcher, hooked = self._state()
        if gated is None:
            try:
                mediastore.build_gated_service(svc)     # raises with a clear reason
            except ValueError as e:
                return {"kind": "text", "data": "Cannot apply on this device:\n  %s" % e}
        if gated and has_watcher and hooked:
            return {"kind": "text", "data": "Already fully installed (service gated, watcher + boot hook present)."}
        todo = []
        if not gated:
            g = mediastore.build_gated_service(svc)
            todo.append("marker-gated libMediaStoreService.so (%d bytes, md5 %s…)"
                        % (len(g), device.md5_bytes(g)[:8]))
        if not has_watcher:
            todo.append("boot watcher  %s" % mediastore.WATCHER_PATH)
        if not hooked:
            todo.append("hook in       %s" % mediastore.HOOK_TARGET)
        return {"kind": "text", "data":
                "Will install:\n  • " + "\n  • ".join(todo) +
                "\n\nReboot after applying: boot is instant (no 'Creating Database'); a USB transfer "
                "still triggers a real scan.\n\n" + DISCLAIMER}

    def apply(self, config, ctx):
        svc, gated, has_watcher, hooked = self._state()
        if gated is None:
            # unrecognized firmware — build_gated_service raises a clear message; nothing written
            mediastore.build_gated_service(svc)
        did = []
        # 1) patched media service — only when currently stock (so the ledger backup captures stock)
        if not gated:
            ctx.ledger.backup_file(self.id + "_service", SERVICE)
            device.install_file(mediastore.build_gated_service(svc), SERVICE, mode="755")
            did.append("service")
        # 2) the /contents watcher (new file — revert removes it)
        if not has_watcher:
            device.install_file(mediastore.WATCHER_SCRIPT.encode("utf-8"), mediastore.WATCHER_PATH, mode="755")
            did.append("watcher")
        # 3) boot hook — back up buildinfo only while it's still unhooked (so the backup is stock)
        if not hooked:
            ctx.ledger.backup_file(self.id + "_hook", mediastore.HOOK_TARGET)
            cur = device.pull_file(mediastore.HOOK_TARGET)
            device.install_file(mediastore.hook_buildinfo(cur), mediastore.HOOK_TARGET, mode="755")
            did.append("hook")
        if not did:
            return "Fast Boot already fully installed. Nothing to do."
        return ("Fast Boot installed (%s). REBOOT to activate: the 'Creating Database' screen is "
                "skipped on boot; adding music over USB still scans automatically. Revert restores "
                "stock." % " + ".join(did))

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
