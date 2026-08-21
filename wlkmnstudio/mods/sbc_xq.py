from ..module import Mod, register
from .. import device
from ..formats import binpatch

MTKBT = "/system/bin/mtkbt"


@register
class SbcXQ(Mod):
    id = "sbc_xq"
    name = "SBC-XQ (bitpool)"
    category = "Audio"
    description = ("Raise the A2DP SBC max bitpool (stock 53) so SBC negotiates near-transparent quality "
                   "with capable sinks — helps ANY Bluetooth device. Reversible mtkbt patch (not the "
                   "protected UI app, so no bootloop). Ghidra-verified: this is the SBC max-bitpool "
                   "written into the codec-capability struct during A2DP negotiation (mtkbt "
                   "FUN_0003f4c0, the 'V' SBC endpoint). Confirm audibly with a real sink + the BT Monitor.")
    risk = "med"
    status = "built"
    # mtkbt FUN_0003f4c0 builds the A2DP SBC SEP capability; the 'V' branch stores max bitpool 0x35 (53)
    # into the cap struct via: b .-2 ; movs r0,#0x35 ; strb r0,[sp,#0x3c].  Unique site in mtkbt.
    FIND = bytes.fromhex("ffe735208df83c00")

    def inputs(self):
        return [{"name": "bitpool", "type": "int", "label": "Max bitpool (53 stock · 76 XQ · ≤86)", "default": 76}]

    def _repl(self, bitpool):
        if not (2 <= bitpool <= 250):
            raise ValueError("bitpool must be 2..250 (SBC-XQ typically 76–86)")
        return self.FIND[:2] + bytes([bitpool, 0x20]) + self.FIND[4:]

    def preview(self, config, ctx):
        bp = int(config.get("bitpool", 76))
        data = device.pull_file(MTKBT)
        if data.count(self.FIND):
            st = f"stock (53) — will set max bitpool = {bp}"
        elif data.count(self._repl(bp)):
            st = f"already set to {bp}"
        else:
            st = "site not found (already set to a different value, or build differs)"
        return {"kind": "text", "data": f"SBC bitpool: {st}"}

    def apply(self, config, ctx):
        bp = int(config.get("bitpool", 76))
        data = device.pull_file(MTKBT)
        if data.count(self.FIND) == 0:
            raise binpatch.PatchError("SBC bitpool site not found (already patched, or build differs)")
        new, off = binpatch.patch(data, self.FIND, self._repl(bp))
        ctx.ledger.backup_file(self.id, MTKBT)
        device.install_file(new, MTKBT, mode="755")
        return (f"SBC max bitpool set to {bp} (@0x{off:x}) — reboot, reconnect BT. "
                f"EXPERIMENTAL: confirm with the BT Monitor / listening test.")

    def revert(self, ctx):
        ctx.ledger.restore(self.id)
