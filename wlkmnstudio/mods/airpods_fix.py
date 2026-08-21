from ..module import Mod, register
from .. import device
from ..formats import binpatch

MTKBT = "/system/bin/mtkbt"


@register
class AirPodsFix(Mod):
    id = "airpods_fix"
    name = "AirPods / A2DP Fix"
    category = "Audio"
    description = ("Fix strict-A2DP sinks (AirPods) that play ~1 ms then go silent: divide the RTP "
                   "media-timestamp increment by 4 (count samples, not bytes). 8-byte mtkbt patch.")
    risk = "low"
    status = "shipped"
    # 18-byte context; last 8 bytes are the patched instructions.
    FIND = bytes.fromhex("089817f8213c03fb0213d3f814c060445861")
    REPL = bytes.fromhex("089817f8213c03fb021380085c6900195861")

    def _current(self, ctx):
        data = device.pull_file(MTKBT)
        return binpatch.state(data, self.FIND, self.REPL), data

    def preview(self, config, ctx):
        st, _ = self._current(ctx)
        return {"kind": "text", "data": f"mtkbt is currently: {st.upper()}"}

    def apply(self, config, ctx):
        st, data = self._current(ctx)
        if st == "patched":
            return "mtkbt already patched — nothing to do"
        if st != "stock":
            raise binpatch.PatchError("mtkbt doesn't match the known build — not patching")
        new, off = binpatch.patch(data, self.FIND, self.REPL)
        ctx.ledger.backup_file(self.id, MTKBT)
        device.install_file(new, MTKBT, mode="755")
        return f"patched mtkbt (8 bytes @ file offset 0x{off + 10:x}) — reboot, then reconnect AirPods"

    def revert(self, ctx):
        ctx.ledger.restore(self.id)
