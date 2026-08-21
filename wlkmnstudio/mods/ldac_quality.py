from ..module import Mod, register
from .. import device
from ..formats import binpatch

LIB = "/system/lib/libldacBTBC.so"


@register
class LdacQuality(Mod):
    id = "ldac_quality"
    name = "LDAC 990 (no downgrade)"
    category = "Audio"
    risk = "med"
    status = "prototype"
    description = (
        "Force LDAC toward its highest quality (990 kbps) and stop the adaptive bitrate (ABR) engine "
        "from auto-downgrading. LDAC's ABR calls an internal 'lower quality' step on a congested link; "
        "this patch neutralizes ONLY that downgrade direction (the 'raise quality' path still works), so "
        "the codec ramps up to 990 and never drops. One-instruction, reversible patch to "
        "libldacBTBC.so (a codec lib, not the UI app — no bootloop risk).\n\n"
        "Only affects LDAC headphones/speakers. On a weak/2.4GHz-crowded link, forcing 990 can cause "
        "audio dropouts — that's the trade-off. EXPERIMENTAL: verify with real LDAC gear (the BT Monitor "
        "can show the live bitrate). Revert restores stock adaptive behavior."
    )

    # ldac_alter_qmode_priority validity gate:  cmp r1,#0 ; beq.w <invalid>
    # r1 = direction (+1 raise / -1 lower). Changing beq.w -> ble.w (signed <=0) also rejects the
    # -1 (downgrade) call, while +1 (raise) still passes. Only the condition field changes.
    FIND = bytes.fromhex("002900f08780")   # cmp r1,#0 ; beq.w
    REPL = bytes.fromhex("002940f38780")   # cmp r1,#0 ; ble.w

    def inputs(self):
        return []      # a straight toggle: Apply = force 990 / no downgrade, Revert = stock

    def _state(self, data):
        if data.count(self.REPL):
            return "patched"
        if data.count(self.FIND):
            return "stock"
        return "unknown"

    def preview(self, config, ctx):
        data = device.pull_file(LIB)
        st = self._state(data)
        msg = {
            "stock":   "LDAC ABR is STOCK (adaptive — can drop to 660/330). Apply forces 990 / no downgrade.",
            "patched": "LDAC downgrade is ALREADY disabled (forced 990). Revert restores adaptive.",
            "unknown": "patch site not found — this libldacBTBC.so build differs; not safe to patch.",
        }[st]
        return {"kind": "text", "data": msg}

    def apply(self, config, ctx):
        data = device.pull_file(LIB)
        st = self._state(data)
        if st == "patched":
            return "LDAC 990 already forced — nothing to do."
        if st != "stock":
            raise binpatch.PatchError("LDAC ABR patch site not found (build differs) — aborted")
        new, off = binpatch.patch(data, self.FIND, self.REPL)   # unique-site checked by binpatch
        ctx.ledger.backup_file(self.id, LIB)
        device.install_file(new, LIB, mode="644")
        return (f"LDAC downgrade disabled @0x{off:x} — reboot, reconnect your LDAC device. It will ramp to "
                f"990 kbps and hold. EXPERIMENTAL: confirm with the BT Monitor / a listening test.")

    def revert(self, ctx):
        ctx.ledger.restore(self.id)
